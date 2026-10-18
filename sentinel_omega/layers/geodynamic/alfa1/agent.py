"""
Alfa-1 Agent — Historical Space Weather Analysis
Source: OMNI NASA SPDF (30 years, 6h resolution)
Variables: Bz (IMF Z), Solar Wind velocity/density, Proton flux

Method (honesto, v2.5.1 — código y afirmación coinciden en ambas ramas):
  - CON modelo ONNX inyectado/cargado: inferencia RandomForest→ONNX sobre
    el vector de 10 features (rama ML).
  - SIN modelo (default hoy: no hay .onnx entrenado en el repo): conditioner
    por UMBRAL de Bz — reglas fijas sobre el campo magnético interplanetario.
Role: Base conditioning — long-range correlations
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

from sentinel_omega.core.shared.agent_base import BaseAgent, AgentSignal, SignalType


class Alfa1Agent(BaseAgent):

    FEATURES = [
        "bz_gsm", "plasma_speed", "proton_density",
        "proton_flux_10mev", "dst_index", "ae_index",
        "kp_index", "ap_index", "field_mag_avg", "flow_pressure"
    ]
    TARGET_WINDOW_H = 72

    def __init__(self):
        super().__init__(name="alfa1", layer="geodynamic")
        self._model = None            # sesión ONNX (inyectada o cargada)
        self._inference = None        # wrapper ONNXBotInference
        self._latest_features: Optional[np.ndarray] = None
        self._available: list = []    # columnas realmente ingeridas, en orden
        self._try_load_onnx()

    def _try_load_onnx(self) -> None:
        """Carga el modelo ONNX de alfa1 si existe en models/ (fail-soft).

        Si no hay archivo .onnx, el agente opera en la rama de umbral y lo
        dice explícitamente — nunca finge que corre ML.
        """
        try:
            from sentinel_omega.config.onnx_config import onnx_config
            from sentinel_omega.core.onnx_engine import (
                ONNXBotInference, ONNXModelLoader,
            )
            cfg = onnx_config.alfa1
            loader = ONNXModelLoader(onnx_config.runtime,
                                     models_dir=onnx_config.models_dir)
            session = loader.load_model(cfg)
            if session is not None:
                self._model = session
                self._inference = ONNXBotInference("alfa1", cfg, session)
                self.logger.info("Alfa-1: modelo ONNX cargado — rama ML activa")
            else:
                self.logger.info(
                    "Alfa-1: sin modelo ONNX — rama de umbral de Bz activa"
                )
        except Exception as e:
            self.logger.info(f"Alfa-1: ONNX no disponible ({e}) — rama de umbral")

    def set_model(self, session, inference=None) -> None:
        """Inyecta una sesión ONNX ya cargada (p. ej. desde el notebook)."""
        self._model = session
        if inference is not None:
            self._inference = inference
        else:
            try:
                from sentinel_omega.config.onnx_config import onnx_config
                from sentinel_omega.core.onnx_engine import ONNXBotInference
                self._inference = ONNXBotInference("alfa1", onnx_config.alfa1,
                                                   session)
            except Exception:
                self._inference = None

    def ingest(self, data: Dict[str, Any]) -> None:
        df = data.get("omni_dataframe")
        if df is None:
            self.logger.warning("No OMNI data provided")
            return

        available = [f for f in self.FEATURES if f in df.columns]
        self._available = available
        self._latest_features = df[available].values
        self.logger.info(f"Ingested {len(df)} OMNI records, {len(available)} features")

    def _bz_mean(self) -> Optional[float]:
        """Media de Bz por NOMBRE de columna — la posición 0 solo es Bz si
        bz_gsm venía en el dataframe; asumirlo silenciosamente corrompe la
        regla de umbral."""
        if self._latest_features is None or "bz_gsm" not in self._available:
            return None
        idx = self._available.index("bz_gsm")
        return float(np.nanmean(self._latest_features[:, idx]))

    # ─── Por qué alfa1 ya NO pregunta a su modelo desde aquí ──────────────
    #
    # Hasta el 2026-09-27 este agente hacía su propia inferencia ONNX, además
    # de la que hace `layer_runners._aplicar_modelos` con el vector canónico
    # del ciclo. Mismo modelo, DOS vectores, y en el ciclo 14419 dieron
    # respuestas opuestas: WATCH 72 % aquí, NO_SIGNAL 31 % allá.
    #
    # La causa, medida: `omni_dataframe` se arma solo con magnetómetro y
    # viento (`data_pipeline.fetch_alfa1_data`) y NUNCA ha tenido columna
    # `kp_index` --- el Kp se busca aparte y vive en `kp_series` de beta1. Así
    # que `agregados_omni` no producía Kp, `vector_para` ponía 0,0 en sus dos
    # posiciones, y el modelo leía ese 0,0 no como «no lo sé» sino como
    # «Kp = 0»: quietud geomagnética extrema. De ahí salía el WATCH.
    #
    # Lo que costó, contado en el Juez:
    #
    #     watch FALSO_POSITIVO, desde esta rama     792
    #     watch ACIERTO,        desde esta rama       5
    #     watch desde la rama de reglas               0
    #
    # 792 falsas alarmas contra 5 aciertos, y todas nacidas de un rasgo
    # AUSENTE. Eso hundió el peso de alfa1 al suelo (0,300) y cada rebuild lo
    # devolvía a 1,425, porque el camino histórico de las firmas no pasa por
    # este vector y era ciego al defecto.
    #
    # El veredicto del modelo ahora sale de un solo sitio: el vector canónico,
    # que es además EL QUE EL JUEZ REGISTRA. Si el modelo infiere sobre un
    # vector que no se guarda, el Juez califica una decisión que no puede
    # reproducir y el reentrenamiento aprende de otra cosa.
    #
    # Aquí queda la rama de reglas, que es lo que este agente sabe hacer solo.

    def analyze(self) -> AgentSignal:
        if self._latest_features is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0,
                                   reasoning="No data ingested")

        # Solo la regla. El modelo habla en `_aplicar_modelos`, con el vector
        # canónico del ciclo y una sola vez (ver el bloque de arriba).
        bz_mean = self._bz_mean()
        if bz_mean is None:
            # Sin columna bz_gsm no hay regla de Bz que aplicar — se dice.
            return self.emit_signal(
                SignalType.NEUTRAL, 0.2,
                data={"onnx": False, "bz_mean": None},
                reasoning="No bz_gsm column ingested — Bz threshold rule not applicable",
            )

        if bz_mean < -10:
            return self.emit_signal(
                SignalType.ALERT, 0.85,
                data={"onnx": False, "bz_mean": float(bz_mean)},
                reasoning=f"Bz threshold rule: severely negative ({bz_mean:.1f} nT) — geomagnetic storm conditions"
            )
        elif bz_mean < -5:
            return self.emit_signal(
                SignalType.ALERT, 0.5,
                data={"onnx": False, "bz_mean": float(bz_mean)},
                reasoning=f"Bz threshold rule: moderately negative ({bz_mean:.1f} nT) — elevated activity"
            )
        else:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.3,
                data={"onnx": False, "bz_mean": float(bz_mean)},
                reasoning=f"Bz threshold rule: normal range ({bz_mean:.1f} nT)"
            )

    def health_check(self) -> bool:
        return self._latest_features is not None
