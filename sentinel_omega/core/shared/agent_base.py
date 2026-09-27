"""
Base Agent Architecture for Sentinel Omega
All 6 agents inherit from this base.
Implements the hierarchical consensus pattern from the master architecture.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    WATCH = "watch"
    ALERT = "alert"
    NO_SIGNAL = "no_signal"


class ConfidenceLevel(Enum):
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class AgentSignal:
    agent_name: str
    signal_type: SignalType
    confidence: float
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class ConsensusResult:
    consensus_reached: bool
    final_signal: SignalType
    confidence: float
    agent_signals: List[AgentSignal] = field(default_factory=list)
    veto_active: bool = False
    veto_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    precursor_risk: Any = None
    precursor_detections: Any = None


class BaseAgent(ABC):

    def __init__(self, name: str, layer: str):
        self.name = name
        self.layer = layer
        self.logger = logging.getLogger(f"sentinel.{layer}.{name}")
        self._last_signal: Optional[AgentSignal] = None

    @abstractmethod
    def ingest(self, data: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def analyze(self) -> AgentSignal:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    def emit_signal(self, signal_type: SignalType, confidence: float,
                    data: Dict[str, Any] = None, reasoning: str = "") -> AgentSignal:
        signal = AgentSignal(
            agent_name=self.name,
            signal_type=signal_type,
            confidence=confidence,
            timestamp=time.time(),
            data=data or {},
            reasoning=reasoning,
        )
        self._last_signal = signal
        self.logger.info(f"Signal: {signal_type.value} @ {confidence:.2f}")
        return signal


class PadreAgent(ABC):
    """
    Árbitro Supremo — Asymmetric Loss Consensus Layer.
    No alert without mathematical consensus across ALL subordinate layers.
    Missed events penalized MORE than false alarms.
    """

    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.logger = logging.getLogger(f"sentinel.padre.{domain}")
        self.miss_penalty = 10.0
        self.false_alarm_penalty = 1.0

    @abstractmethod
    def evaluate_consensus(self, signals: List[AgentSignal]) -> ConsensusResult:
        pass

    def asymmetric_loss(self, predicted: bool, actual: bool) -> float:
        if not predicted and actual:
            return self.miss_penalty
        elif predicted and not actual:
            return self.false_alarm_penalty
        return 0.0

    def veto_check(self, signals: List[AgentSignal],
                   min_agreement: float = 0.66) -> bool:
        if not signals:
            return True

        non_neutral = [s for s in signals if s.signal_type != SignalType.NEUTRAL]
        if not non_neutral:
            return True

        dominant = max(set(s.signal_type for s in non_neutral),
                       key=lambda st: sum(1 for s in non_neutral if s.signal_type == st))
        agreement = sum(1 for s in non_neutral if s.signal_type == dominant) / len(non_neutral)

        return agreement < min_agreement


def valor_medido(datos, *claves):
    """El primer valor REAL entre varias claves, o None si ninguna lo trae.

    Sustituye al patrón `float(d.get("a") or d.get("b") or <constante>)`, que
    tenía dos filos y los dos se midieron el 2026-09-26:

    1. La constante de respaldo se volvía una MEDICIÓN a ojos del que decidía.
       Omega hacía `or 7.83` y luego `if abs(sch - 7.83) >= 0.4`: sin lectura la
       desviación daba cero y concluía «Schumann normal». Delta hacía `or 0.5`
       en `yield_spread` y luego `if yield_spread < 0`: sin dato, «spread
       normal». Ninguno había medido nada.
    2. El `or` trata un **0 medido** como ausencia. Bz cruzando cero --- que es
       precisamente cuando importa --- o Kp en calma saltaban a la clave
       siguiente o al respaldo.

    Aquí sólo None, NaN y lo no convertible son ausencia. El que llama decide
    qué hacer con None, y lo que no puede hacer es fingir que midió.
    """
    for clave in claves:
        v = datos.get(clave)
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv == fv:          # descarta NaN
            return fv
    return None
