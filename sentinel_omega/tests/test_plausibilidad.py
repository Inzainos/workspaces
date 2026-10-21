"""Plausibilidad física en ingesta — el invariante de dominio (ítem 3).

Contrato (regla 12: el test ancla al COMPORTAMIENTO, no a literales del
código):
- valor imposible → None + warning (regla 7/8: basura de API ≠ medición)
- valor raro pero físico (huracán, tormenta X) → pasa INTACTO
- None/NaN → None (ausencia, no implausibilidad — lo distingue el llamador)
- campo sin rango declarado → pasa (fail-open: no romper lecturas viejas)
- el AQI 0 de OWM (imposible: escala 1–5) → None — el bug original
"""

from sentinel_omega.core.plausibilidad import validar


def test_bz_imposible_se_descarta():
    assert validar("bz_nT", 999.0) is None


def test_bz_fisico_extremo_pasa_intacto():
    # −50 nT en una tormenta severa: raro, físico, pasa
    assert validar("bz_nT", -50.0) == -50.0


def test_kp_filtrado_por_escala_noaa():
    assert validar("kp", 14.0) is None
    assert validar("kp", 9.0) == 9.0


def test_aqi_cero_imposible_none():
    # El bug original del 10-19: aqi default 0 en escala 1–5 de OWM
    assert validar("aqi", 0) is None
    assert validar("aqi", 1) == 1
    assert validar("aqi", 5) == 5


def test_none_y_nan_son_ausencia_no_implausibilidad():
    assert validar("kp", None) is None
    assert validar("kp", float("nan")) is None


def test_campo_sin_rango_fail_open():
    assert validar("campo_nuevo_sin_rango", 123.456) == 123.456


def test_fantasma_con_bz_imposible_no_explota():
    """El invariante en la fórmula: Bz corrupto → None → sin término Bz².

    Un Bz=999 haría fantasma=998.001; con el invariante, el término
    desaparece y los components llevan el NULL honesto."""
    from sentinel_omega.core.precursor.risk_calculator import compute_fantasma

    r = compute_fantasma(bz=999.0, viento=400.0, sch_wpc=None, kp=None)
    assert r.components["bz_nT"] is None
    assert r.bz_contribution == 0.0
    # solo queda el viento: 400 * 0.02 = 8.0
    assert abs(r.fantasma - 8.0) < 1e-9


def test_fantasma_con_valores_reales_no_cambia():
    from sentinel_omega.core.precursor.risk_calculator import compute_fantasma

    r = compute_fantasma(bz=-5.0, viento=400.0, sch_wpc=0.5, pressure_hpa=1000.0, kp=6.0)
    # bz² = 25, viento = 8, schumann = 0.75 → 33.75; presión <1008 añade 1.6;
    # kp 6 multiplica por 1.1
    assert abs(r.fantasma - (25 + 8 + 0.75 + 1.6) * 1.1) < 1e-9
