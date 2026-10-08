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

    # El heartbeat que había aquí se RETIRÓ el 2026-10-07: era un no-op.
    #
    # Seguido de punta a punta: `AlertTemplates.heartbeat` produce un
    # `HEARTBEAT`, que está en `_ALWAYS_BUFFER_PREFIXES` --- al buffer **por
    # diseño**, porque la política 2 del vigilante manda inmediato solo lo sin
    # precedentes (`_ALWAYS_IMMEDIATE_TYPES` son SYSTEM_DEAD/DEAD/FALLO). Y
    # `ingest` solo hace `self.buffer.append`: no escribe en ninguna tabla
    # ---comprobado, cero `INSERT`/`execute` en su cuerpo--- así que en este
    # `Type=oneshot` el buffer muere con el proceso milisegundos después.
    #
    # Nunca llegó a Telegram. En el `launcher.py`, que es un proceso largo, el
    # mecanismo sí funciona: los heartbeats del rato viajan en el digesto de la
    # hora. Aquí el flush ocurre ANTES, así que ni eso.
    #
    # Y no se pierde información: el digesto que este mismo script despacha ya
    # lleva el estado del loop (`loop_alive` en `_build_digest`), y si el loop
    # muere hay `SYSTEM_DEAD`, que SÍ pagina al instante. Lo único que producía
    # era una línea de log diciendo «ok» sobre algo que no salía.


if __name__ == "__main__":
    main()
