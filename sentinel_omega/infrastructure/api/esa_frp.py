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

3. **Verificado el 2026-09-26 (Agente-C).** Con credenciales buenas,
   `--probar` bajó `PRODUCTO_VERIFICACION` (Guerrero Gap, ventana de 7 días).
   El producto NO trae `FRP_in.nc`; trae cuatro NetCDF:

   - `FRP_MWIR1km_standard.nc` --- el de REFERENCIA («to be considered by
     default»): `FRP_MWIR`, `FRP_MWIR_uncertainty`, lat/lon, `time`,
     `confidence_MWIR`, `used_channel`. De aquí sale el conteo.
   - `FRP_Merged_MWIR1kmStandard_SWIR1km.nc` --- estándar MWIR + SWIR 1 km:
     `FRP_MWIR`, `FRP_SWIR`, `FRP_uncertainty_MWIR/SWIR` (-1 = esa banda no
     detectó), `confidence_MWIR`, `used_channel`, `n_SWIR_fire`,
     `transmittance_*`, lat/lon, `time` (µs desde 2000-01-01Z).
   - `FRP_SWIR500m.nc` --- `FRP_SWIR_500m`, `FRP_uncertainty_SWIR_500m`,
     `latitude_/longitude_/time_SWIR_500m`, `confidence_SWIR_SAA_500m`.
     (`fires_SWIR500m` es una dimensión vacía, no datos.)
   - `FRP_MWIR1km_alternative.nc` --- «Demonstrational, precaution only».
     **No se usa.** Hasta este cambio el orden alfabético lo ponía primero y
     el conteo de 6 salía de él por accidente; ahora se excluye.

   El gránulo cubre ~1.400 km: conteo y detecciones se filtran a la caja de
   cada zona. Las detecciones completas van a `tbl_frp_detecciones`
   (`medir_frp` en el ciclo del launcher; productos en caché bajo
   `data/cache/frp/` para no re-bajarlos cada hora).
   El invalid_grant previo era la línea sin comillas en `deploy/.env`
   (rompía `source`), no la contraseña. Credenciales: `_get_dag` las toma
   de `COPERNICUS_USER` / `COPERNICUS_PASSWORD`; el proceso las necesita en
   su entorno (systemd `EnvironmentFile=` o `source deploy/.env`).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

COLECCION = "S3_SLSTR_L2FRP"
PROVEEDOR = "cop_dataspace"

# Confirmado contra un producto descargado el 2026-09-26 (ver docstring §3).
VERIFICADO_CONTRA_PRODUCTO_REAL = True
PRODUCTO_VERIFICACION = (
    "S3A_SL_2_FRP____20260919T043726_20260919T044026_20260919T053313_"
    "0180_144_119______MAR_O_NR_003"
)

# Archivos del producto (verificados). El ALTERNATIVO es «Demonstrational,
# precaution only» según su propio atributo: no se usa NUNCA para contar.
# Antes del 2026-09-26 el orden alfabético lo ponía primero y el conteo salía
# de él por accidente.
ARCHIVO_ESTANDAR = "FRP_MWIR1km_standard.nc"
ARCHIVO_MERGED = "FRP_Merged_MWIR1kmStandard_SWIR1km.nc"
ARCHIVO_500M = "FRP_SWIR500m.nc"
ARCHIVO_ALTERNATIVO = "FRP_MWIR1km_alternative.nc"

# Candidatos para la potencia radiativa dentro del NetCDF. `FRP_MWIR` es el
# que trae el producto real (verificado); el resto queda de respaldo por si
# cambia la versión del producto. Si ninguno aparece, se lanza:
# adivinar un nombre y devolver ceros es peor que no medir.
VARIABLES_FRP = ("FRP_MWIR", "FRP", "frp", "FRP_SWIR", "fire_radiative_power")

# Por debajo de esto no se cuenta como anomalía: el producto marca detecciones
# de muy baja potencia que son ruido de superficie caliente, no un evento.
FRP_MINIMO_MW = 1.0

# Productos ya bajados: el ciclo del launcher es horario y la ventana de
# búsqueda de 7 días devuelve casi siempre los mismos productos. Sin caché
# se bajarían otra vez cada hora.
CACHE_DIR = Path(
    os.environ.get("SENTINEL_FRP_CACHE")
    or Path(__file__).resolve().parents[2] / "data" / "cache" / "frp"
)

