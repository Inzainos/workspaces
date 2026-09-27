"""Un número en la unidad equivocada es peor que no dar el dato.

El parte de Telegram publicaba «Schumann: 0,21 Hz»: `orchestrator.py` leía
`comps.get("schumann_hz") or comps.get("schumann_wpc")` y `components` solo
lleva `schumann_wpc`, una fracción 0–1. Eso se arregló el 2026-09-26 en el
orquestador.

Medido el 2026-09-27: el FORMATEADOR seguía imprimiendo esa fracción sin
pestañear si alguien se la pasaba. La defensa era de una sola capa. Esta es la
segunda: el rango físico de la cavidad.
"""
from sentinel_omega.infrastructure.api.telegram import (
    HZ_SCHUMANN_MAX,
    HZ_SCHUMANN_MIN,
    format_centinela_threat,
    hz_schumann_valido,
)


def _linea_schumann(schumann):
    r = format_centinela_threat(risk=95.0, bz=-12.0, wind=650.0, schumann=schumann)
    assert r is not None, "el parte crítico no se generó"
    return next((l for l in r[1].splitlines() if "Schumann" in l), None)


def test_la_fundamental_se_publica():
    assert "7.83" in _linea_schumann(7.83)


def test_los_armonicos_se_publican():
    """14,3 · 20,8 · 27,3 · 33,8 son la misma señal, no ruido."""
    for hz in (14.3, 20.8, 27.3, 33.8):
        assert str(hz) in _linea_schumann(hz), f"se descartó el armónico {hz}"


def test_la_fraccion_wpc_no_pasa_por_hercios():
    """El defecto original: 0,21 publicado como Hz."""
    assert _linea_schumann(0.21) is None


def test_un_cero_no_es_una_lectura_de_la_cavidad():
    """Distinto del `or` falsy que se arregló antes: ahí el problema era
    descartar un 0 legítimo de Bz o de Kp. Cero HERCIOS no es una frecuencia
    medida, es ausencia de señal."""
    assert _linea_schumann(0.0) is None


def test_un_absurdo_no_pasa():
    assert _linea_schumann(500.0) is None
    assert _linea_schumann(-7.83) is None


def test_sin_dato_se_omite_la_linea():
    assert _linea_schumann(None) is None


def test_el_validador_devuelve_el_valor_no_un_booleano():
    """Quien llama necesita el número, para no volver a convertirlo."""
    assert hz_schumann_valido(7.83) == 7.83
    assert hz_schumann_valido("7.83") == 7.83
    assert hz_schumann_valido(None) is None
    assert hz_schumann_valido("no es un número") is None
    assert hz_schumann_valido(float("nan")) is None


def test_el_rango_cubre_la_cavidad_y_excluye_la_fraccion():
    assert HZ_SCHUMANN_MIN > 1.0 - 1e-9        # deja fuera cualquier 0–1
    assert HZ_SCHUMANN_MIN <= 7.83 <= HZ_SCHUMANN_MAX
    assert HZ_SCHUMANN_MAX >= 33.8             # el cuarto armónico entra
