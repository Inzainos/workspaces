"""
Unified Telegram Bot for Sentinel Omega
Routes alerts from all active layers through a single bot instance.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TelegramMessage:
    layer: str
    signal_type: str
    confidence: float
    summary: str
    details: str = ""


class SentinelTelegramBot:

    LAYER_EMOJIS = {
        "geodynamic": "🌍",
        "crypto": "₿",
        "bolsa": "📈",
        "lottery": "🎰",
    }

    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id
        self._enabled = bool(token and chat_id)

    def send_alert(self, msg: TelegramMessage) -> bool:
        emoji = self.LAYER_EMOJIS.get(msg.layer, "⚡")
        text = (
            f"{emoji} SENTINEL OMEGA — {msg.layer.upper()}\n"
            f"Signal: {msg.signal_type} ({msg.confidence:.0%})\n"
            f"{msg.summary}\n"
        )
        if msg.details:
            text += f"\n{msg.details}"

        if not self._enabled:
            logger.info(f"[DRY RUN] Telegram: {text}")
            return True

        try:
            import requests
            resp = requests.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            return resp.ok
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def send_heartbeat(self, status: dict) -> bool:
        layers_status = " | ".join(
            f"{'✅' if v else '❌'} {k}" for k, v in status.items()
        )
        return self.send_alert(TelegramMessage(
            layer="system",
            signal_type="HEARTBEAT",
            confidence=1.0,
            summary=f"Layers: {layers_status}",
        ))
