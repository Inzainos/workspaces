"""alfa2 miraba tres cajas mexicanas; el Juez lo calificaba contra el mundo.

Medido el 2026-10-02. `fetch_alfa2_data` tenía
`target_zones = zones or ["guerrero_gap", "oaxaca_costa", "chiapas"]`, mientras
`verificacion.py` pasa al Juez TODOS los nodos reales y
`fetch_earthquakes(min_magnitude=4.5)` es el catálogo mundial. El bot no
fallaba: miraba otra cosa que la que se le exigía.

Por qué es una rotación y no «todas»
------------------------------------
`compute_temporal_coverage` son dos consultas al catálogo de Copernicus (S2 y
S1). Medido en vivo:

    guerrero_gap        22,53 s
    ring_of_fire_japan  18,96 s

A ~20 s por zona, con un ciclo de ~190 s:

    3 zonas (lo de antes)    ~60 s     un tercio del ciclo
    10 zonas históricas     ~200 s     NO CABE
    50 nodos de la malla   ~1.000 s    17 min, imposible

Así que cada ciclo mide las tres MÁS ANTIGUAS y los rasgos se agregan sobre la
última lectura de todas: barrido completo en ~17 ciclos, poco menos de una hora,
al mismo coste por ciclo que antes.
"""
import sqlite3

import pytest

from sentinel_omega.core.alfa2_zonas import (
    TABLA, ZONAS_POR_CICLO, agregado_global, asegurar_tabla,
    guardar_cobertura, puntaje_zona, zonas_a_medir,
)
from sentinel_omega.infrastructure.api.esa_sentinel import (
    get_seismic_zone_bboxes, zonas_de_la_malla,
)


@pytest.fixture
def base(tmp_path):
    c = sqlite3.connect(tmp_path / "z.db")
    asegurar_tabla(c)
    return c


def _cov(pasadas=8, nubes=(5.0, 10.0, 60.0), revisita=1.0):
    return {"total_passes": pasadas, "s2_count": pasadas // 2,
            "s1_count": pasadas - pasadas // 2,
            "s2_cloud_covers": list(nubes), "mean_revisit_days": revisita}


def test_las_zonas_salen_de_la_malla_y_son_globales():
    """Los 50 nodos `real` son la referencia global del sistema."""
    m = zonas_de_la_malla()
    assert len(m) == 50, len(m)
    lats = [(b[1] + b[3]) / 2 for b in m.values()]
    lons = [(b[0] + b[2]) / 2 for b in m.values()]
    assert min(lats) < -30 and max(lats) > 60, (min(lats), max(lats))
    assert min(lons) < -170 and max(lons) > 170, (min(lons), max(lons))


def test_las_diez_zonas_historicas_sobreviven():
    """`tbl_frp_detecciones` tiene filas que referencian 'guerrero_gap' y
    'chiapas': borrarlas dejaría esas detecciones sin caja que las explique."""
    t = get_seismic_zone_bboxes()
    for z in ("guerrero_gap", "oaxaca_costa", "chiapas", "baja_falla",
              "jalisco_colima", "michoacan", "puebla_tlaxcala",
              "ring_of_fire_japan", "ring_of_fire_chile", "turkey_anatolia"):
        assert z in t, f"desapareció la zona histórica {z}"
    assert len(t) == 60, len(t)


def test_la_rotacion_empieza_por_las_nunca_medidas(base):
    assert len(zonas_a_medir(base)) == ZONAS_POR_CICLO
    primeras = zonas_a_medir(base)
    for z in primeras:
        guardar_cobertura(base, z, _cov())
    # Ya medidas: la siguiente vuelta tiene que traer OTRAS.
    assert not (set(zonas_a_medir(base)) & set(primeras)), (
        "la rotación repitió zonas que acaba de medir")


