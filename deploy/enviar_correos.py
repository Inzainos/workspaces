"""
Despacho de reportes y alertas por Telegram (vía Consenso Vigilante).

El correo ha sido eliminado; todo pasa por Telegram usando el vigilante
de consenso (hourly digest + immediate pages para eventos sin precedentes).

Credenciales: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID en el .env.
"""

import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    from sentinel_omega.infrastructure.messaging.consenso_vigilante import get_vigilante
    from sentinel_omega.infrastructure.messaging.alert_service import AlertTemplates, AlertService

    # Flush the hourly digest - this sends the concentrado to Telegram
    vig = get_vigilante(dry_run=False)
    rec = vig.flush_digest(force=True)

    if rec.sent:
        print("Telegram: DIGESTO_HORARIO enviado")
    else:
        print(f"Telegram: DIGESTO_HORARIO {'dry-run/skipped' if rec.dry_run else 'falló'}")

    # Also send a system status heartbeat
    svc = AlertService()
    msg = AlertTemplates.heartbeat("Despacho manual de reportes/alertas")
    out = svc.dispatch(msg, channels=["telegram", "log"])
    print(f"Telegram heartbeat: {'ok' if out.get('telegram') else 'buffered/fail'}")


if __name__ == "__main__":
    main()
