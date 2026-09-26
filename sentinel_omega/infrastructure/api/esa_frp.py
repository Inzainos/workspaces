"""Anomalías térmicas medidas: Sentinel-3 SLSTR Fire Radiative Power (ESA).

Por qué existe (2026-09-26)
---------------------------
alfa2 se llama «Satellite Thermal Anomaly Detection» y **nunca había medido una
anomalía térmica**. `fetch_alfa2_data` devolvía `"thermal_anomaly_count": 0`
literal, y de las 2.817 filas de `tbl_cobertura_satelital_historico` la columna
tenía **un solo valor distinto: 0**. Sus otros dos rasgos ---
`satellite_coverage_score` y `satellite_clear_passes` --- miden cuán despejado
estaba el cielo para el satélite: son métricas del INSTRUMENTO, no del planeta.
Por eso alfa2 no alarma nunca y no tiene ni una firma de 19.620.

El reparto que pidió el operador --- alfa1 desde la NOAA, alfa2 desde la ESA ---
tiene aquí su pieza real: `S3_SLSTR_L2FRP` es el producto de **potencia
radiativa del fuego**, exactamente la magnitud que alfa2 dice vigilar.
Comprobado contra el catálogo: 5 productos en 7 días sobre el Guerrero Gap.

Lo que hay que saber antes de fiarse
------------------------------------
1. **La búsqueda es pública; la descarga no.** Y el metadato de búsqueda NO
   trae el conteo de incendios --- sólo id, tamaño, órbita y fecha. El número
   sale de DENTRO del producto, así que hay que bajarlo (~1,5 MB) y leerlo.

2. **El nombre de la variable en el NetCDF no está verificado.** El 2026-09-26
   las credenciales de Copernicus del `.env` daban
   `invalid_grant / Invalid user credentials`, así que no se pudo bajar ni un
   producto. Este módulo se escribió SIN haber visto uno. Por eso:

   - busca la variable entre varios nombres candidatos y, si no encuentra
     ninguno, **lanza excepción** --- jamás devuelve 0
   - `contar_anomalias_termicas` devuelve `None` cuando no pudo medir, y
     `None` significa ausente: la clave no se escribe y el modelo no ve un cero
   - `VERIFICADO_CONTRA_PRODUCTO_REAL` queda en False hasta que alguien corra
     `python -m sentinel_omega.infrastructure.api.esa_frp --probar` con
     credenciales buenas y confirme qué variable trae

   Es el mismo error que ya salió caro dos veces en este proyecto: escribir
   contra una estructura supuesta. Aquí al menos falla ruidosamente.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

COLECCION = "S3_SLSTR_L2FRP"
PROVEEDOR = "cop_dataspace"

# Se pone en True cuando la lectura se confirme contra un producto descargado.
VERIFICADO_CONTRA_PRODUCTO_REAL = False

# Candidatos para la potencia radiativa dentro del NetCDF, de más a menos
# probable según la documentación del producto. Si ninguno aparece, se lanza:
# adivinar un nombre y devolver ceros es peor que no medir.
VARIABLES_FRP = ("FRP_MWIR", "FRP", "frp", "FRP_SWIR", "fire_radiative_power")

# Por debajo de esto no se cuenta como anomalía: el producto marca detecciones
# de muy baja potencia que son ruido de superficie caliente, no un evento.
FRP_MINIMO_MW = 1.0


def _dag():
    from sentinel_omega.infrastructure.api.esa_sentinel import _get_dag
    return _get_dag()


def _bbox_de(zonas: List[str]) -> List[Dict[str, float]]:
    from sentinel_omega.infrastructure.api.esa_sentinel import (
        get_seismic_zone_bboxes,
    )
    todas = get_seismic_zone_bboxes()
    fuera = []
    for z in zonas:
        b = todas.get(z)
        if b:
            fuera.append({"lonmin": b[0], "latmin": b[1],
                          "lonmax": b[2], "latmax": b[3]})
    return fuera


def leer_frp(ruta: Path) -> int:
    """Cuántas detecciones con FRP >= FRP_MINIMO_MW trae el producto.

    Lanza `LookupError` si no encuentra ninguna variable conocida. Eso es
    deliberado: el que llama debe tratar «no pude leerlo» distinto de «no hubo
    nada», porque son cosas distintas.
    """
    import h5py
    import numpy as np

    ruta = Path(ruta)
    candidatos = (
        sorted(ruta.rglob("FRP_in.nc")) + sorted(ruta.rglob("*FRP*.nc"))
        if ruta.is_dir() else [ruta]
    )
    if not candidatos:
        raise LookupError(f"ningún NetCDF de FRP dentro de {ruta}")

    for nc in candidatos:
        with h5py.File(nc, "r") as f:
            for nombre in VARIABLES_FRP:
                if nombre not in f:
                    continue
                v = np.asarray(f[nombre][...], dtype=float).ravel()
                relleno = f[nombre].attrs.get("_FillValue")
                if relleno is not None:
                    v = v[v != float(np.asarray(relleno).ravel()[0])]
                v = v[np.isfinite(v)]
                return int((v >= FRP_MINIMO_MW).sum())
    disponibles = []
    with h5py.File(candidatos[0], "r") as f:
        f.visit(lambda n: disponibles.append(n))
    raise LookupError(
        f"ninguna de {VARIABLES_FRP} está en {candidatos[0].name}; "
        f"hay: {disponibles[:25]}"
    )


def contar_anomalias_termicas(
    zonas: List[str],
    days: int = 7,
    max_productos: int = 4,
) -> Optional[int]:
    """Anomalías térmicas sumadas sobre las zonas, o **None si no se pudo medir**.

    `None` no es cero. Cero dice «el satélite miró y no había nada»; None dice
    «no lo sé», y es lo que toca cuando faltan credenciales, falla la red o el
    producto no se pudo leer.
    """
    bboxes = _bbox_de(zonas)
    if not bboxes:
        return None
    fin = datetime.now(timezone.utc)
    ini = fin - timedelta(days=days)
    total = 0
    leidos = 0
    try:
        dag = _dag()
    except Exception as e:  # noqa: BLE001
        logger.warning("ESA no disponible para FRP: %s", e)
        return None

    with tempfile.TemporaryDirectory(prefix="frp_") as tmp:
        for bbox in bboxes:
            try:
                res = dag.search(
                    collection=COLECCION, provider=PROVEEDOR, geom=bbox,
                    start=ini.strftime("%Y-%m-%d"), end=fin.strftime("%Y-%m-%d"),
                    limit=max_productos,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("búsqueda de FRP falló: %s", e)
                continue
            for prod in list(res)[:max_productos]:
                try:
                    ruta = dag.download(prod, output_dir=tmp, extract=True)
                    total += leer_frp(Path(ruta))
                    leidos += 1
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "producto de FRP no legible (%s): %s",
                        prod.properties.get("id", "?")[:40], e,
                    )
    if leidos == 0:
        logger.warning(
            "FRP: no se pudo leer ni un producto --- la anomalía térmica queda "
            "AUSENTE, no en cero"
        )
        return None
    logger.info("FRP: %d anomalías en %d productos de %d zonas",
                total, leidos, len(bboxes))
    return total


def main() -> None:
    """`--probar`: baja un producto y dice qué variables trae de verdad.

    Es el paso que falta para poner `VERIFICADO_CONTRA_PRODUCTO_REAL = True`.
    """
    import argparse

    ap = argparse.ArgumentParser(description="Comprobar la lectura de FRP")
    ap.add_argument("--probar", action="store_true")
    ap.add_argument("--zona", default="guerrero_gap")
    ap.add_argument("--dias", type=int, default=7)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [ESA_FRP] %(levelname)s %(message)s")
    if not args.probar:
        print(contar_anomalias_termicas([args.zona], days=args.dias))
        return

    import h5py

    bboxes = _bbox_de([args.zona])
    if not bboxes:
        raise SystemExit(f"zona desconocida: {args.zona}")
    fin = datetime.now(timezone.utc)
    ini = fin - timedelta(days=args.dias)
    dag = _dag()
    res = dag.search(collection=COLECCION, provider=PROVEEDOR, geom=bboxes[0],
                     start=ini.strftime("%Y-%m-%d"),
                     end=fin.strftime("%Y-%m-%d"), limit=1)
    if not len(res):
        raise SystemExit("sin productos en esa ventana")
    prod = list(res)[0]
    print("producto:", prod.properties.get("id"))
    with tempfile.TemporaryDirectory(prefix="frp_probar_") as tmp:
        ruta = Path(dag.download(prod, output_dir=tmp, extract=True))
        ncs = sorted(ruta.rglob("*.nc")) if ruta.is_dir() else [ruta]
        print(f"NetCDF dentro: {[n.name for n in ncs]}")
        for nc in ncs:
            with h5py.File(nc, "r") as f:
                nombres: List[str] = []
                f.visit(lambda n: nombres.append(n))
                print(f"\n  {nc.name}: {len(nombres)} objetos")
                for n in nombres[:40]:
                    print("    ", n)
        print("\nconteo con los candidatos actuales:", leer_frp(ruta))


if __name__ == "__main__":
    main()
