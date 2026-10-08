"""Omega rellenaba con 7,83 y con 0,0. Que no vuelva.

Auditoría del 2026-09-26, después del trabajo de Schumann en NULL. El arreglo
puso NULL en `TBL_PRECURSORES_COSMICOS`, pero **los consumidores seguían
fabricando el valor**:

    sch = float(d.get("schumann_hz") or d.get("schumann_mean") or 7.83)
    if abs(sch - 7.83) >= 0.4: ...

Sin lectura, `sch` valía 7,83, la desviación daba 0 y omega concluía «Schumann
normal» sin haber medido nada. Con Tomsk caído desde el 11 de septiembre, eso
pasaba en cada ciclo. Es el patrón de siempre al revés: no una señal medida que
no llega a la decisión, sino un marcador que se quita del registro y sigue
decidiendo.

Y el `or` tenía un segundo filo: trataba un **0 medido** como ausencia. Bz
cruzando cero o Kp en calma saltaban a la clave siguiente o al respaldo.
"""

from __future__ import annotations

import numpy as np
import pytest

from sentinel_omega.core.features_onnx import BOT_DIMS, vector_para
from sentinel_omega.core.shared.agent_base import SignalType
from sentinel_omega.layers.geodynamic.omega.agent import (
    SCHUMANN_DESVIACION_MINIMA_HZ,
    SCHUMANN_FUNDAMENTAL_HZ,
    OmegaAgent,
    _primero,
)


def test_un_cero_medido_no_es_ausencia():
    """El filo del `or`: Bz cruzando cero es un dato, no un hueco."""
    assert _primero({"bz": 0.0, "bz_nT": -5.0}, "bz", "bz_nT") == 0.0
    assert _primero({"kp": 0.0}, "kp", "kp_max") == 0.0
    # y lo ausente sigue siendo ausente
    assert _primero({}, "bz", "bz_nT") is None
    assert _primero({"bz": None}, "bz", "bz_nT") is None
    assert _primero({"bz": float("nan")}, "bz") is None
    assert _primero({"bz": "n/a", "bz_nT": 3.0}, "bz", "bz_nT") == 3.0


def test_el_783_es_referencia_no_relleno():
    """Dos papeles distintos que antes cumplía la misma constante."""
    assert SCHUMANN_FUNDAMENTAL_HZ == 7.83
    assert SCHUMANN_DESVIACION_MINIMA_HZ == 0.4
    import inspect

    # Solo CÓDIGO: los comentarios sí pueden nombrar el 7,83 para explicar por
    # qué se quitó.
    codigo = [
        ln.split("#")[0] for ln in inspect.getsource(OmegaAgent).splitlines()
    ]
    codigo = "\n".join(codigo)
    assert "7.83" not in codigo, "volvió el relleno al código de la clase"
    # y la referencia se usa por su nombre, no por su número
    assert "SCHUMANN_FUNDAMENTAL_HZ" in codigo


def test_sin_schumann_omega_no_dice_que_esta_normal():
    ag = OmegaAgent()
    ag.ingest({"bz_nT": -2.0, "kp_max": 3.0})      # sin Schumann
    sig = ag.analyze()
    razon = (sig.reasoning or "")
    assert "sin dato" in razon, razon
    # y no afirma una frecuencia que no midió
    assert "Hz" not in razon or "sin dato" in razon
    assert sig.data.get("schumann") is None


def test_con_schumann_desviado_si_suma_estres():
    """El camino bueno sigue funcionando: una desviación real se nota."""
    ag = OmegaAgent()
    ag.ingest({"bz_nT": -2.0, "kp_max": 3.0, "schumann_hz": 8.6})
    sig = ag.analyze()
    assert "8.60 Hz" in (sig.reasoning or "")


def test_sin_bz_ni_kp_lo_dice_en_vez_de_suponer_calma():
    ag = OmegaAgent()
    ag.ingest({})
    sig = ag.analyze()
    razon = sig.reasoning or ""
    assert "Bz=sin dato" in razon and "Kp=sin dato" in razon, razon


def test_el_vector_omite_lo_ausente_en_vez_de_inventarlo():
    """`vector_para` pone 0.0 donde falta un rasgo, que es con lo que se
    entrenó el modelo. Meter 7,83 sería preguntarle con un valor que nunca vio
    en esa posición."""
    ag = OmegaAgent()
    ag.ingest({"bz_nT": -4.0, "kp_max": 5.0})       # sin Schumann ni luna
    vec = ag._feature_vector()
    assert len(vec) == BOT_DIMS["omega"]
    # la posición 2 del orden canónico es schumann_mean
    from sentinel_omega.core.features_onnx import FEATURE_ORDER
    i = FEATURE_ORDER["omega"].index("schumann_mean")
    assert vec[i] == 0.0, f"se colocó {vec[i]} donde no hubo medición"


def test_con_schumann_el_vector_lo_lleva():
    ag = OmegaAgent()
    ag.ingest({"bz_nT": -4.0, "kp_max": 5.0, "schumann_mean": 8.31})
    from sentinel_omega.core.features_onnx import FEATURE_ORDER
    i = FEATURE_ORDER["omega"].index("schumann_mean")
    assert ag._feature_vector()[i] == pytest.approx(8.31)


def test_el_vector_sigue_el_orden_canonico():
    """No hay un segundo constructor de vector: manda features_onnx."""
    import inspect

    fuente = inspect.getsource(OmegaAgent._feature_vector)
    assert "vector_para" in fuente
    ag = OmegaAgent()
    ag.ingest({"bz_nT": -4.0})
    assert np.asarray(ag._feature_vector()).shape == (BOT_DIMS["omega"],)


