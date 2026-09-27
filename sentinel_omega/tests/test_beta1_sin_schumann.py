"""Beta-1 es el latido y venía latiendo un 7,83 fabricado. Que no vuelva.

Auditoría del 2026-09-26, cerrando lo que el arreglo de Schumann en NULL dejaba
abierto. `ingest` hacía:

    self._schumann_hz = data.get("schumann_frequency", 7.83)
    self._schumann_activity = data.get("schumann_activity", 0.0)

CLAUDE.md dice que **todo se correlaciona contra Beta-1**. Con esos dos rellenos,
tres de sus cinco rutas de decisión quedaban muertas EN SILENCIO ---
`schumann_excited` (>15 %), `schumann_strong` (>30 %) y `composite_vibration`
--- mientras publicaba 7,83 Hz al 0 % como si lo hubiera medido. Y ese valor
viajaba en la figura cimática, que beta2 interpreta y que alimenta firmas.

Lo que estas pruebas defienden: sin lectura hay TRES estados, no dos, y la
ausencia se nombra. La ruta principal (espectro de Kp) sigue pudiendo alarmar.
"""

from __future__ import annotations

import numpy as np
import pytest

from sentinel_omega.layers.geodynamic.beta1.agent import Beta1Agent
from sentinel_omega.layers.geodynamic.beta2.agent import Beta2Agent

KP_CALMA = np.array([3.0] * 80)
# Oscilación rápida: alto `high_freq_ratio`, que es la ruta que NO depende
# de Schumann.
KP_AGITADO = np.array([1.0 if i % 2 else 8.0 for i in range(80)])


def _sin_schumann(kp=KP_CALMA):
    ag = Beta1Agent()
    ag.ingest({"kp_series": kp})
    return ag.analyze()


def test_sin_lectura_no_se_inventa_el_783_ni_el_cero():
    sig = _sin_schumann()
    assert sig.data["schumann_hz"] is None
    assert sig.data["schumann_activity_pct"] is None
    assert sig.data["schumann_sin_dato"] is True


def test_excitado_tiene_tres_estados_no_dos():
    """`None` es «no lo sé», y no debe confundirse con «no excitado»."""
    assert _sin_schumann().data["schumann_excited"] is None

    ag = Beta1Agent()
    ag.ingest({"kp_series": KP_CALMA, "schumann_activity": 5.0})
    assert ag.analyze().data["schumann_excited"] is False

    ag = Beta1Agent()
    ag.ingest({"kp_series": KP_CALMA, "schumann_activity": 25.0})
    assert ag.analyze().data["schumann_excited"] is True


def test_la_vibracion_compuesta_ausente_no_vale_cero():
    """`composite_vibration` = ratio × actividad / 100. Sin actividad no se
    midió la vibración, y eso no es «la vibración es cero»."""
    fig = _sin_schumann().data["cymatic_figure"]
    assert fig["composite_vibration"] is None
    assert fig["schumann_hz"] is None

    ag = Beta1Agent()
    ag.ingest({"kp_series": KP_CALMA, "schumann_activity": 40.0})
    assert ag.analyze().data["cymatic_figure"]["composite_vibration"] is not None


def test_la_ausencia_se_nombra_en_el_veredicto():
    assert "Schumann sin dato" in (_sin_schumann().reasoning or "")


def test_la_ruta_de_kp_sigue_pudiendo_alarmar_sin_schumann():
    """Lo importante: quitar el relleno NO silencia a beta1. Su ruta principal
    sale del espectro de Kp y no necesita Schumann."""
    from sentinel_omega.core.shared.agent_base import SignalType

    sig = _sin_schumann(KP_AGITADO)
    assert sig.signal_type == SignalType.ALERT
    razon = sig.reasoning or ""
    assert "high-frequency Kp" in razon
    # y dice con qué NO contó
    assert "solo espectro Kp" in razon, razon


def test_con_schumann_fuerte_sigue_dando_watch():
    """El camino bueno no se rompió: >30 % es `schumann_strong`."""
    from sentinel_omega.core.shared.agent_base import SignalType

    ag = Beta1Agent()
    ag.ingest({"kp_series": KP_CALMA, "schumann_frequency": 8.4,
               "schumann_activity": 35.0})
    sig = ag.analyze()
    assert sig.signal_type == SignalType.WATCH
    assert sig.confidence >= 0.45


def test_beta2_aguanta_la_figura_sin_schumann():
    """`figure.get("schumann_activity", 0)` NO protege de un None presente:
    el default solo actúa si falta la clave. `None > 20` reventaba."""
    fig = _sin_schumann().data["cymatic_figure"]
    ag = Beta2Agent()
    ag.ingest({"beta1_figure": fig})
    ag.analyze()          # no debe lanzar


def test_un_cero_medido_de_actividad_no_es_ausencia():
    """Tomsk puede medir 0 % de excitación de verdad, y eso es un dato."""
    ag = Beta1Agent()
    ag.ingest({"kp_series": KP_CALMA, "schumann_frequency": 7.83,
               "schumann_activity": 0.0})
    sig = ag.analyze()
    assert sig.data["schumann_activity_pct"] == 0.0
    assert sig.data["schumann_sin_dato"] is False
    assert sig.data["schumann_excited"] is False
    assert sig.data["cymatic_figure"]["composite_vibration"] == 0.0


def test_no_queda_relleno_en_el_codigo_de_la_clase():
    import inspect

    codigo = "\n".join(
        ln.split("#")[0] for ln in inspect.getsource(Beta1Agent).splitlines()
    )
    assert "7.83" not in codigo, "volvió el relleno de frecuencia"
    assert 'get("schumann_activity", 0' not in codigo