# Errores que no se arreglan reintentando: se aborta el resto del ciclo para
# no martillar a Copernicus con credenciales malas.
_ERRORES_FATALES = ("AuthenticationError", "MisconfiguredError")
_TEXTO_FATAL = ("invalid_grant", "invalid user credentials")
_HTTP_FATAL = re.compile(r"\b40[13]\b")

# Sin reintentos escondidos de eodag (ver `_producto_local`).
DESCARGA_WAIT_MIN = 0.1
DESCARGA_TIMEOUT_MIN = 0.1


def _dag():
    from sentinel_omega.infrastructure.api.esa_sentinel import _get_dag
    return _get_dag()


def _bbox_de(zonas: List[str]) -> List[Tuple[str, Dict[str, float]]]:
    from sentinel_omega.infrastructure.api.esa_sentinel import (
        get_seismic_zone_bboxes,
    )
    todas = get_seismic_zone_bboxes()
    fuera = []
    for z in zonas:
        b = todas.get(z)
        if b:
            fuera.append((z, {"lonmin": b[0], "latmin": b[1],
                              "lonmax": b[2], "latmax": b[3]}))
    return fuera


# ── lectura ──────────────────────────────────────────────────────────

def _vector(f, nombre: str):
    """Variable 1-D como float, con `_FillValue` a NaN y escala aplicada.

    None si la variable no existe o no es de datos (dimensión vacía).
    """
    import numpy as np

    if nombre not in f:
        return None
    d = f[nombre]
    if d.shape == () or d.size == 0:
        return None
    v = np.asarray(d[...], dtype=float).ravel()
    relleno = d.attrs.get("_FillValue")
    if relleno is not None:
        v[v == float(np.asarray(relleno).ravel()[0])] = np.nan
    esc = d.attrs.get("scale_factor")
    off = d.attrs.get("add_offset")
    if esc is not None:
        v = v * float(np.asarray(esc).ravel()[0])
    if off is not None:
        v = v + float(np.asarray(off).ravel()[0])
    return v


_UNIDADES_S = {"seconds": 1.0, "milliseconds": 1e-3, "microseconds": 1e-6}


