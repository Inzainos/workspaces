"""Claves de omega/loki, un solo veredicto por modelo y la fuga de `kp_mean`.

Diagnóstico del 2026-09-27 (omega_diag). Desde las 13:59 CST alfa1, loki y
omega dijeron WATCH en 44 de 44 ciclos con la regla en neutral, y en la misma
fila del Juez convivían dos lecturas del MISMO modelo de omega:

    analyze()          NEUTRAL 0,42   vector todo ceros (claves que no llegaban)
    _aplicar_modelos   WATCH   0,72   vector canónico

Tres defectos, tres guardias:

1. Claves. La regla de omega buscaba `bz`/`kp` y el runner le pasaba un
   DataFrame con `bz_gsm`: «Bz=sin dato; Kp=sin dato» con Bz −0,93 en el
   ciclo. Loki leía `bz`, `schumann_activity` y `lod` con respaldo 0.0; el
   runner mandaba `bz_gsm`, `schumann_resonance` y `lod_ms`, más un viento
   400, un VIX 20 y un Schumann 7,83 inventados.
2. Dos veredictos del mismo modelo. omega ya no infiere en `analyze`.
3. Fuga. En el entrenamiento `kp_mean` vale 0 en el 100 % de las firmas
   (eventos) y, cuando viene, es NEUTRAL en el 100 % del Juez: el modelo lee
   la presencia como etiqueta. Con `kp_mean` 0,30 (media del Kp entero de 1
   minuto en calma) los tres modelos decían WATCH. Se callan hasta reentrenar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel_omega.core.shared.agent_base import AgentSignal, SignalType
from sentinel_omega.infrastructure.pipeline import layer_runners
from sentinel_omega.infrastructure.pipeline.layer_runners import (
    RASGOS_CON_FUGA,
    GeodynamicLayerRunner,
)
from sentinel_omega.layers.geodynamic.loki.agent import LokiAgent
from sentinel_omega.layers.geodynamic.omega.agent import OmegaAgent

# Rasgos reales del ciclo del Juez id 8583612 (2026-09-27 18:11:32 CST), con
# `kp_mean` en 0,30: el valor con el que los tres modelos cruzaron a WATCH.
CICLO_REAL = {
    "bz_mean": -0.93, "bz_min": -3.85, "bz_mean_72h": -0.7318,
    "bz_deriv_std": 0.3377, "viento_avg": 414.96, "viento_max": 467.6,
    "proton_max": 0.3953, "kp_mean": 0.30, "kp_max": 1.0, "kp_max_72h": 1.0,
    "sismo_count_win": 99.0, "sismo_count_72h": 27.0, "sismo_max_mag_win": 6.6,
    "fase_lunar": 0.5374, "es_sicigia": 1.0,
    "btc_volatilidad": 1.622, "btc_vol_max": 6.729, "btc_ret_win": 9.97,
    "btc_vol_72h": 0.3199, "vix": 14.87,
    "xray_mean": 2.01e-07, "xray_max": 3.89e-07, "trends_mean": 65.0,
    "delta_geo_coupling": 0.1122,
    "delta_cross_coupling": float("nan"), "delta_schumann_coupling": float("nan"),
}


def _senal(bot, tipo=SignalType.NEUTRAL, conf=0.3, texto="regla"):
    return AgentSignal(agent_name=bot, signal_type=tipo, confidence=conf,
                       timestamp=0.0, data={}, reasoning=texto)


def _runner(monkeypatch, rasgos):
    runner = object.__new__(GeodynamicLayerRunner)
    monkeypatch.setattr(runner, "_rasgos_del_ciclo", lambda: dict(rasgos),
                        raising=False)
    return runner


# ── (a) la fuga de kp_mean calla al modelo de alfa1, loki y omega ────────────

MAREAS = ["marea_total", "marea_luna", "marea_sol", "marea_sicigia",
          "marea_dist_luna", "marea_rango_24h", "marea_max_24h", "marea_deriv"]


def test_la_tabla_de_fugas_es_la_medida():
    assert RASGOS_CON_FUGA == {"alfa1": ["kp_mean"], "loki": ["kp_mean"],
                               "omega": ["kp_mean"], "beta2": MAREAS}


def test_las_mareas_de_beta2_son_las_del_vector_y_las_de_la_fuga_medida():
    """Nombres exactos: los de FEATURE_ORDER y los que mide el revisor G."""
    from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER
    orden = FEATURE_ORDER["beta2"][:BOT_DIMS["beta2"]]
    en_vector = [k for i, k in enumerate(orden)
                 if k.startswith("marea") and k not in orden[:i]]
    assert RASGOS_CON_FUGA["beta2"] == en_vector
    from sentinel_omega.tests.test_fuga_de_procedencia import (
        FUGAS_MEDIDAS_2026_09_27,
    )
    assert set(RASGOS_CON_FUGA["beta2"]) == set(FUGAS_MEDIDAS_2026_09_27["beta2"])


def test_beta2_con_marea_real_no_deja_hablar_al_modelo(monkeypatch):
    """Ciclo real con las 8 mareas presentes: el modelo de beta2 se calla,
    con los modelos REALES, y la regla conserva señal y texto."""
    ciclo = dict(CICLO_REAL, marea_total=1.6245, marea_luna=1.1851,
                 marea_sol=0.5018, marea_sicigia=0.8261, marea_dist_luna=0.9752,
                 marea_rango_24h=0.0262, marea_max_24h=1.6507,
                 marea_deriv=-0.00257, so2_kt_win=0.0, erupciones_win=0.0,
                 so2_kt_90d=0.0, erupciones_90d=0.0)
    runner = _runner(monkeypatch, ciclo)
    sig = _senal("beta2", SignalType.WATCH, 0.6, "regla beta2")
    GeodynamicLayerRunner._aplicar_modelos(runner, [sig])
    assert sig.signal_type is SignalType.WATCH and sig.confidence == 0.6
    assert sig.reasoning == "regla beta2"
    assert sig.data["onnx"] is False
    assert sig.data["onnx_callado"] == "fuga:marea"
    assert "gano" not in sig.data and "onnx_senal" not in sig.data


def test_kp_mean_030_no_produce_watch_del_modelo(monkeypatch):
    """Con los modelos REALES (sin simularlos) y el ciclo real."""
    runner = _runner(monkeypatch, CICLO_REAL)
    sigs = {b: _senal(b, texto=f"regla {b}") for b in ("alfa1", "loki", "omega")}
    GeodynamicLayerRunner._aplicar_modelos(runner, list(sigs.values()))
    for bot, sig in sigs.items():
        assert sig.signal_type is SignalType.NEUTRAL, f"{bot}: el modelo habló"
        assert sig.confidence == 0.3
        assert sig.reasoning == f"regla {bot}", "se reescribió el texto de la regla"
        assert sig.data["onnx"] is False
        assert sig.data["onnx_callado"] == "fuga:kp_mean"
        assert "onnx_senal" not in sig.data
        assert "gano" not in sig.data, "no hubo empate que resolver"


def test_al_bot_callado_ni_se_le_pregunta(monkeypatch):
    runner = _runner(monkeypatch, CICLO_REAL)
    preguntados = []
    monkeypatch.setattr(
        "sentinel_omega.core.onnx_mixin.senal_desde_rasgos",
        lambda bot, rasgos, **kw: preguntados.append(bot) or
        (SignalType.WATCH, 0.99, "WATCH"))
    sigs = [_senal(b) for b in ("alfa1", "loki", "omega", "beta2", "beta1")]
    GeodynamicLayerRunner._aplicar_modelos(runner, sigs)
    assert preguntados == ["beta1"], preguntados
    # el bot sin fuga sigue con la lógica del empate intacta
    beta1 = sigs[-1]
    assert beta1.data["gano"] == "modelo"
    assert "onnx_callado" not in beta1.data


def test_los_rasgos_del_runner_no_llevan_nan(monkeypatch):
    """Los acoplamientos de delta llegan NaN desde `_build_live_features`;
    el runner no los reparte como si fueran medidos."""
    import sentinel_omega.launcher as launcher
    monkeypatch.setattr(launcher, "_build_live_features",
                        lambda runner, conn=None: dict(CICLO_REAL))
    runner = object.__new__(GeodynamicLayerRunner)
    rasgos = GeodynamicLayerRunner._rasgos_del_ciclo(runner)
    assert "delta_cross_coupling" not in rasgos
    assert "delta_schumann_coupling" not in rasgos
    assert rasgos["delta_geo_coupling"] == pytest.approx(0.1122)
    assert rasgos["bz_mean"] == pytest.approx(-0.93)


# ── (b) omega y loki leen el Bz real del ciclo ──────────────────────────────

def _omni(bz=-0.93, viento=415.0):
    return pd.DataFrame({
        "time_tag": pd.date_range("2026-09-27 23:00", periods=3, freq="min"),
        "bz_gsm": [-2.0, np.nan, bz],
        "plasma_speed": [410.0, viento, np.nan],
    })


def test_omega_recibe_los_rasgos_del_ciclo_y_lee_el_bz(monkeypatch):
    runner = _runner(monkeypatch, CICLO_REAL)
    datos = runner._datos_omega({"omni_dataframe": _omni()},
                                {"schumann_frequency": None})
    assert "schumann_mean" not in datos and "schumann_std" not in datos
    ag = OmegaAgent()
    ag.ingest(datos)
    sig = ag.analyze()
    assert "Bz=sin dato" not in sig.reasoning, sig.reasoning
    assert "Kp=sin dato" not in sig.reasoning, sig.reasoning
    assert "Bz=-0.93" in sig.reasoning
    assert sig.data["bz"] == pytest.approx(-0.93)
    assert sig.data["kp"] == pytest.approx(1.0)
    # Schumann sigue sin lectura y se dice
    assert "Schumann=sin dato" in sig.reasoning


@pytest.mark.parametrize("clave", ["bz_mean", "bz_gsm", "bz", "bz_nT"])
def test_omega_acepta_los_alias_de_bz(clave):
    ag = OmegaAgent()
    ag.ingest({clave: -0.93, "kp": 1.0})
    sig = ag.analyze()
    assert sig.data["bz"] == pytest.approx(-0.93)
    assert "Bz=sin dato" not in sig.reasoning


def test_omega_alias_de_kp_viento_luna_en_el_vector():
    from sentinel_omega.core.features_onnx import FEATURE_ORDER, vector_para
    ag = OmegaAgent()
    ag.ingest(CICLO_REAL)
    # con los rasgos canónicos, el vector de omega es el de _aplicar_modelos
    assert np.allclose(ag._feature_vector(), vector_para("omega", CICLO_REAL))
    ag.ingest({"kp_mean": 0.5, "plasma_speed": 420.0, "moon_phase": 0.25,
               "syzygy": 0.0, "bz_gsm": -1.0})
    v = ag._feature_vector()
    o = FEATURE_ORDER["omega"]
    assert v[o.index("kp_mean")] == pytest.approx(0.5)
    assert v[o.index("viento_avg")] == pytest.approx(420.0)
    assert v[o.index("fase_lunar")] == pytest.approx(0.25)
    assert v[o.index("bz_mean")] == pytest.approx(-1.0)


def test_loki_lee_el_bz_real_del_ciclo():
    datos = GeodynamicLayerRunner._datos_loki(
        {"omni_dataframe": _omni()},
        {"schumann_activity": 21.46, "lod_ms": np.array([1.1, 1.2, np.nan])},
        {"vix": 14.87})
    assert datos == {"bz_gsm": pytest.approx(-0.93), "solar_wind": pytest.approx(415.0),
                     "schumann_activity": pytest.approx(21.46),
                     "vix": pytest.approx(14.87), "lod_ms": pytest.approx(1.2)}
    loki = LokiAgent()
    loki.ingest(datos)
    assert loki._data_vector[0] == pytest.approx(-0.93)
    assert loki._faltan == []
    sig = loki.analyze()
    assert sig.signal_type is not SignalType.NO_SIGNAL
    assert "sin dato" not in sig.reasoning
    assert sig.data["medido"]["bz"] == pytest.approx(-0.93)


@pytest.mark.parametrize("clave, pos", [("bz", 0), ("schumann_resonance", 2), ("lod", 4)])
def test_loki_acepta_alias(clave, pos):
    # El alias solo se usa si falta el nombre canónico (bz_gsm manda sobre bz).
    datos = {"solar_wind": 400.0, clave: 3.0}
    if clave != "bz":
        datos["bz_gsm"] = -0.5
    loki = LokiAgent()
    loki.ingest(datos)
    assert loki._data_vector[pos] == pytest.approx(3.0)


def test_loki_el_nombre_canonico_manda_sobre_el_alias():
    loki = LokiAgent()
    loki.ingest({"bz_gsm": -0.5, "bz": 3.0, "solar_wind": 400.0})
    assert loki._data_vector[0] == pytest.approx(-0.5)


# ── (c) loki sin entradas: NO_SIGNAL y nada inventado ───────────────────────

def test_runner_de_loki_no_inventa_defaults():
    datos = GeodynamicLayerRunner._datos_loki({}, {}, {})
    assert datos == {"bz_gsm": None, "solar_wind": None,
                     "schumann_activity": None, "vix": None, "lod_ms": None}
    # tampoco con un 7,83 de schumann_mean (clave que beta1 no produce)
    datos = GeodynamicLayerRunner._datos_loki(
        {"omni_dataframe": _omni()}, {"schumann_mean": 7.83}, {})
    assert datos["schumann_activity"] is None
    assert datos["vix"] is None


def test_loki_sin_entradas_da_no_signal():
    loki = LokiAgent()
    loki.ingest({"bz_gsm": None, "solar_wind": None, "schumann_activity": None,
                 "vix": None, "lod_ms": None})
    sig = loki.analyze()
    assert sig.signal_type is SignalType.NO_SIGNAL
    assert sig.confidence == 0.0
    assert sig.data["sin_dato"] is True
    assert set(sig.data["faltan"]) == {"bz", "solar_wind", "schumann_activity",
                                      "vix", "lod"}
    assert "20" not in str(sig.data["medido"].get("vix"))
    assert all(v is None for v in sig.data["medido"].values())


def test_loki_con_nan_es_sin_dato_y_no_toca_el_prior():
    loki = LokiAgent()
    prior = loki._bayesian_prior
    loki.ingest({"bz_gsm": float("nan"), "solar_wind": 410.0})
    sig = loki.analyze()
    assert sig.signal_type is SignalType.NO_SIGNAL
    assert "bz" in sig.data["faltan"]
    assert loki._bayesian_prior == prior


def test_loki_sin_schumann_ni_lod_sigue_pero_lo_anota():
    loki = LokiAgent()
    loki.ingest({"bz_gsm": -0.93, "solar_wind": 415.0, "vix": 14.87})
    sig = loki.analyze()
    assert sig.signal_type is not SignalType.NO_SIGNAL
    assert set(sig.data["faltan"]) == {"schumann_activity", "lod"}


# ── (d) omega.analyze() ya no corre ONNX ────────────────────────────────────

def test_omega_analyze_no_infiere(monkeypatch):
    import sentinel_omega.core.onnx_mixin as mixin

    def _prohibido(*a, **k):
        raise AssertionError("omega.analyze() volvió a correr ONNX")

    monkeypatch.setattr(mixin, "predict_signal", _prohibido)
    monkeypatch.setattr(mixin, "pad_vector", _prohibido)
    ag = OmegaAgent()
    assert ag._onnx is None
    ag.ingest(CICLO_REAL)
    sig = ag.analyze()
    assert "ONNX" not in sig.reasoning
    assert sig.signal_type is SignalType.NEUTRAL


def test_la_fuente_de_analyze_no_tiene_rama_onnx():
    import inspect
    fuente = inspect.getsource(OmegaAgent.analyze)
    for prohibido in ("predict_signal", "pad_vector", "self._onnx"):
        assert prohibido not in fuente, prohibido


# --------------------------------------------------------------------------
# La marca de fuga llega al Juez (juez_cycle_register copia `onnx_callado`)
# --------------------------------------------------------------------------

class _JuezEspia:
    def __init__(self):
        self.filas = []

    def registrar_prediccion(self, **kw):
        self.filas.append(kw)


def _registrar(sigs):
    from types import SimpleNamespace
    from sentinel_omega.infrastructure.pipeline.juez_cycle_register import (
        register_cycle_predictions,
    )
    juez = _JuezEspia()
    geo = SimpleNamespace(final_signal=SignalType.NEUTRAL, confidence=0.3,
                          agent_signals=sigs)
    n = register_cycle_predictions(juez, geo)
    assert n == len(sigs)
    return {f["bot_name"]: f["detalles"] for f in juez.filas}


def test_la_marca_de_fuga_llega_a_detalles_json(monkeypatch):
    """Camino real: el runner calla a alfa1 por kp_mean y el registrador lo
    guarda en el `detalles` que acaba en detalles_json."""
    runner = _runner(monkeypatch, CICLO_REAL)
    sig = _senal("alfa1", texto="regla alfa1")
    GeodynamicLayerRunner._aplicar_modelos(runner, [sig])
    assert sig.data["onnx_callado"] == "fuga:kp_mean"
    det = _registrar([sig])["alfa1"]
    assert det["onnx_callado"] == "fuga:kp_mean"
    assert det["onnx"] is False
    import json
    assert json.loads(json.dumps(det))["onnx_callado"] == "fuga:kp_mean"


def test_sin_marca_no_se_inventa_la_clave():
    sig = _senal("beta1", texto="regla beta1")
    sig.data = {"onnx": True, "onnx_senal": "NEUTRAL", "onnx_conf": 0.4,
                "regla_senal": "NEUTRAL", "regla_conf": 0.3, "gano": "modelo"}
    det = _registrar([sig])["beta1"]
    assert "onnx_callado" not in det
    for clave in ("onnx", "onnx_senal", "onnx_conf", "regla_senal",
                  "regla_conf", "gano"):
        assert det[clave] == sig.data[clave]