# ─── El umbral de tormenta mira el Kp RECIENTE, no el máximo de 336 h ────────
#
# Medido el 2026-10-08: la regla de omega decía `WATCH` en **27 de 27** ciclos
# vivos con confianza **0,4900 exacta** --- o sea `stress = 0.35`, que solo sale
# de una condición. Era `kp >= 6`, y el Kp que leía venía de `CLAVES_KP_REGLA`,
# que empieza por `kp_max`: **el máximo de la ventana de 336 h**, que valía 6.0
# por una tormenta de la quincena anterior. El Kp real de esas horas: 0,2-2,0.
#
#     máximo de kp_max en 336 h   6.0   -> dispara «kp>=6»
#     Kp real de ahora            2.0
#
# Un umbral de tormenta instantánea aplicado al máximo de catorce días dice
# «hay tormenta» mientras la hubo alguna vez en la quincena.
#
# Y no se quedaba en omega: en el `FAMILY_MAP` del Padre omega es su PROPIA
# familia (`cosmic_correlation`), así que ese watch permanente mantenía una
# familia activa por sí sola y dejaba al consenso **a un solo watch** de su
# rama de alarma --- `active_families >= 2 and (alertas >= 1 or watches >= 2)`.
#
# La ironía: el arreglo del 2026-09-27, que omega dejara de escribir «Kp=sin
# dato» teniendo el ciclo Kp 1, fue el que le metió los agregados de ventana,
# porque le añadió los rasgos canónicos enteros.

_CICLO_REAL = {"bz_mean": -1.5, "kp_max": 6.0, "schumann_hz": 7.96}


def _senal(**extra):
    a = OmegaAgent()
    a.ingest({**_CICLO_REAL, **extra})
    return a.analyze()


def test_el_maximo_de_la_ventana_NO_dispara_el_umbral_de_tormenta():
    """El caso exacto de producción: kp_max 6.0 de la quincena, Kp real 0,96."""
    s = _senal(kp_reciente=0.96)
    assert s.signal_type is not SignalType.WATCH, (
        f"volvió el watch permanente: {s.signal_type.value} {s.confidence:.4f}")
    assert s.signal_type is SignalType.NEUTRAL
    assert s.data.get("stress", 0.0) < 0.30


def test_una_tormenta_DE_VERDAD_sigue_alarmando():
    """El arreglo no puede volverlo sordo: con Kp 6,2 AHORA, watch."""
    s = _senal(kp_reciente=6.2)
    assert s.signal_type is SignalType.WATCH
    assert s.data.get("stress", 0.0) >= 0.30


def test_sin_Kp_reciente_se_NOMBRA_la_ausencia_y_no_se_cae_al_maximo():
    """El respaldo a `kp_max` es justo el defecto: no existe a propósito.

    Pero tampoco se finge no tener dato cuando el ciclo trae el agregado ---
    eso sería el defecto del 2026-09-27 al revés, cuando omega escribía «Kp=sin
    dato» con el ciclo trayendo Kp 1. Se nombran los dos, cada uno con lo que
    es.
    """
    s = _senal()
    assert s.signal_type is SignalType.NEUTRAL
    assert "Kp reciente=sin dato" in s.reasoning, s.reasoning
    assert "336 h=6.0" in s.reasoning, (
        "no se reporta el agregado que sí hay: el parte parece una no-medición")
    assert "no vale de umbral" in s.reasoning
    assert s.data.get("kp") is None, "el umbral no puede haber usado el máximo"


def test_sin_NINGUN_Kp_lo_dice_sin_adornos():
    a = OmegaAgent()
    a.ingest({"bz_mean": -1.5, "schumann_hz": 7.96})
    s = a.analyze()
    assert "Kp=sin dato" in s.reasoning, s.reasoning


def test_el_umbral_de_tormenta_no_declara_kp_max_entre_sus_claves():
    """Que no vuelva por la puerta de las constantes."""
    from sentinel_omega.layers.geodynamic.omega.agent import CLAVES_KP_TORMENTA
    assert "kp_max" not in CLAVES_KP_TORMENTA
    assert "kp_max_72h" not in CLAVES_KP_TORMENTA
    assert "kp_reciente" in CLAVES_KP_TORMENTA


def test_el_VECTOR_sigue_usando_los_agregados_de_ventana():
    """La otra mitad, y es la que hace quirúrgico el arreglo: el modelo de
    omega aprendió con `kp_max` de 336 h, así que el VECTOR tiene que seguir
    llevándolo. Solo cambió la entrada de la REGLA."""
    from sentinel_omega.core.features_onnx import FEATURE_ORDER

    a = OmegaAgent()
    a.ingest({**_CICLO_REAL, "kp_reciente": 0.96, "kp_mean": 1.7})
    vec = a._feature_vector()
    i = FEATURE_ORDER["omega"].index("kp_max")
    assert vec[i] == 6.0, (
        f"el vector perdió el máximo de ventana que el modelo aprendió: "
        f"posición {i} vale {vec[i]}")


def test_el_runner_le_pasa_el_Kp_reciente_de_la_serie_viva():
    """Y que sea la MISMA cantidad con la que se calcula el Fantasma: si las
    dos ramas midieran cosas distintas, volveríamos al desajuste del Kp."""
    import inspect

    from sentinel_omega.infrastructure.pipeline import layer_runners
    fuente = inspect.getsource(layer_runners.GeodynamicLayerRunner._datos_omega)
    assert 'omega_data["kp_reciente"]' in fuente
    assert 'kp_series' in fuente
