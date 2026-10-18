"""
Sentinel Omega — ONNX Models Configuration
Central management for all bot ONNX models (Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Omega)
All models are ONNX runtime optimized — no TF/Torch dependencies at runtime
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class ONNXModelConfig:
    """Configuration for a single bot's ONNX model"""
    name: str
    model_path: str
    input_features: int
    output_shape: tuple
    confidence_threshold: float = 0.5
    enabled: bool = True

    def get_full_path(self, base_dir: str = "sentinel_omega/models") -> Path:
        """Get absolute path to model file (cwd-independent)."""
        base = Path(base_dir)
        if base.is_absolute() and base.exists():
            return base / self.model_path
        cand = base / self.model_path
        if cand.exists():
            return cand
        pkg = Path(__file__).resolve().parent.parent
        cand2 = pkg / "models" / self.model_path
        if cand2.exists():
            return cand2
        cand3 = pkg.parent / "sentinel_omega" / "models" / self.model_path
        return cand3 if cand3.exists() else cand2


@dataclass
class ONNXRuntimeConfig:
    """Global ONNX Runtime settings"""
    providers: list = field(default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
    graph_optimization_level: str = "ORT_ENABLE_ALL"
    intra_op_num_threads: int = 4
    inter_op_num_threads: int = 1
    session_options_kwargs: Dict = field(default_factory=dict)


@dataclass
class AllONNXModelsConfig:
    """All bots' ONNX models configuration"""

    models_dir: str = "sentinel_omega/models"

    alfa1: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="alfa1",
        model_path="alfa1_spaceweather_rf.onnx",
        input_features=10,
        output_shape=(1, 2),
        confidence_threshold=0.6,
        enabled=True
    ))

    # alfa2 VOTA (decisión del operador, 2026-10-02) pero vota con su REGLA:
    # su ONNX queda apagado hasta que tenga material real para entrenarse.
    #
    # Al reentrenarlo ese día el trazo lo dijo: `alfa2: hybrid real=23 +
    # boot=2500 → 2684`. O sea el 99 % sintético, de `train_onnx_bootstrap.
    # gen_alfa2`, que fabrica con `RNG.uniform/poisson/normal`. Y lo peor no es
    # la proporción: **cinco de sus ocho columnas llevan otra magnitud** que las
    # del vector vigente, y las dimensiones CUADRAN (8 = 8), así que
    # `test_onnx_dims` no puede verlo --- solo cuenta posiciones.
    #
    #   pos  prior sintetico        vector real
    #    3   total       0-19       densidad... no: revisita_dias  0-1,68
    #    4   revisit     1-14       coverage_score     0,30-0,93
    #    5   cloud       0-1        clear_passes       ~5.437 (suma de ventana)
    #    6   anomaly_rate 0-2       revisita_dias      0-1,68
    #    7   pad        ±0,4        thermal_anomalies  ~447
    #
    # Un modelo entrenado así no responde a los rasgos: responde a ruido en las
    # posiciones de los rasgos. `try_load_onnx` honra este `enabled` y cae a la
    # rama de reglas dejándolo en el log, que es el comportamiento honesto.
    #
    # PARA VOLVER A ENCENDERLO: que `load_juez_feedback` + firmas den >=
    # `MIN_SAMPLES` muestras REALES de alfa2 (el 2026-10-02 eran 23), reentrenar
    # con `--bots alfa2` y comprobar que el trazo dice `db-only (N)` y NO
    # `hybrid`. Su memoria crece sola: 19 firmas y 1.966 recurrencias en su
    # primera pasada, sobre 70 dias de historia satelital.
    alfa2: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="alfa2",
        model_path="alfa2_satellite_cnn.onnx",
        input_features=8,
        output_shape=(1, 2),
        confidence_threshold=0.65,
        enabled=False      # vota con su REGLA — ver el comentario de arriba
    ))

    # ── MODELOS APAGADOS POR CONSTANTES (2026-10-07) ──────────────────────
    #
    # Aplica a beta1, delta, loki y omega. Decisión del operador tras medir.
    #
    # Los ONNX reentrenados en `53f51e7` (5-oct 17:06) salieron devolviendo
    # prácticamente un número fijo. Desviación típica de la confianza sobre 27
    # ciclos vivos: beta2 0,0026 · loki 0,0100 · omega 0,0149 · beta1 0,0153 ·
    # delta 0,0183 · jupiter 0,0199, contra alfa1 **0,1663** --- el único que
    # varía de verdad, y por eso alfa1 se queda encendido.
    #
    # Un modelo con desviación 0,010 sobre 0,736 devuelve 0,736 ± 1,4 %: no
    # responde al dato, devuelve el promedio del objetivo. Consecuencia medida:
    # cinco bots alarmaron el 100 % de los ciclos durante dos días, con
    # ganancia de Molchan **0,81x a 2 h --- peor que el azar ---** y 159 falsos
    # positivos que hundieron seis pesos al suelo de 0,300.
    #
    # Los tests lo habían dicho desde el 5-oct y la suite llevaba roja sin que
    # nadie mirara: «el fantasma VOLVIÓ: con el Kp ausente sale WATCH 0.599»
    # (`test_fantasma_alfa1_kp_cero`) y «loki: el modelo volvió a alarmar con
    # kp_mean bajo (WATCH 0.7399) --- la fuga de procedencia regresó»
    # (`test_claves_omega_loki`).
    #
    # Efecto medido de apagar, contra lo que dice la REGLA de cada uno:
    #
    #     beta1  modelo  93 %  regla   0 %   -> alarma BAJA a 0 %
    #     delta  modelo 100 %  regla   0 %   -> alarma BAJA a 0 %
    #     loki   modelo 100 %  regla   0 %   -> alarma BAJA a 0 %
    #     omega  modelo 100 %  regla 100 %   -> SIN CAMBIO
    #
    # omega se apaga igual, y a propósito: su modelo tampoco informa, y
    # apagarlo DESTAPA que quien alarma es su regla --- con el modelo encima el
    # log decía «modelo WATCH sobre regla watch», y eso lo escondía.
    #
    # `beta2` tambien se apaga, y su caso corrige una incoherencia mia: lo
    # habia dejado encendido pensando que bastaba el umbral de confianza (emite
    # WATCH a 0,50 con 0,60 declarado, asi que A lo filtra), pero su desviacion
    # es **0,0026 --- la MAS constante de las ocho**. Y apagarlo baja su alarma
    # del 30 % al 4 %, que es lo que dice su regla. Dejar encendido el modelo
    # mas constante por un tecnicismo era justo el error que esta nota describe.
    #
    # NO se apagan: `alfa1` (el único con discriminación, 0,1663) ni `jupiter`
    # (su modelo dice NEUTRAL y está FRENANDO los watches de su regla: apagarlo
    # subiría su alarma del 0 % al 22 %).
    #
    # PARA RECONENDER cualquiera de los cuatro: reentrenar con un objetivo que
    # varíe y comprobar que la desviación típica de la confianza sube de 0,02.
    # Mientras siga constante, encenderlo es volver a alarmar sin información.
    beta1: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta1",
        model_path="beta1_schumann_fft.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=False      # constante — ver «MODELOS APAGADOS POR CONSTANTES»
    ))

    beta2: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta2",
        model_path="beta2_atmospheric_cnn.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.60,
        enabled=False      # constante 0,0026 — ver «MODELOS APAGADOS POR CONSTANTES»
    ))

    delta: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="delta",
        model_path="delta_financial_lstm.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.50,
        enabled=False      # constante — ver «MODELOS APAGADOS POR CONSTANTES»
    ))

    omega: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="omega",
        model_path="omega_espacial_rf.onnx",
        input_features=12,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=False      # constante — ver «MODELOS APAGADOS POR CONSTANTES»
    ))

    # loki y jupiter existían como modelos en disco --- el reentrenamiento
    # semanal produce los OCHO --- pero no tenían entrada aquí, así que
    # `try_load_onnx` devolvía None y nunca podían cargarse. Añadidos el
    # 2026-09-26: en una arquitectura de expertos, un experto sin modelo no
    # opina, y el que no opina tampoco puede ser corregido por el Juez.
    loki: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="loki",
        model_path="loki_unificado_rf.onnx",
        input_features=8,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=False      # constante — ver «MODELOS APAGADOS POR CONSTANTES»
    ))

    runtime: ONNXRuntimeConfig = field(default_factory=ONNXRuntimeConfig)

    def get_enabled_models(self) -> Dict[str, ONNXModelConfig]:
        models = {
            "alfa1": self.alfa1,
            "alfa2": self.alfa2,
            "beta1": self.beta1,
            "beta2": self.beta2,
            "loki": self.loki,
            "delta": self.delta,
            "omega": self.omega,
        }
        return {k: v for k, v in models.items() if v.enabled}

    def verify_models_exist(self) -> bool:
        for name, model_cfg in self.get_enabled_models().items():
            model_file = model_cfg.get_full_path(self.models_dir)
            if not model_file.exists():
                print(f"WARNING: Model not found: {model_file}")
                return False
        return True


onnx_config = AllONNXModelsConfig()
