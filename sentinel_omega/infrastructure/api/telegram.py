"""
Telegram Bot API connector — Alert dispatch for Sentinel Omega.

Sends real-time alerts when agents detect anomalies above threshold.
Used by the Padre agent and the orchestrator.

Requires: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID environment variables.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
TIMEOUT = 10


def _get_credentials() -> Optional[tuple]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.debug("Telegram credentials not configured")
        return None
    return token, chat_id


def send_alert(message: str, parse_mode: str = "HTML") -> bool:
    """Send a text alert to the configured Telegram chat."""
    creds = _get_credentials()
    if not creds:
        return False

    token, chat_id = creds
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        logger.info("Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


def format_geodynamic_alert(
    signal_type: str,
    confidence: float,
    details: str,
) -> str:
    """Format a geodynamic alert message."""
    return (
        f"<b>SENTINEL OMEGA — GEODYNAMIC ALERT</b>\n\n"
        f"Signal: <code>{signal_type}</code>\n"
        f"Confidence: <code>{confidence:.0%}</code>\n\n"
        f"{details}"
    )


def format_consensus_alert(
    layer: str,
    signal_type: str,
    confidence: float,
    agents_reporting: int,
) -> str:
    """Format a consensus-level alert from a Padre agent."""
    return (
        f"<b>SENTINEL OMEGA — {layer.upper()} CONSENSUS</b>\n\n"
        f"Final Signal: <code>{signal_type}</code>\n"
        f"Confidence: <code>{confidence:.0%}</code>\n"
        f"Agents: <code>{agents_reporting}</code>\n"
    )


def format_precursor_alert(
    precursor_type: str,
    display_name: str,
    value: float,
    details: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    lugar: Optional[str] = None,
) -> str:
    """Format a precursor detection alert with prediction windows."""
    from datetime import datetime, timedelta, timezone

    ahora = datetime.now(timezone.utc)
    location = ""
    if lugar:
        location = f"\n<b>Zona:</b> {lugar}"
    if lat is not None and lon is not None:
        location += f"\n<b>Coordenadas:</b> {lat:.2f}, {lon:.2f}"

    return (
        f"<b>SENTINEL OMEGA — ALERTA DE PRECURSOR</b>\n\n"
        f"<b>Tipo:</b> {display_name}\n"
        f"<b>Valor:</b> <code>{value:.2f}</code>\n"
        f"{location}\n\n"
        f"<b>VENTANAS DE PREDICCIÓN:</b>\n"
        f"  72h → {(ahora + timedelta(hours=72)).strftime('%d/%m %H:%M')} UTC\n"
        f"  48h → {(ahora + timedelta(hours=48)).strftime('%d/%m %H:%M')} UTC\n"
        f"  24h → {(ahora + timedelta(hours=24)).strftime('%d/%m %H:%M')} UTC\n\n"
        f"{details}\n\n"
        f"<i>{ahora.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
    )