def _tiempos(f, nombre: str) -> List[Optional[str]]:
    """`time` del producto (p. ej. «microseconds since 2000-01-01…») a ISO UTC."""
    v = _vector(f, nombre)
    if v is None:
        return []
    unidades = f[nombre].attrs.get("units", b"")
    if isinstance(unidades, bytes):
        unidades = unidades.decode("utf-8", "ignore")
    m = re.match(r"\s*(\w+)\s+since\s+(\d{4}-\d{2}-\d{2})", str(unidades))
    if not m or m.group(1) not in _UNIDADES_S:
        return [None] * len(v)
    base = datetime.fromisoformat(m.group(2)).replace(tzinfo=timezone.utc)
    k = _UNIDADES_S[m.group(1)]
    return [
        None if x != x else
        (base + timedelta(seconds=x * k)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for x in v
    ]


def _num(v, i: int, negativo_es_ausente: bool = False):
    if v is None or i >= len(v):
        return None
    x = float(v[i])
    if x != x or (negativo_es_ausente and x < 0):
        return None
    return x


def _dentro(lat, lon, bbox: Optional[Dict[str, float]]) -> bool:
    if bbox is None:
        return True
    if lat is None or lon is None:
        return False
    return (bbox["latmin"] <= lat <= bbox["latmax"]
            and bbox["lonmin"] <= lon <= bbox["lonmax"])


def _candidatos_conteo(ruta: Path) -> List[Path]:
    """Orden de preferencia para CONTAR: estándar, merged, legado; nunca el
    alternativo."""
    if not ruta.is_dir():
        return [ruta]
    preferidos = []
    for nombre in (ARCHIVO_ESTANDAR, ARCHIVO_MERGED, "FRP_in.nc"):
        preferidos += sorted(ruta.rglob(nombre))
    resto = [p for p in sorted(ruta.rglob("*FRP*.nc"))
             if p not in preferidos and p.name != ARCHIVO_ALTERNATIVO]
    return preferidos + resto


def leer_frp(ruta: Path, bbox: Optional[Dict[str, float]] = None) -> int:
    """Cuántas detecciones con FRP >= FRP_MINIMO_MW trae el producto.

    Con `bbox`, sólo las que caen dentro (el gránulo de SLSTR cubre ~1.400 km
    y la mayoría de sus fuegos no son de la zona). Lanza `LookupError` si no
    encuentra ninguna variable conocida: «no pude leerlo» no es «no hubo nada».
    """
    import h5py
    import numpy as np

    ruta = Path(ruta)
    candidatos = _candidatos_conteo(ruta)
    if not candidatos:
        raise LookupError(f"ningún NetCDF de FRP dentro de {ruta}")

    for nc in candidatos:
        with h5py.File(nc, "r") as f:
            for nombre in VARIABLES_FRP:
                v = _vector(f, nombre)
                if v is None:
                    continue
                ok = np.isfinite(v) & (v >= FRP_MINIMO_MW)
                if bbox is not None:
                    lat, lon = _vector(f, "latitude"), _vector(f, "longitude")
                    if lat is None or lon is None:
                        raise LookupError(
                            f"{nc.name} sin latitude/longitude: no se puede "
                            "filtrar por zona")
                    ok &= ((lat >= bbox["latmin"]) & (lat <= bbox["latmax"])
                           & (lon >= bbox["lonmin"]) & (lon <= bbox["lonmax"]))
                return int(ok.sum())
    disponibles: List[str] = []
    with h5py.File(candidatos[0], "r") as f:
        f.visit(lambda n: disponibles.append(n))
    raise LookupError(
        f"ninguna de {VARIABLES_FRP} está en {candidatos[0].name}; "
        f"hay: {disponibles[:25]}"
    )


def leer_detecciones(
    ruta: Path,
    bbox: Optional[Dict[str, float]] = None,
    zona: Optional[str] = None,
    producto_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Todas las variables por detección: una fila por fuego.

    - `fuente="1km"`: del merged (MWIR estándar + SWIR 1 km). En ese archivo
      `-1` significa «esta banda no detectó»: se guarda None, no -1.
      Si no hay merged, se cae al estándar (sólo MWIR).
    - `fuente="500m"`: de `FRP_SWIR500m.nc`.
    Nunca lee el alternativo.
    """
    import h5py

    ruta = Path(ruta)
    base = ruta if ruta.is_dir() else ruta.parent
    pid = producto_id or base.name
    filas: List[Dict[str, Any]] = []

    def _uno(nombre):
        hall = sorted(base.rglob(nombre))
        return hall[0] if hall else None

    nc1 = _uno(ARCHIVO_MERGED) or _uno(ARCHIVO_ESTANDAR)
    if nc1 is not None:
        with h5py.File(nc1, "r") as f:
            mw = _vector(f, "FRP_MWIR")
            n = 0 if mw is None else len(mw)
            lat, lon = _vector(f, "latitude"), _vector(f, "longitude")
            tt = _tiempos(f, "time")
            mw_u = _vector(f, "FRP_uncertainty_MWIR")
            if mw_u is None:
                mw_u = _vector(f, "FRP_MWIR_uncertainty")
            sw, sw_u = _vector(f, "FRP_SWIR"), _vector(f, "FRP_uncertainty_SWIR")
            conf, canal = _vector(f, "confidence_MWIR"), _vector(f, "used_channel")
            nsw = _vector(f, "n_SWIR_fire")
            tr_mw = _vector(f, "transmittance_MWIR")
            tr_sw = _vector(f, "transmittance_SWIR")
            for i in range(n):
                la, lo = _num(lat, i), _num(lon, i)
                if not _dentro(la, lo, bbox):
                    continue
                c = _num(canal, i)
                s = _num(nsw, i, True)
                filas.append({
                    "producto_id": pid, "zona": zona, "fuente": "1km",
                    "archivo": nc1.name, "idx": i,
                    "ts_utc": tt[i] if i < len(tt) else None,
                    "lat": la, "lon": lo,
                    "frp_mwir": _num(mw, i, True),
                    "frp_mwir_unc": _num(mw_u, i, True),
                    "frp_swir": _num(sw, i, True),
                    "frp_swir_unc": _num(sw_u, i, True),
                    "confidence_mwir": _num(conf, i, True),
                    "used_channel": None if c is None else int(c),
                    "n_swir_fire": None if s is None else int(s),
                    "transmittance_mwir": _num(tr_mw, i, True),
                    "transmittance_swir": _num(tr_sw, i, True),
                    "frp_swir_500m": None, "frp_swir_500m_unc": None,
                    "confidence_swir_saa": None,
                })

    nc5 = _uno(ARCHIVO_500M)
    if nc5 is not None:
        with h5py.File(nc5, "r") as f:
            fr = _vector(f, "FRP_SWIR_500m")
            n = 0 if fr is None else len(fr)
            lat = _vector(f, "latitude_SWIR_500m")
            lon = _vector(f, "longitude_SWIR_500m")
            tt = _tiempos(f, "time_SWIR_500m")
            fr_u = _vector(f, "FRP_uncertainty_SWIR_500m")
            saa = _vector(f, "confidence_SWIR_SAA_500m")
            tr = _vector(f, "transmittance_SWIR_500m")
            for i in range(n):
                la, lo = _num(lat, i), _num(lon, i)
                if not _dentro(la, lo, bbox):
                    continue
                filas.append({
                    "producto_id": pid, "zona": zona, "fuente": "500m",
                    "archivo": nc5.name, "idx": i,
                    "ts_utc": tt[i] if i < len(tt) else None,
                    "lat": la, "lon": lo,
                    "frp_mwir": None, "frp_mwir_unc": None,
                    "frp_swir": None, "frp_swir_unc": None,
                    "confidence_mwir": None, "used_channel": None,
                    "n_swir_fire": None, "transmittance_mwir": None,
                    "transmittance_swir": _num(tr, i, True),
                    "frp_swir_500m": _num(fr, i, True),
                    "frp_swir_500m_unc": _num(fr_u, i, True),
                    "confidence_swir_saa": _num(saa, i, True),
                })
    return filas


# ── descarga + ciclo ─────────────────────────────────────────────────

def _es_fatal(e: Exception) -> bool:
    if type(e).__name__ in _ERRORES_FATALES:
        return True
    t = str(e).lower()
    return any(s in t for s in _TEXTO_FATAL) or bool(_HTTP_FATAL.search(t))


def _podar_cache(dias: int) -> None:
    if not CACHE_DIR.is_dir():
        return
    limite = time.time() - (dias + 2) * 86400
    for d in CACHE_DIR.iterdir():
        try:
            if d.is_dir() and d.stat().st_mtime < limite:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def _producto_local(dag, prod) -> Path:
    """Ruta al producto extraído, bajándolo sólo si no está en la caché."""
    pid = str(prod.properties.get("id") or prod.properties.get("title"))
    destino = CACHE_DIR / pid
    if destino.is_dir() and any(destino.rglob("*.nc")):
        return destino
    destino.mkdir(parents=True, exist_ok=True)
    try:
        # wait/timeout en MINUTOS: por defecto eodag re-pide un producto
        # OFFLINE cada 12 s durante 10 min. Aquí, un intento y se salta.
        dag.download(prod, output_dir=str(destino), extract=True,
                     wait=DESCARGA_WAIT_MIN, timeout=DESCARGA_TIMEOUT_MIN)
    except Exception:
        shutil.rmtree(destino, ignore_errors=True)
        raise
    if not any(destino.rglob("*.nc")):
        shutil.rmtree(destino, ignore_errors=True)
        raise LookupError(f"descarga de {pid[:40]} sin NetCDF")
    return destino


def medir_frp(
    zonas: List[str],
    days: int = 7,
    max_productos: int = 4,
) -> Optional[Dict[str, Any]]:
    """Conteo de anomalías y detecciones completas, o **None si no se midió**.

    Devuelve `{"conteo", "detecciones", "productos"}`. `conteo` sale del
    archivo estándar, filtrado a la caja de cada zona. Un fallo de descarga se
    registra y el ciclo sigue; un fallo de autenticación corta el resto de
    descargas del ciclo (reintentar no lo arregla y sí satura a Copernicus).
    """
    zb = _bbox_de(zonas)
    if not zb:
        return None
    fin = datetime.now(timezone.utc)
    ini = fin - timedelta(days=days)
    try:
        dag = _dag()
    except Exception as e:  # noqa: BLE001
        logger.warning("ESA no disponible para FRP: %s", e)
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _podar_cache(days)
    total, leidos = 0, 0
    detecciones: List[Dict[str, Any]] = []
    abortar = False
    for zona, bbox in zb:
        if abortar:
            break
        try:
            res = dag.search(
                collection=COLECCION, provider=PROVEEDOR, geom=bbox,
                start=ini.strftime("%Y-%m-%d"), end=fin.strftime("%Y-%m-%d"),
                limit=max_productos,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("búsqueda de FRP falló (%s): %s", zona, e)
            if _es_fatal(e):
                abortar = True
            continue
        for prod in list(res)[:max_productos]:
            pid = str(prod.properties.get("id", "?"))
            try:
                ruta = _producto_local(dag, prod)
                total += leer_frp(ruta, bbox=bbox)
                detecciones += leer_detecciones(ruta, bbox, zona, pid)
                leidos += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("producto de FRP no legible (%s): %s",
                               pid[:40], e)
                if _es_fatal(e):
                    logger.error("FRP: fallo de autenticación; se cortan las "
                                 "descargas de este ciclo")
                    abortar = True
                    break
    if leidos == 0:
        logger.warning(
            "FRP: no se pudo leer ni un producto --- la anomalía térmica queda "
            "AUSENTE, no en cero"
        )
        return None
    logger.info("FRP: %d anomalías y %d detecciones en %d productos de %d zonas",
                total, len(detecciones), leidos, len(zb))
    return {"conteo": total, "detecciones": detecciones, "productos": leidos}


def contar_anomalias_termicas(
    zonas: List[str],
    days: int = 7,
    max_productos: int = 4,
) -> Optional[int]:
    """Anomalías térmicas sumadas sobre las zonas, o **None si no se pudo medir**.

    `None` no es cero. Cero dice «el satélite miró y no había nada»; None dice
    «no lo sé».
    """
    m = medir_frp(zonas, days=days, max_productos=max_productos)
    return None if m is None else m["conteo"]


def main() -> None:
    """`--probar`: baja UN producto (a la caché) y dice qué trae de verdad."""
    import argparse

    ap = argparse.ArgumentParser(description="Comprobar la lectura de FRP")
    ap.add_argument("--probar", action="store_true")
    ap.add_argument("--zona", default="guerrero_gap")
    ap.add_argument("--dias", type=int, default=7)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [ESA_FRP] %(levelname)s %(message)s")
    if not args.probar:
        m = medir_frp([args.zona], days=args.dias)
        print(None if m is None else
              {"conteo": m["conteo"], "detecciones": len(m["detecciones"]),
               "productos": m["productos"]})
        return

    import h5py

    zb = _bbox_de([args.zona])
    if not zb:
        raise SystemExit(f"zona desconocida: {args.zona}")
    zona, bbox = zb[0]
    fin = datetime.now(timezone.utc)
    ini = fin - timedelta(days=args.dias)
    dag = _dag()
    res = dag.search(collection=COLECCION, provider=PROVEEDOR, geom=bbox,
                     start=ini.strftime("%Y-%m-%d"),
                     end=fin.strftime("%Y-%m-%d"), limit=1)
    if not len(res):
        raise SystemExit("sin productos en esa ventana")
    prod = list(res)[0]
    print("producto:", prod.properties.get("id"))
    ruta = _producto_local(dag, prod)
    ncs = sorted(ruta.rglob("*.nc"))
    print(f"NetCDF dentro: {[n.name for n in ncs]}")
    for nc in ncs:
        with h5py.File(nc, "r") as f:
            nombres: List[str] = []
            f.visit(lambda n: nombres.append(n))
            print(f"\n  {nc.name}: {len(nombres)} objetos")
            for n in nombres[:40]:
                print("    ", n)
    print("\nconteo en todo el gránulo:", leer_frp(ruta))
    print(f"conteo dentro de {zona}:", leer_frp(ruta, bbox=bbox))
    print("detecciones dentro de la zona:",
          len(leer_detecciones(ruta, bbox, zona)))


if __name__ == "__main__":
    main()
