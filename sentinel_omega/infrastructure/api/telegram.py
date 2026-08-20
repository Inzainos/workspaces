"""
Telegram Bot API — alertas Sentinel Omega.

Hereda del Centinela V2 (Drive TELEGRAM_SENTINEL / COMMS_LINK):
  - anti-spam por tipo (cooldown 30 min)
  - heartbeat periódico
  - fallo de ciclo / restauración
  - prioridades: crítico, grieta Bz, tormenta, advertencia

Credenciales SOLO por entorno (nunca hardcode):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  TELEGRAM_COOLDOWN_S (opcional, default 1800)
  TELEGRAM_HEARTBEAT_S (opcional, default 14400 = 4 h)
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from sentinel_omega.infrastructure.api._http import get_session

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
TIMEOUT = 10

TH_RISK_WARN = float(os.environ.get("TG_TH_RISK_WARN", "0.60"))
TH_RISK_CRIT = float(os.environ.get("TG_TH_RISK_CRIT", "0.75"))
TH_BZ_CRACK = float(os.environ.get("TG_TH_BZ_CRACK", "-5.0"))
TH_WIND_STORM = float(os.environ.get("TG_TH_WIND_STORM", "600"))
COOLDOWN_S = int(os.environ.get("TELEGRAM_COOLDOWN_S", "1800"))
HEARTBEAT_S = int(os.environ.get("TELEGRAM_HEARTBEAT_S", "14400"))


class _AlertGate:
    """Anti-spam: mismo tipo no se reenvía hasta cooldown, salvo cambio de tipo."""

    def __init__(self):
        self.last_alert_time = 0.0
        self.last_msg_type = ""
        self.last_heartbeat = 0.0
        self.system_dead_alerted = False

    def allow(self, alert_type: str, cooldown: int = COOLDOWN_S) -> bool:
        now = time.time()
        if alert_type != self.last_msg_type or (now - self.last_alert_time) > cooldown:
            self.last_alert_time = now
            self.last_msg_type = alert_type
            return True
        return False

    def heartbeat_due(self) -> bool:
        return (time.time() - self.last_heartbeat) > HEARTBEAT_S

    def mark_heartbeat(self) -> None:
        self.last_heartbeat = time.time()


_GATE = _AlertGate()


def _get_credentials() -> Optional[Tuple[str, str]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.debug("Telegram credentials not configured")
        return None
    if "TU_TOKEN" in token or token.startswith("REPLACE"):
        logger.warning("Telegram token placeholder — configure TELEGRAM_BOT_TOKEN")
        return None
    return token, chat_id


def send_alert(message: str, parse_mode: str = "HTML") -> bool:
    """Envío directo (sin gate). Preferir send_alert_gated en ciclos."""
    creds = _get_credentials()
    if not creds:
        return False
    token, chat_id = creds
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    if len(message) > 4000:
        message = message[:3990] + "…"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        resp = get_session().post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        logger.info("Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def send_alert_gated(
    message: str,
    alert_type: str,
    parse_mode: str = "HTML",
    cooldown: int = COOLDOWN_S,
) -> bool:
    """Envía solo si el gate anti-spam lo permite."""
    if not _GATE.allow(alert_type, cooldown=cooldown):
        logger.debug(f"Telegram gated skip: {alert_type}")
        return False
    return send_alert(message, parse_mode=parse_mode)


def notify_online() -> bool:
    return send_alert(
        "🔵 <b>SISTEMA ONLINE</b>\nSentinel Omega vigilando telemetría y precursores."
    )


def notify_system_dead(minutes: float) -> bool:
    if _GATE.system_dead_alerted:
        return False
    ok = send_alert(
        f"💀 <b>FALLO DE CICLO PRINCIPAL</b>\n\n"
        f"Sin datos recientes (~{int(minutes)} min).\n"
        f"Revisar launcher / orchestrator."
    )
    if ok:
        _GATE.system_dead_alerted = True
    return ok


def notify_system_restored() -> bool:
    if not _GATE.system_dead_alerted:
        return False
    ok = send_alert(
        "🟢 <b>SISTEMA PRINCIPAL RESTAURADO</b>\nFlujo de ciclos reanudado."
    )
    if ok:
        _GATE.system_dead_alerted = False
    return ok


def maybe_heartbeat(status_line: str) -> bool:
    if not _GATE.heartbeat_due():
        return False
    ok = send_alert(
        f"💓 <b>REPORTE DE ESTADO</b>\n{status_line}\n"
        f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</i>"
    )
    if ok:
        _GATE.mark_heartbeat()
    return ok


def format_geodynamic_alert(signal_type: str, confidence: float, details: str) -> str:
    return (
        f"<b>SENTINEL OMEGA — GEODYNAMIC</b>\n\n"
        f"Signal: <code>{signal_type}</code>\n"
        f"Confidence: <code>{confidence:.0%}</code>\n\n"
        f"{details}"
    )


def format_consensus_alert(
    layer: str,
    signal_type: str,
    confidence: float,
    agents_reporting: int,
    dual_ask: Optional[Dict] = None,
    omega_voto: Optional[Dict] = None,
) -> str:
    lines = [
        f"<b>SENTINEL OMEGA — {layer.upper()} CONSENSUS</b>\n",
        f"Final: <code>{signal_type}</code> ({confidence:.0%})",
        f"Agents: <code>{agents_reporting}</code>",
    ]
    if omega_voto:
        lines.append(
            f"Ω Omega: <code>{omega_voto.get('signal')}</code> "
            f"({float(omega_voto.get('confidence') or 0):.0%})"
        )
    if dual_ask:
        lines.append(f"\n🔁 <b>Dual-ask</b>: {dual_ask.get('texto', '')}")
    return "\n".join(lines)


def format_precursor_alert(
    precursor_type: str,
    display_name: str,
    value: float,
    details: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    lugar: Optional[str] = None,
    lag_horas: Optional[float] = None,
) -> str:
    ahora = datetime.now(timezone.utc)
    location = ""
    if lugar:
        location = f"\n<b>Zona:</b> {lugar}"
    if lat is not None and lon is not None:
        location += f"\n<b>Coords:</b> {lat:.2f}, {lon:.2f}"

    ventanas = ""
    if lag_horas and lag_horas > 0:
        h = int(lag_horas)
        ventanas = (
            f"\n<b>Ventana típica firma:</b> ~{h}h "
            f"→ {(ahora + timedelta(hours=h)).strftime('%d/%m %H:%M')} UTC\n"
        )
    else:
        ventanas = (
            f"\n<b>Ventanas:</b>\n"
            f"  72h → {(ahora + timedelta(hours=72)).strftime('%d/%m %H:%M')} UTC\n"
            f"  48h → {(ahora + timedelta(hours=48)).strftime('%d/%m %H:%M')} UTC\n"
            f"  24h → {(ahora + timedelta(hours=24)).strftime('%d/%m %H:%M')} UTC\n"
        )

    return (
        f"<b>SENTINEL OMEGA — PRECURSOR</b>\n\n"
        f"<b>Tipo:</b> {display_name}\n"
        f"<b>Conf:</b> <code>{value:.0%}</code>"
        f"{location}{ventanas}\n"
        f"{details}\n\n"
        f"<i>{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
    )


def format_centinela_threat(
    risk: float,
    bz: float,
    wind: float,
    schumann: Optional[float] = None,
) -> Optional[Tuple[str, str]]:
    r = float(risk)
    if r > 1.5:
        r = r / 10.0
    bz = float(bz)
    wind = float(wind)

    if r >= TH_RISK_CRIT:
        return (
            "CRITICO",
            f"🔴 <b>ALERTA CRÍTICA</b>\n\n"
            f"⚠️ Fantasma: <b>{r:.2f}</b>\n"
            f"🧲 Bz: {bz:.1f} nT\n"
            f"💨 Viento: {wind:.0f} km/s"
            + (f"\n🌐 Schumann: {schumann:.2f} Hz" if schumann else ""),
        )
    if bz <= TH_BZ_CRACK:
        return (
            "GRIETA",
            f"🛡️ <b>FALLO DE ESCUDO (GRIETA)</b>\n\n"
            f"Bz colapsado: <b>{bz:.1f} nT</b>\n"
            f"Posible entrada de energía solar.",
        )
    if wind >= TH_WIND_STORM:
        return (
            "TORMENTA",
            f"🌪️ <b>TORMENTA SOLAR</b>\n\n"
            f"Viento: <b>{wind:.0f} km/s</b>\n"
            f"Presión sobre magnetosfera.",
        )
    if r >= TH_RISK_WARN:
        return (
            "ADVERTENCIA",
            f"🟠 <b>ACTIVIDAD ELEVADA</b>\n\n"
            f"Fantasma: {r:.2f}\n"
            f"Bz: {bz:.1f} | Viento: {wind:.0f}",
        )
    return None


def format_omega_dual_ask(meta: Dict) -> Optional[str]:
    dual = (meta or {}).get("dual_ask")
    if not dual:
        return None
    ov = (meta or {}).get("omega_voto") or {}
    ref = (meta or {}).get("omega_referencia")
    return (
        f"Ω <b>OMEGA / DUAL-ASK</b>\n\n"
        f"{dual.get('texto', '')}\n"
        f"Primero: <code>{dual.get('quien_primero')}</code> → "
        f"pregunta a <code>{dual.get('pregunta_a')}</code>\n"
        f"Omega voto: <code>{ov.get('signal', '?')}</code> "
        f"({float(ov.get('confidence') or 0):.0%})\n"
        f"Referencia: <code>{'SÍ' if ref else 'NO'}</code>"
    )


def dispatch_cycle_alerts(
    *,
    fantasma: Optional[float] = None,
    bz: Optional[float] = None,
    wind: Optional[float] = None,
    schumann: Optional[float] = None,
    consensus_signal: Optional[str] = None,
    consensus_conf: float = 0.0,
    agents_n: int = 0,
    metadata: Optional[Dict] = None,
    muro_msg: Optional[str] = None,
    elevated_risk_msg: Optional[str] = None,
) -> int:
    sent = 0
    meta = metadata or {}

    if fantasma is not None and bz is not None and wind is not None:
        threat = format_centinela_threat(fantasma, bz, wind, schumann)
        if threat:
            atype, html = threat
            if send_alert_gated(html, atype):
                sent += 1

    if consensus_signal and consensus_signal.lower() in ("alert", "watch"):
        msg = format_consensus_alert(
            "geodynamic",
            consensus_signal,
            consensus_conf,
            agents_n,
            dual_ask=meta.get("dual_ask"),
            omega_voto=meta.get("omega_voto"),
        )
        if send_alert_gated(msg, f"CONSENSUS_{consensus_signal.upper()}"):
            sent += 1

    omega_msg = format_omega_dual_ask(meta)
    if omega_msg and meta.get("dual_ask"):
        if send_alert_gated(omega_msg, "OMEGA_DUAL"):
            sent += 1

    if elevated_risk_msg:
        if send_alert_gated(elevated_risk_msg, "RISK_ELEVATED"):
            sent += 1

    if muro_msg:
        if send_alert_gated(muro_msg, "MURO_BREACH", cooldown=max(900, COOLDOWN_S // 2)):
            sent += 1

    return sent
