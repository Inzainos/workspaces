"""
Padre / Árbitro — Hierarchical Consensus Validator (v2.5.4 - Three Acts)
========================================================================
Architecture: SNT Families (Alfa/Beta/Delta) -> Omega -> Loki (Final Act)

Asymmetric Loss: missed events penalized 10x more than false alarms.
VETO power: no alert without cross-family validation.

Hierarchy:
  - Padre validates SNT Families against 30-year history
  - Omega provides spatial/cosmic corroboration
  - Loki provides Bayesian probability collapse (Final Act)

Corroboration (was \"Schumann correlation\", renamed 2026-10-10):
  The schumann_cymatics FAMILY (beta1 OR beta2) must be active for ALERT.
  Until 2026-10-10 this gate demanded beta1 SPECIFICALLY without reading a
  single Schumann data point --- with beta1's only live route at 0.02%,
  the system emitted 0 ALERTs in 4,566 production cycles. Family-level
  corroboration chosen by the operator (option B): beta1 (0.02%) or
  beta2 (~7% via fog/atmospheric stress) provides the second voice.

Flow:
  1. SNT Families detect patterns -> cross-family validation
  2. Familia schumann_cymatics corrobora (gate de ALERT)
  3. Omega activo sube el techo de confianza; Loki solo sube confianza
     (sus ramas de decision estan muertas por construccion, medido)
  4. ALERT cuando: >=2 familias + >=2 alertas + corroboration > 0.3
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
        "omega": 30,
        "loki": 0,  # Loki is not trained on history; it computes probability
    }

    FAMILY_MAP = {
        "alfa1": "space_weather",
        "alfa2": "space_weather",
        "beta1": "schumann_cymatics",
        "beta2": "schumann_cymatics",
        "delta": "financial_sentiment",
        "omega": "cosmic_correlation",
        "loki": "unified_field",  # Act 3 - standalone
    }

    SENIOR_AGENTS = {"alfa1", "beta1"}
    JUNIOR_AGENTS = {"alfa2", "beta2"}
    SENIOR_FOR_JUNIOR = {"alfa2": "alfa1", "beta2": "beta1"}

    PESO_DEMOTION_THRESHOLD = 0.6

    def __init__(self):
        super().__init__(name="padre_geo", domain="geodynamic")
        self.miss_penalty = 10.0
        self.false_alarm_penalty = 1.0
        self.pesos_bots: Dict[str, float] = {}
        self.asertividad_omega: float = 0.0
        self.asertividad_corum: float = 0.0
        self.omega_es_referencia: bool = False
        self.loki_probability: float = 0.0
        self.loki_threshold: float = 0.8

    def set_pesos(self, pesos: Dict[str, float]) -> None:
        self.pesos_bots = dict(pesos or {})

    def set_asertividades(self, omega: float, corum: float) -> None:
        self.asertividad_omega = float(omega or 0)
        self.asertividad_corum = float(corum or 0)
        self.omega_es_referencia = (
            self.asertividad_omega > 0
            and self.asertividad_omega >= self.asertividad_corum
        )

    def _aplicar_pesos(self, validated: Dict[str, AgentSignal]) -> Dict[str, AgentSignal]:
        if not self.pesos_bots:
            return validated
        weighted = {}
        for name, sig in validated.items():
            peso = self.pesos_bots.get(name, 1.0)
            if peso == 1.0:
                weighted[name] = sig
                continue
            signal_type = sig.signal_type
            if peso < self.PESO_DEMOTION_THRESHOLD and signal_type == SignalType.ALERT:
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

    def _validate_junior_with_senior(self, signals: List[AgentSignal]) -> Dict[str, AgentSignal]:
        by_name = {s.agent_name: s for s in signals}
        validated = {}
        for senior_name in self.SENIOR_AGENTS:
            if senior_name in by_name:
                validated[senior_name] = by_name[senior_name]
        for junior_name, senior_name in self.SENIOR_FOR_JUNIOR.items():
            junior = by_name.get(junior_name)
            senior = by_name.get(senior_name)
            if junior is None:
                continue
            junior_active = junior.signal_type in (SignalType.ALERT, SignalType.WATCH)
            senior_confirms = senior is not None and senior.signal_type in (SignalType.ALERT, SignalType.WATCH)
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
        for extra in ("omega", "loki"):
            if extra in by_name:
                validated[extra] = by_name[extra]
        return validated

    def _cross_family_check(self, validated: Dict[str, AgentSignal]) -> Dict[str, bool]:
        family_active = {}
        for agent_name, signal in validated.items():
            family = self.FAMILY_MAP.get(agent_name, "unknown")
            is_active = signal.signal_type in (SignalType.ALERT, SignalType.WATCH)
            if family not in family_active:
                family_active[family] = False
            if is_active:
                family_active[family] = True
        return family_active

    def _corroboracion_familiar(self, validated: Dict[str, AgentSignal]) -> float:
        """Corroboración de la FAMILIA schumann_cymatics: beta1 O beta2 activos.

        Hasta el 2026-10-10 esto exigía beta1 específicamente y se llamaba
        «correlación Schumann» SIN leer un solo dato de Schumann --- la
        fórmula era `otros_activos×0,3 + conf_beta1×0,4`, o sea «beta1
        activo». Con la única ruta viva de beta1 al 0,02 % de las ventanas
        (medido, BITACORA_2026-10-09 §4.2), la compuerta era un veto casi
        permanente: **0 ALERTs en 4.566 ciclos de producción**.

        El operador eligió la corroboración por FAMILIA (opción B): la
        segunda voz la da cualquiera de los dos bots de la familia ---
        beta1 (0,02 %) o beta2 (~7 % vía niebla/estrés, medido 203/2.863
        ciclos). El umbral 0,3 se mantiene: con dos familias activas (requisito
        previo) hay siempre ≥1 «otro activo», así que un bot familiar activo
        da 0,3 + 0,4×conf >= 0,5 --- la compuerta filtra «la familia no ve
        nada» sin volver a ser un veto eterno.
        """
        mejor = None
        for name in ("beta1", "beta2"):
            sig = validated.get(name)
            if sig is not None and sig.signal_type in (SignalType.ALERT, SignalType.WATCH):
                if mejor is None or sig.confidence > mejor.confidence:
                    mejor = sig
        if mejor is None:
            return 0.0
        other_active = sum(
            1 for name, sig in validated.items()
            if name not in ("beta1", "beta2")
            and sig.signal_type in (SignalType.ALERT, SignalType.WATCH))
        return min(1.0, other_active * 0.3 + mejor.confidence * 0.4)

    def _loki_validation(self, validated: Dict[str, AgentSignal]) -> Dict[str, Any]:
        loki_sig = validated.get("loki")
        if loki_sig is None:
            return {"loki_active": False, "loki_probability": 0.0, "loki_confirms": False, "loki_reasoning": "Loki signal not received"}
        self.loki_probability = loki_sig.confidence
        loki_confirms = loki_sig.signal_type in (SignalType.ALERT, SignalType.WATCH) and self.loki_probability >= self.loki_threshold
        return {"loki_active": True, "loki_probability": self.loki_probability, "loki_confirms": loki_confirms, "loki_reasoning": loki_sig.reasoning, "loki_signal_type": loki_sig.signal_type.value}

    def _dual_ask(self, omega_sig, corum_signal: SignalType, alert_signals, watch_signals):
        meta = {"omega_voto": None, "omega_referencia": self.omega_es_referencia, "asertividad_omega": self.asertividad_omega, "asertividad_corum": self.asertividad_corum, "dual_ask": None}
        if omega_sig is None:
            return meta
        meta["omega_voto"] = {"signal": omega_sig.signal_type.value, "confidence": omega_sig.confidence, "reasoning": (omega_sig.reasoning or "")[:300]}
        omega_alert = omega_sig.signal_type in (SignalType.ALERT, SignalType.WATCH)
        corum_alert = corum_signal in (SignalType.ALERT, SignalType.WATCH) or bool(alert_signals or watch_signals)
        if omega_alert and not corum_alert:
            meta["dual_ask"] = {"quien_primero": "omega", "pregunta_a": "corum", "texto": "Omega alerta -- que ven las familias del corum?"}
        elif corum_alert and not omega_alert:
            meta["dual_ask"] = {"quien_primero": "corum", "pregunta_a": "omega", "texto": "Corum alerta -- que ve Omega en espacial + Beta?"}
        elif omega_alert and corum_alert:
            meta["dual_ask"] = {"quien_primero": "ambos", "pregunta_a": "juez", "texto": "Alineados en alerta -- el Juez valida post-evento"}
        if self.omega_es_referencia and omega_alert:
            meta["omega_eleva_revision"] = True
        return meta

    def evaluate_consensus(self, signals: List[AgentSignal]) -> ConsensusResult:
        if not signals:
            return ConsensusResult(consensus_reached=False, final_signal=SignalType.NO_SIGNAL, confidence=0.0, agent_signals=signals, veto_active=True, veto_reason="No signals received")
        validated = self._validate_junior_with_senior(signals)
        validated = self._aplicar_pesos(validated)
        omega_sig = None
        loki_sig = None
        for k in list(validated.keys()):
            if str(k).lower() == "omega":
                omega_sig = validated.pop(k)
            elif str(k).lower() == "loki":
                loki_sig = validated.pop(k)
        family_status = self._cross_family_check(validated)
        corroboracion = self._corroboracion_familiar(validated)
        active_families = sum(1 for a in family_status.values() if a)
        alert_signals = [s for s in validated.values() if s.signal_type == SignalType.ALERT]
        watch_signals = [s for s in validated.values() if s.signal_type == SignalType.WATCH]
        omega_active = omega_sig and omega_sig.signal_type in (SignalType.ALERT, SignalType.WATCH)
        loki_validation = self._loki_validation({"loki": loki_sig} if loki_sig else {})
        loki_confirms = loki_validation["loki_confirms"]
        veto_active = False
        veto_reason = ""
        note = ""
        if (active_families >= 2 and len(alert_signals) >= 2
                and corroboracion > 0.3 and omega_active):
            # Loki ya NO elige entre dos ramas ALERT (elegía entre «THREE
            # ACTS» y «SNT + Omega; Loki pending», ambas ALERT --- confirmar
            # o no daba lo mismo, y su confirmación es imposible: posterior
            # ~1e-112). Solo sube la confianza cuando confirma.
            avg_conf = sum(s.confidence for s in alert_signals) / len(alert_signals)
            if loki_confirms:
                final, reached, conf = SignalType.ALERT, True, min(
                    avg_conf + corroboracion * 0.15
                    + loki_validation["loki_probability"] * 0.15, 0.98)
                note = "Familia corrobora + Omega + Loki (three acts)"
            else:
                final, reached, conf = SignalType.ALERT, True, min(
                    avg_conf + corroboracion * 0.2, 0.9)
                note = "Familia schumann_cymatics corrobora + Omega (Loki sin confirmar)"
        elif (active_families >= 2 and len(alert_signals) >= 2
                and corroboracion > 0.3):
            # Sin Omega (ausente o inactivo): ALERT con techo menor. Las dos
            # ramas VIEJAS que esto reemplaza estaban muertas --- una exigía
            # loki_confirms (imposible) y la otra exigía que Loki NO emitiera
            # señal (solo alcanzable en tests).
            avg_conf = sum(s.confidence for s in alert_signals) / len(alert_signals)
            final, reached, conf = SignalType.ALERT, True, min(
                avg_conf + corroboracion * 0.1, 0.85)
            note = "Familia schumann_cymatics corrobora; Omega ausente/inactivo"
        elif active_families >= 2 and (len(alert_signals) >= 1 or len(watch_signals) >= 2):
            avg_conf = sum(s.confidence for s in (alert_signals + watch_signals)) / max(len(alert_signals + watch_signals), 1)
            final, reached, conf = SignalType.WATCH, True, avg_conf * 0.8
            note = "Cross-family watch (SNT only)"
        elif len(alert_signals) >= 1:
            final, reached, conf = SignalType.WATCH, False, 0.35
            note = "Single-family alert, needs cross-validation"
        elif self.veto_check(list(validated.values())):
            final, reached, conf = SignalType.NO_SIGNAL, False, 0.0
            note = "Insufficient cross-family agreement"
            veto_active, veto_reason = True, note
        else:
            final, reached, conf = SignalType.NEUTRAL, False, 0.2
            note = "neutral"
        dual = self._dual_ask(omega_sig, final, alert_signals, watch_signals)
        if dual.get("omega_eleva_revision") and final in (SignalType.NEUTRAL, SignalType.NO_SIGNAL):
            final = SignalType.WATCH
            conf = max(conf, float(omega_sig.confidence) * 0.7 if omega_sig else conf)
            reached = False
            note = "Omega referencia eleva revision"
            dual["note_elevacion"] = note
            veto_active = False
        all_sigs = list(validated.values())
        if omega_sig:
            all_sigs.append(omega_sig)
        if loki_sig:
            all_sigs.append(loki_sig)
        return ConsensusResult(consensus_reached=reached, final_signal=final, confidence=conf, agent_signals=all_sigs, veto_active=veto_active, veto_reason=veto_reason, metadata={"families_active": active_families, "corroboracion_familiar": corroboracion, "cross_family": family_status, "note": note, "loki": loki_validation, **dual})