def test_la_rotacion_barre_todas_sin_contador(base):
    """«La más antigua primero» es toda la rotación: no hay cursor que se
    desincronice si un ciclo falla o si el sistema estuvo apagado."""
    total = len(zonas_de_la_malla())
    vistas = set()
    for _ in range((total // ZONAS_POR_CICLO) + 2):
        toca = zonas_a_medir(base)
        vistas.update(toca)
        for z in toca:
            guardar_cobertura(base, z, _cov())
    assert vistas == set(zonas_de_la_malla()), (
        f"faltaron {sorted(set(zonas_de_la_malla()) - vistas)}")


def test_el_agregado_usa_todas_las_zonas_medidas_no_solo_las_del_ciclo(base):
    """El corazón del arreglo: el rasgo describe el barrido global."""
    for z in list(zonas_de_la_malla())[:12]:
        guardar_cobertura(base, z, _cov())
    g = agregado_global(base)
    assert g is not None
    assert g["zonas"] == 12, g
    assert 0.0 <= g["satellite_coverage_score"] <= 1.0


def test_sin_ninguna_lectura_el_agregado_es_None(base):
    """Cero sintético: faltante es faltante, no un puntaje de 0."""
    assert agregado_global(base) is None


def test_guardar_sobreescribe_la_misma_zona(base):
    """Interesa la foto más reciente de cada sitio, no una fila por pasada."""
    z = next(iter(zonas_de_la_malla()))
    guardar_cobertura(base, z, _cov(pasadas=4))
    guardar_cobertura(base, z, _cov(pasadas=40))
    filas = base.execute(
        f"SELECT total_passes FROM {TABLA} WHERE zona=?", (z,)).fetchall()
    assert filas == [(40,)], filas


def test_el_puntaje_es_una_sola_formula():
    """Estaba escrita a mano TRES veces: en `_build_live_features`, en el
    bloque que persiste la cobertura y en el agregado. Tres copias de la misma
    aritmética se separan solas. Ahora la única es `puntaje_zona`."""
    from pathlib import Path

    fuente = Path("sentinel_omega/launcher.py").read_text()
    assert "_puntaje_zona(" in fuente, (
        "el launcher dejó de usar la función compartida")
    for copia in ("min(total / 8.0, 1.0)", "min(total_p / 8.0, 1.0)",
                  "max(0, 1.0 - revisit / 12.0)"):
        assert copia not in fuente, f"volvió una copia de la fórmula: {copia}"


def test_el_puntaje_satura_y_premia_lo_limpio():
    """Tres tercios: pasadas (saturando en 8), fracción sin nubes, revisita."""
    assert puntaje_zona(100, 10, 10, 0.0) == pytest.approx(1.0)
    assert puntaje_zona(0, 0, 0, 99.0) == pytest.approx(0.0)
    # Más pasadas limpias con todo lo demás igual: mejor puntaje.
    assert puntaje_zona(8, 8, 10, 1.0) > puntaje_zona(8, 2, 10, 1.0)


def test_los_cuatro_rasgos_salen_DE_LA_VENTANA_no_de_las_zonas():
    """El desajuste de escala que casi entro en produccion con el voto de alfa2.

    La firma agrega sobre 336 h de `tbl_cobertura_satelital` unida a su
    historico; el agregado de la rotacion suma sobre las ZONAS de la ultima
    lectura. Son dos magnitudes con el mismo nombre."""
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher._build_live_features)
    # Los cuatro rasgos salen de la MISMA ventana que la firma, y no hay
    # respaldo por ciclo --- un respaldo a otra escala es el desajuste con un
    # `if` delante. Medido el 2026-10-02 mirando las firmas de alfa2 antes de
    # declararlo votante:
    #
    #   coverage_score     firma 0,7894 media   vivo 0,8019    compatible
    #   thermal_anomalies  firma   447  SUMA    vivo 0-1        ~160x
    #   clear_passes       firma  5437  SUMA    vivo   34       ~160x
    #   revisita_dias      firma 0,6916 media   vivo 0,6916     identico
    assert "-336 hours" in fuente
    assert "tbl_cobertura_satelital_historico" in fuente, (
        "la ventana viva dejó de unir el histórico: la firma sí lo une")
    for agregacion in ("np.mean(cov)", "sum(ther)", "sum(clar)", "np.mean(revi)"):
        assert agregacion in fuente, f"falta la agregación {agregacion}"
    assert "if scores and not glob:" not in fuente, (
        "volvió el respaldo por ciclo, que escribía 34 donde el modelo "
        "aprendió 5.437")


def test_el_ciclo_ya_no_pide_tres_cajas_fijas():
    """El defecto estaba en el DEFAULT del pipeline, y el runner ahora le pasa
    siempre las zonas de la rotación."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import layer_runners

    fuente = inspect.getsource(layer_runners.GeodynamicLayerRunner)
    assert "zonas_a_medir(conn_z)" in fuente
    assert "fetch_alfa2_data(zones=zonas)" in fuente, (
        "el runner volvió a llamar sin zonas: se usaría el default mexicano")
