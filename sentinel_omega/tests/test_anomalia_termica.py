"""alfa2 medía el instrumento, no el planeta. Que no vuelva a pasar.

Hallado el 2026-09-26: `fetch_alfa2_data` devolvía `"thermal_anomaly_count": 0`
literal, y de las 2.817 filas de `tbl_cobertura_satelital_historico` la columna
`thermal_anomalies` tenía **un solo valor distinto: 0**. El bot que se llama
«Satellite Thermal Anomaly Detection» nunca había medido una anomalía térmica.
Sus otros dos rasgos --- `satellite_coverage_score` y `satellite_clear_passes`
--- miden cuán despejado estaba el cielo para el satélite: el instrumento, no
la Tierra. De ahí que no alarme nunca y no tenga ni una firma de 19.620.

Estas pruebas defienden la frontera: **cero es un valor medido; lo que no se
midió va ausente**, y el lector de FRP falla ruidosamente antes que devolver 0.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from sentinel_omega.core.features_onnx import vector_para
from sentinel_omega.infrastructure.api import esa_frp


def test_el_cero_literal_ya_no_esta_en_el_pipeline():
    """La línea que lo fabricaba: `"thermal_anomaly_count": 0`."""
    fuente = Path(
        "sentinel_omega/infrastructure/pipeline/data_pipeline.py"
    ).read_text()
    assert '"thermal_anomaly_count": 0' not in fuente
    # y ahora sale de un producto de verdad
    assert "contar_anomalias_termicas" in fuente


def test_el_ciclo_no_escribe_la_clave_si_no_se_midio():
    """`vector_para` pone 0.0 donde falta un rasgo --- y para el modelo eso
    significa «cero anomalías medidas». La diferencia está en NO escribir la
    clave: así el descarte por vector vacío puede actuar."""
    fuente = Path("sentinel_omega/launcher.py").read_text()
    # el patrón viejo: leer con 0 por defecto
    assert 'alfa2_data.get("thermal_anomaly_count", 0)' not in fuente
    assert 'anomalias = alfa2_data.get("thermal_anomaly_count")' in fuente


def test_el_repositorio_guarda_null_no_cero(tmp_path):
    """Sin medición, la fila debe quedar con NULL: así el histórico distingue
    «no se midió» de «no hubo»."""
    from sentinel_omega.infrastructure.database.schema import init_database

    db = str(tmp_path / "t.db")
    conn = init_database(db)
    conn.close()
    from sentinel_omega.infrastructure.database.repository import (
        SentinelRepository,
    )
    repo = SentinelRepository(db)
    repo.insert_cobertura_satelital(
        timestamp_blk="2026-09-26 12:00", zona="guerrero_gap",
        coverage_score=0.8, clear_passes=20, total_passes=50, revisit_days=3.0,
    )
    c = sqlite3.connect(db)
    valor = c.execute(
        "SELECT thermal_anomalies FROM tbl_cobertura_satelital"
    ).fetchone()[0]
    c.close()
    assert valor is None, f"se guardó {valor!r} en vez de NULL"


def test_el_lector_de_frp_no_devuelve_cero_cuando_no_encuentra_nada(tmp_path):
    """Si la variable no está en el NetCDF, LANZA. Adivinar un nombre y
    devolver ceros es peor que no medir --- y es el error que este proyecto ya
    pagó dos veces."""
    h5py = pytest.importorskip("h5py")
    nc = tmp_path / "FRP_in.nc"
    with h5py.File(nc, "w") as f:
        f.create_dataset("otra_cosa", data=np.zeros(4))
    with pytest.raises(LookupError):
        esa_frp.leer_frp(nc)


def test_el_lector_de_frp_cuenta_solo_sobre_el_umbral(tmp_path):
    h5py = pytest.importorskip("h5py")
    nc = tmp_path / "FRP_in.nc"
    with h5py.File(nc, "w") as f:
        # dos por encima del mínimo, dos por debajo
        f.create_dataset("FRP_MWIR", data=np.array([0.2, 5.0, 0.4, 120.0]))
    assert esa_frp.leer_frp(nc) == 2


def test_el_lector_de_frp_descarta_el_relleno(tmp_path):
    """`_FillValue` no es una medición."""
    h5py = pytest.importorskip("h5py")
    nc = tmp_path / "FRP_in.nc"
    with h5py.File(nc, "w") as f:
        d = f.create_dataset("FRP_MWIR", data=np.array([-999.0, 8.0, -999.0]))
        d.attrs["_FillValue"] = -999.0
    assert esa_frp.leer_frp(nc) == 1


def test_sin_zonas_no_inventa_un_conteo():
    """None, no 0: «no lo sé» no es «no hubo»."""
    assert esa_frp.contar_anomalias_termicas([]) is None
    assert esa_frp.contar_anomalias_termicas(["zona_que_no_existe"]) is None


def test_verificado_contra_producto_real_y_frp_mwir_primero():
    """El 2026-09-26 `--probar` bajó un producto SL_2_FRP real y confirmó que
    la potencia viene en `FRP_MWIR`. La bandera sube a True sólo con eso, y el
    producto usado queda anotado para poder repetir la verificación."""
    assert esa_frp.VERIFICADO_CONTRA_PRODUCTO_REAL is True
    assert esa_frp.VARIABLES_FRP[0] == "FRP_MWIR"
    assert "SL_2_FRP" in esa_frp.PRODUCTO_VERIFICACION
    assert len(esa_frp.VARIABLES_FRP) >= 2, "debe conservar respaldos"


def test_alfa2_sin_anomalia_medida_solo_lleva_lo_observable():
    """Lo que hoy tiene alfa2: dos rasgos de observabilidad. El tercero llega
    cuando la ESA responda."""
    rasgos = {"satellite_coverage_score": 0.78, "satellite_clear_passes": 25.0}
    vec = vector_para("alfa2", rasgos)
    assert vec.shape == (8,)
    assert int(np.count_nonzero(vec)) > 0
    # con la anomalía medida, el vector cambia --- prueba de que la posición
    # existe y estaba desperdiciada en un cero
    con = vector_para("alfa2", {**rasgos, "satellite_thermal_anomalies": 3.0})
    assert not np.array_equal(vec, con)


# ── Muestra real (recortada) del producto verificado el 2026-09-26 ──────────
# `tests/data/frp_muestra/<PRODUCTO_VERIFICACION>/`: los tres NetCDF que se
# usan, sólo con sus variables 1-D (las detecciones), sin la malla de flags.

MUESTRA = (
    Path(__file__).parent / "data" / "frp_muestra" / esa_frp.PRODUCTO_VERIFICACION
)
TODO_EL_GRANULO = {"lonmin": -180.0, "latmin": -90.0,
                   "lonmax": 180.0, "latmax": 90.0}


def test_la_muestra_real_esta_en_el_repo():
    for n in (esa_frp.ARCHIVO_ESTANDAR, esa_frp.ARCHIVO_MERGED,
              esa_frp.ARCHIVO_500M):
        assert (MUESTRA / n).is_file(), n


def test_cuenta_del_estandar_nunca_del_alternativo(tmp_path):
    """Hasta el 2026-09-26 el orden alfabético elegía el ALTERNATIVO
    («Demonstrational, precaution only»). Un alternativo con 50 fuegos falsos
    al lado no debe cambiar el conteo."""
    pytest.importorskip("h5py")
    import h5py
    import shutil

    d = tmp_path / "prod"
    shutil.copytree(MUESTRA, d)
    with h5py.File(d / esa_frp.ARCHIVO_ALTERNATIVO, "w") as f:
        f.create_dataset("FRP_MWIR", data=np.full(50, 500.0))
    assert esa_frp.leer_frp(d) == esa_frp.leer_frp(d / esa_frp.ARCHIVO_ESTANDAR)
    assert esa_frp.leer_frp(d) == 6
    assert all(x["archivo"] != esa_frp.ARCHIVO_ALTERNATIVO
               for x in esa_frp.leer_detecciones(d))


def test_detecciones_traen_todas_las_variables():
    pytest.importorskip("h5py")
    det = esa_frp.leer_detecciones(MUESTRA, zona="z")
    km = [x for x in det if x["fuente"] == "1km"]
    m5 = [x for x in det if x["fuente"] == "500m"]
    assert len(km) == 18 and len(m5) == 16
    # MWIR y SWIR 1 km, con sus incertidumbres
    assert sum(x["frp_mwir"] is not None for x in km) >= 6
    assert any(x["frp_swir"] is not None for x in km)
    assert all((x["frp_mwir"] is None) == (x["frp_mwir_unc"] is None)
               for x in km)
    # el -1 del merged («esta banda no detectó») se guarda como ausente
    for x in km:
        for k in ("frp_mwir", "frp_mwir_unc", "frp_swir", "frp_swir_unc"):
            assert x[k] is None or x[k] >= 0, (k, x[k])
    assert all(isinstance(x["used_channel"], int) for x in km)
    # la confianza MWIR existe donde detectó MWIR (en las sólo-SWIR es -1)
    assert all(x["confidence_mwir"] is not None
               for x in km if x["frp_mwir"] is not None)
    assert all(x["frp_swir_500m"] is not None for x in m5)
    assert all(x["frp_swir_500m_unc"] is not None for x in m5)
    # tiempo real del paso (19-sep-2026 ~04:40 UTC) y coordenadas en México
    assert all(x["ts_utc"].startswith("2026-09-19T04:") for x in det)
    assert all(14 < x["lat"] < 33 and -118 < x["lon"] < -86 for x in det)
    assert all(x["producto_id"] == esa_frp.PRODUCTO_VERIFICACION for x in det)


def test_la_caja_de_la_zona_filtra_el_granulo():
    """El gránulo cubre ~1.400 km; sus 6 fuegos caen entre 17,8° y 20,6° N,
    fuera del Guerrero Gap (16,0°-17,5° N). Antes se contaban igual."""
    pytest.importorskip("h5py")
    gg = {"lonmin": -100.5, "latmin": 16.0, "lonmax": -98.5, "latmax": 17.5}
    assert esa_frp.leer_frp(MUESTRA, bbox=TODO_EL_GRANULO) == 6
    assert esa_frp.leer_frp(MUESTRA, bbox=gg) == 0
    assert esa_frp.leer_detecciones(MUESTRA, bbox=gg) == []


def test_repositorio_guarda_detecciones_sin_duplicar(tmp_path):
    pytest.importorskip("h5py")
    from sentinel_omega.infrastructure.database.repository import (
        SentinelRepository,
    )
    from sentinel_omega.infrastructure.database.schema import init_database

    db = str(tmp_path / "t.db")
    init_database(db).close()
    c = sqlite3.connect(db)
    tablas_antes = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    c.close()

    det = esa_frp.leer_detecciones(MUESTRA, zona="z")
    repo = SentinelRepository(db)
    assert repo.insert_frp_detecciones(det) == 34
    assert repo.insert_frp_detecciones(det) == 0   # LOCF repite el lote
    assert repo.insert_frp_detecciones([]) == 0

    c = sqlite3.connect(db)
    tablas = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert tablas - tablas_antes == {"tbl_frp_detecciones"}
    n, nulos_swir, menos1 = c.execute(
        "SELECT COUNT(*), SUM(frp_swir IS NULL), "
        "SUM(frp_mwir = -1 OR frp_swir = -1) FROM tbl_frp_detecciones"
    ).fetchone()
    c.close()
    assert n == 34 and nulos_swir > 0 and not menos1


class _Prod:
    def __init__(self, i):
        self.properties = {"id": f"S3A_SL_2_FRP_prueba_{i}"}


class _DagSinCredenciales:
    """Busca bien, pero cada descarga falla por autenticación."""
    def __init__(self):
        self.descargas = 0

    def search(self, **kw):
        return [_Prod(i) for i in range(4)]

    def download(self, prod, **kw):
        self.descargas += 1
        MisconfiguredError = type("MisconfiguredError", (Exception,), {})
        raise MisconfiguredError("Missing credentials")


def test_fallo_de_autenticacion_corta_el_ciclo_sin_bucle(tmp_path, monkeypatch):
    """4 productos x 3 zonas serían 12 intentos contra Copernicus. Con
    credenciales malas debe haber UNO, y el resultado es None (no 0)."""
    dag = _DagSinCredenciales()
    monkeypatch.setattr(esa_frp, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(esa_frp, "_dag", lambda: dag)
    monkeypatch.setattr(esa_frp, "_bbox_de", lambda zonas: [
        (z, TODO_EL_GRANULO) for z in zonas])
    assert esa_frp.medir_frp(["a", "b", "c"]) is None
    assert dag.descargas == 1


def test_producto_en_cache_no_se_vuelve_a_bajar(tmp_path, monkeypatch):
    import shutil

    cache = tmp_path / "cache"
    shutil.copytree(MUESTRA, cache / "S3A_SL_2_FRP_prueba_0")
    dag = _DagSinCredenciales()
    dag.search = lambda **kw: [_Prod(0)]
    monkeypatch.setattr(esa_frp, "CACHE_DIR", cache)
    monkeypatch.setattr(esa_frp, "_dag", lambda: dag)
    monkeypatch.setattr(esa_frp, "_bbox_de", lambda zonas: [
        (z, TODO_EL_GRANULO) for z in zonas])
    m = esa_frp.medir_frp(["z"])
    assert dag.descargas == 0
    assert m["conteo"] == 6 and len(m["detecciones"]) == 34


def test_el_ciclo_persiste_las_detecciones():
    pipe = Path(
        "sentinel_omega/infrastructure/pipeline/data_pipeline.py").read_text()
    assert 'result["frp_detections"]' in pipe
    lanz = Path("sentinel_omega/launcher.py").read_text()
    assert "repo.insert_frp_detecciones(" in lanz


def test_solo_401_403_como_codigo_cortan_el_ciclo():
    assert esa_frp._es_fatal(Exception("HTTP 401 Unauthorized"))
    assert esa_frp._es_fatal(Exception("403 Forbidden"))
    assert not esa_frp._es_fatal(Exception("S3A_SL_2_FRP_1403 no legible"))
    assert not esa_frp._es_fatal(Exception("https://x/4011/prod timeout"))


def test_la_descarga_no_espera_minutos_a_un_producto_offline():
    assert esa_frp.DESCARGA_TIMEOUT_MIN <= 0.5
    assert "timeout=DESCARGA_TIMEOUT_MIN" in Path(esa_frp.__file__).read_text()


def test_zona_nula_no_duplica(tmp_path):
    pytest.importorskip("h5py")
    from sentinel_omega.infrastructure.database.repository import (
        SentinelRepository,
    )
    from sentinel_omega.infrastructure.database.schema import init_database

    db = str(tmp_path / "t.db")
    init_database(db).close()
    det = esa_frp.leer_detecciones(MUESTRA)  # zona=None
    repo = SentinelRepository(db)
    assert repo.insert_frp_detecciones(det) == 34
    assert repo.insert_frp_detecciones(det) == 0
