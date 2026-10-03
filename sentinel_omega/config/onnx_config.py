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

    beta1: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta1",
        model_path="beta1_schumann_fft.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=True
    ))

    beta2: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta2",
        model_path="beta2_atmospheric_cnn.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.60,
        enabled=True
    ))

    delta: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="delta",
        model_path="delta_financial_lstm.onnx",
        input_features=16,
        output_shape=(1, 2),
        confidence_threshold=0.50,
        enabled=True
    ))

    omega: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="omega",
        model_path="omega_espacial_rf.onnx",
        input_features=12,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=True
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
        enabled=True
    ))

    jupiter: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="jupiter",
        model_path="jupiter_attention_rf.onnx",
        input_features=8,
        output_shape=(1, 2),
        confidence_threshold=0.55,
        enabled=True
    ))

    runtime: ONNXRuntimeConfig = field(default_factory=ONNXRuntimeConfig)

    def get_enabled_models(self) -> Dict[str, ONNXModelConfig]:
        models = {
            "alfa1": self.alfa1,
            "alfa2": self.alfa2,
            "beta1": self.beta1,
            "beta2": self.beta2,
            "loki": self.loki,
            "jupiter": self.jupiter,
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
