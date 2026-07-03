"""
Sentinel Omega — ONNX Models Configuration
Central management for all bot ONNX models (Alfa-1, Alfa-2, Beta-1, Beta-2, Delta)
All models are ONNX runtime optimized — no TF/Torch dependencies at runtime
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ONNXModelConfig:
    """Configuration for a single bot's ONNX model"""
    name: str                      # e.g., "alfa1", "beta1", "delta"
    model_path: str                # Relative path to .onnx file
    input_features: int            # Number of input features
    output_shape: tuple            # Output tensor shape
    confidence_threshold: float = 0.5
    enabled: bool = True
    
    def get_full_path(self, base_dir: str = "sentinel_omega/models") -> Path:
        """Get absolute path to model file"""
        return Path(base_dir) / self.model_path


@dataclass
class ONNXRuntimeConfig:
    """Global ONNX Runtime settings"""
    providers: list = field(default_factory=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
    graph_optimization_level: str = "all"  # "disabled", "basic", "extended", "all"
    intra_op_num_threads: int = 4
    inter_op_num_threads: int = 1
    session_options_kwargs: Dict = field(default_factory=dict)


@dataclass
class AllONNXModelsConfig:
    """All bots' ONNX models configuration"""
    
    models_dir: str = "sentinel_omega/models"
    
    # Individual bot models
    alfa1: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="alfa1",
        model_path="alfa1_spaceweather_rf.onnx",
        input_features=10,
        output_shape=(1, 2),  # [confidence, signal_type]
        confidence_threshold=0.6,
        enabled=True
    ))
    
    alfa2: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="alfa2",
        model_path="alfa2_satellite_cnn.onnx",
        input_features=512,  # Satellite imagery features
        output_shape=(1, 3),
        confidence_threshold=0.65,
        enabled=True
    ))
    
    beta1: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta1",
        model_path="beta1_schumann_fft.onnx",
        input_features=256,  # FFT bins
        output_shape=(1, 4),  # [coherence, frequency, power, signal]
        confidence_threshold=0.55,
        enabled=True
    ))
    
    beta2: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="beta2",
        model_path="beta2_atmospheric_cnn.onnx",
        input_features=64,  # Weather feature maps
        output_shape=(1, 3),
        confidence_threshold=0.60,
        enabled=True
    ))
    
    delta: ONNXModelConfig = field(default_factory=lambda: ONNXModelConfig(
        name="delta",
        model_path="delta_financial_lstm.onnx",
        input_features=32,  # Time series features
        output_shape=(1, 2),  # [sentiment, confidence]
        confidence_threshold=0.50,
        enabled=True
    ))
    
    # Runtime configuration
    runtime: ONNXRuntimeConfig = field(default_factory=ONNXRuntimeConfig)
    
    def get_enabled_models(self) -> Dict[str, ONNXModelConfig]:
        """Get all enabled models as dict"""
        return {
            "alfa1": self.alfa1,
            "alfa2": self.alfa2,
            "beta1": self.beta1,
            "beta2": self.beta2,
            "delta": self.delta,
        } if all([self.alfa1.enabled, self.alfa2.enabled, self.beta1.enabled,
                   self.beta2.enabled, self.delta.enabled]) else {}
    
    def verify_models_exist(self) -> bool:
        """Check if all enabled model files exist"""
        for name, model_cfg in self.get_enabled_models().items():
            model_file = model_cfg.get_full_path(self.models_dir)
            if not model_file.exists():
                print(f"WARNING: Model not found: {model_file}")
                return False
        return True


# Global instance
onnx_config = AllONNXModelsConfig()
