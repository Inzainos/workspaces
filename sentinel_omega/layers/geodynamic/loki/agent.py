"""
Loki Agent — Resonancia del Ciclo Mayor (Fractal-Bayesian, rediseñado 2026-10-12)
================================================================================
Acto 3 del consenso: el sistema menor (tormentas geomagnéticas) resonando con
el sistema mayor (la rotación solar de Carrington, 27,275 d).

REDESÑEADO contra la teoría del operador («TEORÍA DEL CAMPO UNIFICADO
FRACTAL», 2026-09-16), operacionalizada y MEDIDA contra 11.688 días
(1994-2025) en `deploy/medir_loki_teoria.py`:

  * Fourier (paso B de la teoría): la recurrencia de rotación solar EXISTE
    en los datos — picos contra el nulo de ruido rojo a 27,3 d (viento
    ×1,19; Bz ×1,53) y armónicos 13,5 d / 9,1 d.
  * Bayes (paso C): P(tormenta Kp>=5) = 0,94 % base → 3,19 % si hubo
    tormenta hace 26-29 d (ganancia 3,4×; control sin antecedente 0,88 %).
    Dispara el 3,2 % de los días (regla 8 ✓).
  * Gauss-Jordan (paso A): rango 4,00 EXACTO en calma y tormenta — las 7
    columnas del clima espacial son colineales SIEMPRE. Es LIMPIEZA
    (preprocesado), no señal: define las 4 dimensiones independientes del
    cubo, y con ello queda fuera el SVD de una fila del diseño viejo.
  * El «colapso» (resonancia ∧ grieta viva): P = 23 % contra 0,94 % —
    medido con n=13 días en 32 años (FRÁGIL, reportado con su n). La
    conjunción NO supera a la grieta sola (34 %): el aporte de Loki es el
    EJE DEL TIEMPO (el antecedente), no la conjunción.

Lo que se RETIRÓ (medido muerto el 2026-10-09, bitácora §4.3): el pipeline
SVD→FFT→dimensión fractal sobre UNA FILA degeneraba por construcción
(dimensión 2,0 en todos los ciclos) y el `phi_alignment` comparaba la norma
del vector (km/s mezclados con nT) contra φ=1,618 — posteriores de 1e-80 a
1e-214 contra umbrales de 0,5: muerto por ~112 órdenes de magnitud. La
Espiral Dorada de la teoría sobrevive como el CICLO en el tiempo (r=ae^bθ
→ la rotación de 27,275 d que barre los agujeros coronales recurrentes),
no como la norma de un vector contra 1,618.

Base Node: Tlaxcala, Mexico (19.318°N, -98.237°W) — el ancla de la teoría.
"""

from typing import Any, Dict, List, Optional

from sentinel_omega.core.shared.agent_base import (
    BaseAgent, AgentSignal, SignalType, valor_medido,
)


