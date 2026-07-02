"""
Juez — disciplinary audit engine over TBL_JUEZ_AUDITORIA.

Cycle contract:
  1. register_prediccion() — each cycle, what each bot/Padre said (PENDIENTE).
  2. evaluar_pendientes() — once a prediction's window expires, compare
     against observed truth (USGS events) and resolve it:
        ACIERTO         — predicted event, event happened
        FALLO           — predicted calm / stayed silent, event happened
        FALSO_POSITIVO  — predicted event, nothing happened
  3. Severity is asymmetric and recidivism-scaled: missing a KNOWN
     (consolidated) signature is the gravest failure. Falsos positivos are
     recorded but cheap — the system prefers over-alerting.
  4. The Juez never adjusts predictor weights in-cycle; its record feeds
     offline recalibration only.
"""

import json
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SEVERIDAD_FALLO_BASE = 10.0
SEVERIDAD_FALSO_POSITIVO = 1.0
SEVERIDAD_FALLO_FIRMA_CONOCIDA = 20.0  # missed a consolidated signature

ALERT_SIGNALS = ("alert", "watch")


class Juez:

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ── Registro ─────────────────────────────────────────────────

    def registrar_prediccion(
        self,
        bot_name: str,
        prediccion: str,
        confianza: float,
        ventana_h: int = 72,
        detalles: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> int:
        ts = timestamp or time.time()
        cur = self._conn.execute(
            "INSERT INTO TBL_JUEZ_AUDITORIA "
            "(timestamp, bot_name, prediccion, confianza, ventana_h, "
            " detalles_json) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, bot_name, prediccion, confianza, ventana_h,
             json.dumps(detalles or {})),
        )
        self._conn.commit()
        return cur.lastrowid

    def reincidencia(self, bot_name: str) -> int:
        """Historical count of FALLOs for a bot (drives severity scaling)."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA "
            "WHERE bot_name = ? AND resultado = 'FALLO'",
            (bot_name,),
        ).fetchone()
        return row[0]

    # ── Evaluación ───────────────────────────────────────────────

    def evaluar_pendientes(
        self,
        evento_ocurrido: bool,
        verdad: str = "",
        ahora: Optional[float] = None,
        firma_conocida: bool = False,
        multiplicador: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Resolve every PENDIENTE prediction whose window has expired.

        evento_ocurrido: whether a qualifying real event happened within the
        prediction window (caller checks USGS/catalog truth).
        firma_conocida: True when the missed event matched a consolidated
        signature — gravest failure class.
        """
        now = ahora or time.time()
        pendientes = self._conn.execute(
            "SELECT id, timestamp, bot_name, prediccion, confianza, ventana_h "
            "FROM TBL_JUEZ_AUDITORIA WHERE resultado = 'PENDIENTE'"
        ).fetchall()

        resueltos = []
        for pid, ts, bot, pred, conf, ventana_h in pendientes:
            if now - ts < ventana_h * 3600:
                continue  # window still open

            predijo_evento = pred.lower() in ALERT_SIGNALS
            if predijo_evento and evento_ocurrido:
                resultado, severidad = "ACIERTO", 0.0
            elif predijo_evento and not evento_ocurrido:
                resultado, severidad = "FALSO_POSITIVO", SEVERIDAD_FALSO_POSITIVO
            elif not predijo_evento and evento_ocurrido:
                resultado = "FALLO"
                base = (
                    SEVERIDAD_FALLO_FIRMA_CONOCIDA
                    if firma_conocida
                    else SEVERIDAD_FALLO_BASE
                )
                reincid = self.reincidencia(bot)
                severidad = base * (1.0 + 0.25 * reincid) * multiplicador
            else:
                resultado, severidad = "ACIERTO", 0.0  # calm predicted, calm held

            reincid_final = self.reincidencia(bot) + (1 if resultado == "FALLO" else 0)
            self._conn.execute(
                "UPDATE TBL_JUEZ_AUDITORIA SET resultado = ?, severidad = ?, "
                "verdad = ?, reincidencia = ?, resuelto_at = datetime('now') "
                "WHERE id = ?",
                (resultado, severidad, verdad, reincid_final, pid),
            )
            resueltos.append({
                "id": pid, "bot_name": bot, "prediccion": pred,
                "resultado": resultado, "severidad": severidad,
            })
            if resultado == "FALLO":
                logger.warning(
                    f"JUEZ: FALLO de {bot} (severidad={severidad:.1f}, "
                    f"reincidencia={reincid_final}) — predijo '{pred}', "
                    f"ocurrió: {verdad}"
                )

        if resueltos:
            self._conn.commit()
        return resueltos

    # ── Reportes ─────────────────────────────────────────────────

    def resumen_por_bot(self) -> Dict[str, Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT bot_name, resultado, COUNT(*), COALESCE(SUM(severidad),0) "
            "FROM TBL_JUEZ_AUDITORIA WHERE resultado != 'PENDIENTE' "
            "GROUP BY bot_name, resultado"
        ).fetchall()

        resumen: Dict[str, Dict[str, Any]] = {}
        for bot, resultado, n, sev in rows:
            entry = resumen.setdefault(bot, {
                "ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0,
                "severidad_total": 0.0,
            })
            entry[resultado] = n
            entry["severidad_total"] += sev

        for bot, entry in resumen.items():
            total = entry["ACIERTO"] + entry["FALLO"] + entry["FALSO_POSITIVO"]
            entry["asertividad"] = (
                round(entry["ACIERTO"] / total, 3) if total else 0.0
            )
        return resumen
