"""
Padre / Árbitro — Hierarchical Consensus Validator
Asymmetric Loss: missed events penalized 10× more than false alarms.
VETO power: no alert without cross-family validation.

Hierarchy:
  - Padre punishes Alfa-1 and Beta-1 (30-year trained agents)
  - Alfa-1 validates Alfa-2 (14 years → validated against 30-year history)
  - Beta-1 validates Beta-2 (14 years → validated against 30-year history)
  - Delta provides financial cross-correlation (10 years)

Schumann correlation:
  Everything correlates against the Schumann resonance (Beta-1).
  If Schumann is perturbed alongside any other signal, that's a precursor.

Flow:
  1. #2 agents detect pattern → report to #1
  2. #1 agents validate against 30-year history
  3. If confirmed → escalate to Padre
  4. Padre cross-validates with OTHER agent families
  5. If pattern matches across families → alert confirmed
"""

from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import (
    PadreAgent, AgentSignal, ConsensusResult, SignalType
)


class GeodynamicPadre(PadreAgent):

    AGENT_TRAINING_YEARS = {
        "alfa1": 30, "beta1": 30,
        "alfa2": 14, "beta2": 14,
        "delta": 10,
    }

    FAMILY_MAP = {
        "alfa1": "space_weather",
        "alfa2": "space_weather",
        "beta1": "schumann_cymatics",
        "beta2": "schumann_cymatics",
        "delta": "financial_sentiment",
    }

    SENIOR_AGENTS = {"alfa1", "beta1"}
    JUNIOR_AGENTS = {"alfa2", "beta2"}
    SENIOR_FOR_JUNIOR = {"alfa2": "alfa1", "beta2": "beta1"}

    # Below this credibility weight, a bot's ALERT is demoted to WATCH:
    # the Padre no longer trusts it enough to escalate on its word alone.
    PESO_DEMOTION_THRESHOLD = 0.6

    def __init__(self):
        super().__init__(name="padre_geo", domain="geodynamic")
        self.miss_penalty = 10.0
        self.false_alarm_penalty = 1.0
        # Per-bot credibility weights, adjusted by disciplinary training
        # (castigo hijo x1 / Padre x2). Empty dict = everyone at 1.0.
        self.pesos_bots: Dict[str, float] = {}

    def set_pesos(self, pesos: Dict[str, float]) -> None:
        self.pesos_bots = dict(pesos or {})

    def _aplicar_pesos(
        self, validated: Dict[str, AgentSignal]
    ) -> Dict[str, AgentSignal]:
        """Weigh each bot's vote by its disciplinary credibility."""
        if not self.pesos_bots:
            return validated

        weighted: Dict[str, AgentSignal] = {}
        for name, sig in validated.items():
            peso = self.pesos_bots.get(name, 1.0)
            if peso == 1.0:
                weighted[name] = sig
                continue

            signal_type = sig.signal_type
            if (
                peso < self.PESO_DEMOTION_THRESHOLD
                and signal_type == SignalType.ALERT
            ):
                signal_type = SignalType.WATCH

            weighted[name] = AgentSignal(
                agent_name=sig.agent_name,
                signal_type=signal_type,
                confidence=min(sig.confidence * peso, 0.95),
                timestamp=sig.timestamp,
                data={**sig.data, "peso_bot": peso},
                reasoning=sig.reasoning,
            )
        return weighted

    def _validate_junior_with_senior(
        self, signals: List[AgentSignal]
    ) -> Dict[str, AgentSignal]:
        """
        #2 agents report to #1 agents. If a junior detects a pattern,
        it's only confirmed if the senior's 30-year history supports it.
        Returns validated signals (junior confirmed by senior, or senior alone).
        """
        by_name = {s.agent_name: s for s in signals}
        validated: Dict[str, AgentSignal] = {}

        for senior_name in self.SENIOR_AGENTS:
            if senior_name in by_name:
                validated[senior_name] = by_name[senior_name]

        for junior_name, senior_name in self.SENIOR_FOR_JUNIOR.items():
            junior = by_name.get(junior_name)
            senior = by_name.get(senior_name)
            if junior is None:
                continue

            junior_active = junior.signal_type in (
                SignalType.ALERT, SignalType.WATCH
            )
            senior_confirms = (
                senior is not None
                and senior.signal_type in (SignalType.ALERT, SignalType.WATCH)
            )

            if junior_active and senior_confirms:
                boost = min(junior.confidence * 1.2, 0.95)
                validated[junior_name] = AgentSignal(
                    agent_name=junior_name,
                    signal_type=junior.signal_type,
                    confidence=boost,
                    timestamp=junior.timestamp,
                    data={**junior.data, "senior_confirmed": True},
                    reasoning=f"{junior.reasoning} [confirmed by {senior_name}]",
                )
            elif junior_active and not senior_confirms:
                validated[junior_name] = AgentSignal(
                    agent_name=junior_name,
                    signal_type=SignalType.WATCH,
                    confidence=junior.confidence * 0.5,
                    timestamp=junior.timestamp,
                    data={**junior.data, "senior_confirmed": False},
                    reasoning=f"{junior.reasoning} [unconfirmed by {senior_name}]",
                )
            else:
                validated[junior_name] = junior

        if "delta" in by_name:
            validated["delta"] = by_name["delta"]

        return validated

    def _cross_family_check(
        self, validated: Dict[str, AgentSignal]
    ) -> Dict[str, bool]:
        """
        Check if multiple families show correlated patterns.
        A precursor is stronger when space weather + Schumann + financial align.
        """
        family_active = {}
        for agent_name, signal in validated.items():
            family = self.FAMILY_MAP.get(agent_name, "unknown")
            is_active = signal.signal_type in (SignalType.ALERT, SignalType.WATCH)
            if family not in family_active:
                family_active[family] = False
            if is_active:
                family_active[family] = True
        return family_active

    def _schumann_correlation(
        self, validated: Dict[str, AgentSignal]
    ) -> float:
        """
        Everything correlates against Schumann (Beta-1).
        If Schumann is excited while other agents fire, correlation is high.
        """
        beta1 = validated.get("beta1")
        if beta1 is None:
            return 0.0

        schumann_active = beta1.signal_type in (SignalType.ALERT, SignalType.WATCH)
        if not schumann_active:
            return 0.0

        other_active = sum(
            1 for name, sig in validated.items()
            if name != "beta1" and sig.signal_type in (SignalType.ALERT, SignalType.WATCH)
        )
        return min(1.0, other_active * 0.3 + beta1.confidence * 0.4)

    def evaluate_consensus(self, signals: List[AgentSignal]) -> ConsensusResult:
        if not signals:
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                agent_signals=signals,
                veto_active=True,
                veto_reason="No signals received",
            )

        validated = self._validate_junior_with_senior(signals)
        validated = self._aplicar_pesos(validated)
        family_status = self._cross_family_check(validated)
        schumann_corr = self._schumann_correlation(validated)

        active_families = sum(1 for active in family_status.values() if active)
        total_families = len(family_status)

        alert_signals = [
            s for s in validated.values()
            if s.signal_type == SignalType.ALERT
        ]
        watch_signals = [
            s for s in validated.values()
            if s.signal_type == SignalType.WATCH
        ]

        if active_families >= 2 and len(alert_signals) >= 2 and schumann_corr > 0.3:
            avg_conf = sum(s.confidence for s in alert_signals) / len(alert_signals)
            boosted = min(avg_conf + schumann_corr * 0.2, 0.95)
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.ALERT,
                confidence=boosted,
                agent_signals=list(validated.values()),
                metadata={
                    "families_active": active_families,
                    "schumann_correlation": schumann_corr,
                    "cross_family": family_status,
                },
            )

        if active_families >= 2 and (len(alert_signals) >= 1 or len(watch_signals) >= 2):
            avg_conf = sum(s.confidence for s in (alert_signals + watch_signals)) / max(len(alert_signals + watch_signals), 1)
            return ConsensusResult(
                consensus_reached=True,
                final_signal=SignalType.WATCH,
                confidence=avg_conf * 0.8,
                agent_signals=list(validated.values()),
                metadata={
                    "families_active": active_families,
                    "schumann_correlation": schumann_corr,
                },
            )

        if len(alert_signals) >= 1:
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.WATCH,
                confidence=0.35,
                agent_signals=list(validated.values()),
                metadata={"note": "Single-family alert, needs cross-validation"},
            )

        if self.veto_check(list(validated.values())):
            return ConsensusResult(
                consensus_reached=False,
                final_signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                agent_signals=list(validated.values()),
                veto_active=True,
                veto_reason="Insufficient cross-family agreement",
            )

        return ConsensusResult(
            consensus_reached=False,
            final_signal=SignalType.NEUTRAL,
            confidence=0.2,
            agent_signals=list(validated.values()),
        )
