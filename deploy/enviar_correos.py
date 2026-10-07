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

    # Despacha el concentrado SI LE TOCA. `force=False` a propósito: este
    # script lo llama `rutinas_locales.sh` cada 15 min, y `force=True` saltaba
    # el temporizador --- su propio docstring lo dice: «force ignores the
    # timer». Medido el 2026-10-07: 54 digestos en un día, 4 por hora, con
    # `TG_DIGEST_MINUTES=60` declarado. Quien decide la cadencia es
    # `maybe_flush` contra la marca en disco, no este llamador.
    vig = get_vigilante(dry_run=False)
    rec = vig.flush_digest(force=False)

    if rec.sent:
        print("Telegram: DIGESTO_HORARIO enviado")
    elif not rec.html:
        # `maybe_flush` devolvió el registro vacío de «todavía no toca».
        print("Telegram: DIGESTO_HORARIO aún no toca (cadencia)")
    else:
        print(f"Telegram: DIGESTO_HORARIO {'dry-run/skipped' if rec.dry_run else 'falló'}")

    # Also send a system status heartbeat
    svc = AlertService()
    msg = AlertTemplates.heartbeat("Despacho manual de reportes/alertas")
    out = svc.dispatch(msg, channels=["telegram", "log"])
    # `dispatch` cuenta «buffered» como éxito (`alert_service.py:359`), así que
    # el viejo `'ok' if out.get('telegram')` imprimía ok para un heartbeat que
    # se queda en el buffer --- y en este `Type=oneshot` el buffer muere con el
    # proceso, o sea que NO llega a Telegram. Se dice cuál de las dos cosas
    # pasó, que es lo que el operador necesita leer.
    accion = out.get("telegram_action")
    if accion == "immediate":
        print("Telegram heartbeat: enviado")
    elif accion == "buffered":
        print("Telegram heartbeat: al buffer (no sale de este proceso)")
    else:
        print("Telegram heartbeat: falló")


if __name__ == "__main__":
    main()
