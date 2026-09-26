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


def test_queda_marcado_como_no_verificado_hasta_ver_un_producto():
    """El 2026-09-26 las credenciales de Copernicus daban invalid_grant, así que
    este módulo se escribió SIN haber visto un producto. La bandera existe para
    que nadie lo dé por probado: se pone en True cuando
    `python -m sentinel_omega.infrastructure.api.esa_frp --probar` confirme qué
    variable trae de verdad."""
    assert esa_frp.VERIFICADO_CONTRA_PRODUCTO_REAL is False
    assert len(esa_frp.VARIABLES_FRP) >= 2, "debe probar varios nombres"


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
