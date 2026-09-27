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