class LokiAgent(BaseAgent):
    TLAXCALA_LAT = 19.318
    TLAXCALA_LON = -98.237
    ROTACION_CARRINGTON_D = 27.275

    # ── Medido el 2026-10-12 contra 11.688 días (1994-2025) ──────────────────
    # deploy/medir_loki_teoria.py. Estos números son HISTORIA medida, no
    # parámetros de diseño: cambiarlos exige volver a medir.
    P_BASE = 0.0094          # P(tormenta Kp>=5 un día cualquiera)
    P_RESONANCIA = 0.0319    # P(tormenta | tormenta hace 26-29 d) — 3,4×
    P_COLAPSO = 0.2308       # P(tormenta | resonancia ∧ grieta) — n=13, frágil
    BZ_GRIETA = -5.0         # umbral de grieta: el mismo del Centinela (GRIETA)

    CONF_RESONANCIA = 0.55   # WATCH: pre-posiciona, no pagina
    CONF_COLAPSO = 0.70      # WATCH de confirmación: sube la confianza del consenso

    def __init__(self):
        super().__init__(name="loki", layer="geodynamic")
        self._data_vector: Optional[List[float]] = None
        self._medido: Dict[str, Optional[float]] = {}
        self._faltan: List[str] = []
        self._resonancia: Optional[Dict[str, Any]] = None
        self.logger.info(
            "Loki Agent (Resonancia del Ciclo Mayor) initialized at Tlaxcala Node")

    # ─── Qué lee Loki y con qué nombre llega ──────────────────────────────
    #
    # Medido el 2026-09-27: el runner mandaba `bz_gsm`, `schumann_resonance` y
    # `lod_ms`, y aquí se leía `bz`, `schumann_activity` y `lod` con respaldo
    # 0.0 --- así que Bz, Schumann y LOD valían CERO en todos los ciclos, y el
    # VIX, cuando faltaba, un 20 inventado. La regla decidía sobre un vector
    # fabricado y lo presentaba como medición.
    #
    # Ahora cada magnitud se busca por su nombre canónico y sus alias con
    # `valor_medido` (None, NaN y lo no numérico son ausencia), SIN respaldo.
    # Lo que falta queda en `self._faltan`; si falta una entrada CLAVE, Loki
    # emite NO_SIGNAL en vez de colapsar sobre ceros.
    #
    # `_data_vector` conserva 0.0 en las posiciones ausentes solo como
    # marcador interno del contrato de `vector_para` (el ONNX sigue
    # entrenado con 0 = «no lo sé»); la decisión nunca se toma sobre él.
    ENTRADAS = (
        ("bz", ("bz_gsm", "bz")),                                # IMF Bz GSM (nT)
        ("solar_wind", ("solar_wind",)),                         # km/s
        ("schumann_activity", ("schumann_activity", "schumann_resonance")),
        ("vix", ("vix",)),                                       # índice del miedo
        ("lod", ("lod_ms", "lod")),                              # Length of Day (ms)
    )
    # Sin campo magnético y viento solar no hay «campo unificado» que medir.
    ENTRADAS_CLAVE = ("bz", "solar_wind")

    def ingest(self, data: Dict[str, Any]) -> None:
        """Ingest multi-domain data + estado de resonancia del ciclo mayor."""
        data = dict(data or {})
        valores = {nombre: valor_medido(data, *alias) for nombre, alias in self.ENTRADAS}
        self._medido = valores
        self._faltan = [n for n, v in valores.items() if v is None]
        self._data_vector = [0.0 if v is None else float(v) for v in valores.values()]
        # La resonancia la calcula el runner contra la tabla horaria (histórico
        # medido, no live): dict con activa/dias_desde/ultima_tormenta_dias.
        # AUSENTE ≠ «no hay resonancia»: sin la clave no se decide sobre ella.
        res = data.get("resonancia_rotacion")
        self._resonancia = res if isinstance(res, dict) else None
        self.logger.info(
            f"Loki: Data vector ingested: {self._data_vector} "
            f"(sin dato: {self._faltan or 'ninguno'}) "
            f"resonancia={'activa' if self._resonancia_activa else ('medida, inactiva' if self._resonancia else 'sin medir')}")

    @property
    def _resonancia_activa(self) -> bool:
        return bool(self._resonancia and self._resonancia.get("activa"))

    def analyze(self) -> AgentSignal:
        if self._data_vector is None:
            return self.emit_signal(SignalType.NO_SIGNAL, 0.0, reasoning="No data vector ingested")

        faltan_clave = [n for n in self.ENTRADAS_CLAVE if n in self._faltan]
        if faltan_clave:
            # Sin sus entradas clave Loki no decide sobre ceros: lo dice.
            return self.emit_signal(
                SignalType.NO_SIGNAL, 0.0,
                data={"faltan": list(self._faltan), "sin_dato": True,
                      "medido": dict(self._medido)},
                reasoning="Loki sin dato: " + ", ".join(
                    f"{n}=sin dato" for n in self._faltan),
            )

        bz = self._medido.get("bz")
        data_base = {
            "medido": dict(self._medido),
            "faltan": list(self._faltan),
            "tlaxcala_node": [self.TLAXCALA_LAT, self.TLAXCALA_LON],
            "rotacion_carrington_d": self.ROTACION_CARRINGTON_D,
            "p_base": self.P_BASE,
        }

        # ── Sin resonancia medida: neutral honesto. Ausencia de la clave no
        # es «no hay resonancia» (regla 7); nunca se inventa el antecedente.
        if self._resonancia is None:
            return self.emit_signal(
                SignalType.NEUTRAL, 0.2,
                data={**data_base, "resonancia": None,
                      "bayesian_posterior": self.P_BASE},
                reasoning="Loki: sin resonancia medida este ciclo (el estado "
                          "del ciclo mayor no llegó); neutral por honesto, "
                          f"P(tormenta) base {self.P_BASE*100:.2f}%",
            )

        dias = self._resonancia.get("dias_desde")
        ultima = self._resonancia.get("ultima_tormenta_dias")
        res_data = {**data_base, "resonancia": dict(self._resonancia)}

        # ── COLAPSO RECURRENTE: la grieta viva llegó dentro de la ventana
        # de resonancia. Loki CONFIRMA (su rol en el consenso post-2026-10-10:
        # subir confianza cuando confirma, nunca alertar solo). El umbral de
        # grieta es el del Centinela (-5 nT), medido.
        if self._resonancia_activa and bz is not None and bz <= self.BZ_GRIETA:
            return self.emit_signal(
                SignalType.WATCH, self.CONF_COLAPSO,
                data={**res_data,
                      "bayesian_posterior": self.P_COLAPSO,
                      "colapso_recurrente": True},
                reasoning=(
                    f"COLAPSO RECURRENTE: grieta viva (Bz {bz:.1f} ≤ {self.BZ_GRIETA} nT) "
                    f"dentro de la ventana de resonancia (tormenta hace {dias} d, "
                    f"rotación de Carrington {self.ROTACION_CARRINGTON_D:.1f} d). "
                    f"P(tormenta) {self.P_COLAPSO*100:.0f}% contra base "
                    f"{self.P_BASE*100:.2f}% — medido 1994-2025, n=13 días: frágil, "
                    f"reportado con su n. Loki CONFIRMA, no alerta solo."),
            )

        # ── RESONANCIA ACTIVA (el WATCH lento del ciclo mayor): el
        # antecedente pre-posiciona al sistema; ~3,2 % de los días.
        if self._resonancia_activa:
            return self.emit_signal(
                SignalType.WATCH, self.CONF_RESONANCIA,
                data={**res_data,
                      "bayesian_posterior": self.P_RESONANCIA,
                      "colapso_recurrente": False},
                reasoning=(
                    f"Resonancia de rotación solar: hubo tormenta Kp>=5 hace "
                    f"{dias} d; la rotación de Carrington "
                    f"({self.ROTACION_CARRINGTON_D:.1f} d) devuelve los agujeros "
                    f"coronales recurrentes. P(tormenta hoy) {self.P_RESONANCIA*100:.2f}% "
                    f"contra base {self.P_BASE*100:.2f}% — ganancia "
                    f"{self.P_RESONANCIA/self.P_BASE:.1f}× medida 1994-2025 "
                    f"(control sin antecedente 0,88 %)."),
            )

        # ── Resonancia medida, inactiva: neutral con el contexto del ciclo.
        return self.emit_signal(
            SignalType.NEUTRAL, 0.2,
            data={**res_data, "bayesian_posterior": self.P_BASE,
                  "colapso_recurrente": False},
            reasoning=(
                f"Sin resonancia de rotación activa (última tormenta hace "
                f"{ultima if ultima is not None else '?'} d; la ventana es "
                f"26-29 d). P(tormenta) en base: {self.P_BASE*100:.2f}%."),
        )

    def health_check(self) -> bool:
        return self._data_vector is not None
