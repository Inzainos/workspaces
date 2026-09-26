"""El termómetro principal, auditado.

El Fantasma es el número que encabeza cada reporte y dispara el semáforo:

    fantasma = |Bz|² + viento×0,02 + Schumann×1,5

Auditado el 2026-09-25 contra 3.261 ciclos y 280.941 lecturas de clima espacial.
Tres cosas que el número solo no deja ver:

  · El viento solar pone un piso de 4,6 a 8,1 él SOLO, y el umbral VERDE es <5.
    Medido: VERDE salió **3 veces en 3.261 ciclos (0,1 %)**. El estado normal es
    AMARILLO (74,9 %), que por tanto no informa de nada.
  · **|Bz|² es SIMÉTRICO**: un Bz norte --- que *suprime* el acoplamiento con la
    magnetosfera --- puntúa igual que uno sur, aunque el encabezado del propio
    módulo diga «southward = negative = geomagnetically active». El 47,8 % de
    las lecturas tiene Bz positivo y **el 49 % del 5 % más alto viene de Bz
    norte**.
  · Schumann aporta 1,5 como máximo sobre ~12-35: un 4-10 %.

La fórmula NO se cambia --- movería 3.261 ciclos de historia y los umbrales del
semáforo con ellos ---, pero queda medida, expuesta en el reporte y con estos
tests para que la decisión de cambiarla sea informada.
"""
import pytest

from sentinel_omega.core.precursor.risk_calculator import (
    RISK_THRESHOLDS,
    classify_risk,
    compute_fantasma,
)


def test_el_bz_norte_puntua_igual_que_el_sur():
    """La simetría, escrita como test para que no se olvide."""
    sur = compute_fantasma(bz=-10.0, viento=400.0, sch_wpc=0.2)
    norte = compute_fantasma(bz=10.0, viento=400.0, sch_wpc=0.2)
    assert sur.fantasma == pytest.approx(norte.fantasma)
    assert norte.risk_level == "CRITICAL"       # con Bz tranquilo


def test_el_indice_marca_de_donde_viene():
    norte = compute_fantasma(bz=10.0, viento=400.0, sch_wpc=0.2)
    sur = compute_fantasma(bz=-10.0, viento=400.0, sch_wpc=0.2)
    assert norte.bz_es_norte is True
    assert sur.bz_es_norte is False


def test_contando_solo_el_sur_el_bz_norte_no_suma():
    norte = compute_fantasma(bz=10.0, viento=400.0, sch_wpc=0.2)
    assert norte.fantasma_solo_sur == pytest.approx(400 * 0.02 + 0.2 * 1.5)
    assert norte.fantasma_solo_sur < norte.fantasma / 10


def test_con_bz_sur_las_dos_cuentas_coinciden():
    sur = compute_fantasma(bz=-7.0, viento=450.0, sch_wpc=0.3)
    assert sur.fantasma_solo_sur == pytest.approx(sur.fantasma)


def test_el_viento_solo_ya_pasa_el_umbral_verde():
    """Por qué VERDE salió 3 veces en 3.261 ciclos."""
    quieto = compute_fantasma(bz=0.0, viento=400.0, sch_wpc=0.0)
    assert quieto.fantasma > RISK_THRESHOLDS["MODERATE"]
    assert quieto.risk_level != "LOW"
    # Para bajar de 5 haría falta un viento que casi nunca se da.
    muy_lento = compute_fantasma(bz=0.0, viento=200.0, sch_wpc=0.0)
    assert muy_lento.risk_level == "LOW"


def test_schumann_apenas_mueve_la_aguja():
    sin_sch = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=0.0)
    con_todo = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=1.0)
    salto = con_todo.fantasma - sin_sch.fantasma
    assert salto == pytest.approx(1.5)
    assert salto / con_todo.fantasma < 0.12      # menos del 12 % del total


def test_los_umbrales_siguen_donde_estaban():
    # Guarda: si alguien mueve el semáforo, que sea a propósito.
    assert RISK_THRESHOLDS == {"LOW": 0.0, "MODERATE": 5.0,
                               "HIGH": 15.0, "CRITICAL": 30.0}
    assert classify_risk(4.9) == "LOW"
    assert classify_risk(5.0) == "MODERATE"
    assert classify_risk(15.0) == "HIGH"
    assert classify_risk(30.0) == "CRITICAL"


def test_la_presion_baja_suma_pero_poco():
    normal = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=0.2)
    tormenta = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=0.2,
                                pressure_hpa=990.0)
    assert tormenta.pressure_modifier == pytest.approx(3.0)   # tope
    assert tormenta.fantasma > normal.fantasma


def test_el_kp_alto_multiplica():
    sin_kp = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=0.2, kp=4.0)
    con_kp = compute_fantasma(bz=-3.0, viento=450.0, sch_wpc=0.2, kp=7.0)
    assert sin_kp.kp_modifier == 1.0
    assert con_kp.kp_modifier == pytest.approx(1.2)
    assert con_kp.fantasma > sin_kp.fantasma


def test_el_reporte_ensena_el_desglose():
    import inspect
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deploy"))
    import generar_reporte
    fuente = inspect.getsource(generar_reporte)
    assert "De qué está hecho ese número" in fuente
    assert "Bz NORTE" in fuente
