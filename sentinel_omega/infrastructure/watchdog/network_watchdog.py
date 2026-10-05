
"""
Sentinel Omega — Network & Agent Watchdog
Levanta el sistema si ve desconexiones o fallos de red/servicio.

- Chequea conectividad cada 60s (ping 8.8.8.8 + 1.1.1.1 + http google)
- Chequea health del agente (ollama + DB) via agent_bridge si existe
- Si falla N veces seguidas => intenta `systemctl --user restart sentinel-omega` + watchdog alert
- CADA ciclo sano asegura que sentinel-omega y los dashboards de usuario
  (API FastAPI 8787 + web React 5173) sigan activos: unidad inactiva =>
  `systemctl --user restart` + aviso por Telegram en la primera detección
  (2026-09-28). `Restart=always` cubre el proceso muerto; esto cubre la
  unidad DETENIDA (stop manual o StartLimit agotado).
- El dashboard Streamlit (8510) es unit de SISTEMA (root): el watchdog solo
  puede DETECTAR que cayó y avisar con el comando manual — `sudo -n` falla
  sin sudoers passwordless y un servicio de usuario no puede dar más.
- Notifica via AlertService (Telegram/Log) cuando vuelve la red
- Corre como unit de USUARIO systemd sentinel-omega-watchdog.service (Restart=always);
  todas las llamadas usan `systemctl --user` (las units de sistema estan enmascaradas)

Ojo operador: si DETIENE una unidad a propósito (mantenimiento), este watchdog
la re-levantará en <=60s. Detenga primero el watchdog
(`systemctl --user stop sentinel-omega-watchdog`) o quite la unidad de
WATCHDOG_RESTORE_UNITS en deploy/.env.

No requiere credenciales para chequear; si hay Telegram, notifica.
"""
from __future__ import annotations
import time, subprocess, logging, socket, os
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WATCHDOG] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECK_INTERVAL_S = int(os.environ.get('WATCHDOG_INTERVAL_S', '60'))
FAIL_THRESHOLD = int(os.environ.get('WATCHDOG_FAIL_THRESHOLD', '3'))
PING_HOSTS = ['8.8.8.8','1.1.1.1']
HTTP_HOSTS = ['https://www.google.com','https://api.nasa.gov']

# Sentinel corre como units de USUARIO: siempre `systemctl --user`.
SYSTEMCTL = ['systemctl', '--user']
# Units (manager de usuario) a asegurar CADA ciclo sano. Desde 2026-09-28
# incluyen los dashboards: "cuando se levanta Sentinel se levanta el
# dashboard" también cuando el que lo levanta es el watchdog.
RESTORE_UNITS = [u.strip() for u in os.environ.get(
    'WATCHDOG_RESTORE_UNITS',
    'sentinel-omega,sentinel-omega-dashboard-api,sentinel-omega-dashboard-web'
).split(',') if u.strip()]

# El Streamlit legacy es unit de SISTEMA (root, /etc/systemd/system): solo
# detectable por puerto. Desactivable con WATCHDOG_STREAMLIT_CHECK=0.
STREAMLIT_CHECK = os.environ.get('WATCHDOG_STREAMLIT_CHECK', '1') == '1'
STREAMLIT_HOST = os.environ.get('WATCHDOG_STREAMLIT_HOST', '127.0.0.1')
STREAMLIT_PORT = int(os.environ.get('WATCHDOG_STREAMLIT_PORT', '8510'))
STREAMLIT_UNIT = os.environ.get('WATCHDOG_STREAMLIT_UNIT', 'sentinel-omega-dashboard')

# Estado del ciclo anterior por clave (nombre de unidad o 'streamlit') para
# avisar SOLO en la transición activa->caída, no cada ciclo.
_previo: dict = {}


def _user_systemd_env() -> dict:
    """Entorno para `systemctl --user` aun desde cron/ssh sin sesion.

    Devuelve una COPIA de os.environ (no muta el entorno global) con
    XDG_RUNTIME_DIR=/run/user/<uid> y el bus de usuario si faltan.
    """
    env = dict(os.environ)
    if not env.get('XDG_RUNTIME_DIR'):
        env['XDG_RUNTIME_DIR'] = f'/run/user/{os.getuid()}'
    if not env.get('DBUS_SESSION_BUS_ADDRESS'):
        env['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path={env['XDG_RUNTIME_DIR']}/bus"
    return env


def _systemctl(*args: str, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run([*SYSTEMCTL, *args], capture_output=True, text=True,
                          timeout=timeout, env=_user_systemd_env())


def _sudo_systemctl(*args: str) -> subprocess.CompletedProcess:
    """systemctl de SISTEMA con sudo NO-interactivo.

    Sin sudoers passwordless devuelve rc!=0 con `sudo: a password is
    required` — eso es lo esperado en esta máquina y el aviso al operador
    lleva el comando a mano. Nunca cuelga pidiendo contraseña.
    """
    return subprocess.run(['sudo', '-n', 'systemctl', *args],
                           capture_output=True, text=True, timeout=30)


def _puerto_ok(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except Exception:
        return False


def has_network() -> bool:
    # 1) DNS + TCP check (sin depender de ping binario)
    for host in PING_HOSTS:
        try:
            socket.create_connection((host, 53), timeout=5)
            return True
        except Exception:
            continue
    # 2) fallback http
    try:
        import httpx
        for url in HTTP_HOSTS:
            try:
                with httpx.Client(timeout=5.0, follow_redirects=True) as c:
                    r = c.get(url)
                    if r.status_code < 500:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def service_active(name: str) -> bool:
    try:
        r = _systemctl('is-active', name, timeout=5)
        return r.stdout.strip() == 'active'
    except Exception:
        return False


def try_restart(services):
    for svc in services:
        try:
            logger.warning(f'Restart {svc}')
            r = _systemctl('restart', svc, timeout=30)
            if r.returncode != 0:
                logger.error(f'restart {svc} rc={r.returncode}: {(r.stderr or "").strip()}')
        except Exception as e:
            logger.error(f'restart {svc} fail: {e}')


def agent_ok() -> bool:
    try:
        from sentinel_omega.infrastructure.messaging.agent_bridge import agent_health
        h = agent_health()
        # ok si ollama responde o al menos DB existe
        return bool(h.get('db_exists') or h.get('ollama_ok'))
    except Exception:
        return True  # no bloquear por agente si no esta


def notify(subject: str, html: str):
    try:
        from sentinel_omega.infrastructure.messaging.alert_service import AlertService, AlertTemplates, Severity, FormattedMessage
        svc = AlertService()
        msg = FormattedMessage(html=html, markdown=html, plain=html, subject=subject, severity=Severity.AMARILLO, alert_type='WATCHDOG')
        svc.dispatch(msg, channels=['telegram','log'])
        logger.info(f'notify {subject}')
    except Exception as e:
        logger.warning(f'notify fail: {e}')
        logger.info(html)


def asegurar_unidades() -> None:
    """Cada ciclo sano: unidad de usuario inactiva => restart + aviso en la caída.

    El aviso por Telegram sale SOLO la primera vez que se detecta la caída
    (transición activa->inactiva respecto al ciclo anterior): si la unidad
    sigue caída o el restart falla, los ciclos siguientes solo lo dejan en
    el log, no spamean el chat.
    """
    for svc in RESTORE_UNITS:
        activa = service_active(svc)
        if not activa:
            logger.warning(f'{svc} inactiva => re-levantando')
            try_restart([svc])
            levantada = service_active(svc)
            logger.info(f'{svc} tras restart: {"activa" if levantada else "SIGUE INACTIVA"}')
            if _previo.get(svc) and not activa:
                notify(f'[WATCHDOG] {svc} re-levantada',
                       f'`{svc}` amaneció inactiva y el watchdog la reinició '
                       f'({"OK" if levantada else "el restart no la levantó"}). '
                       f'{datetime.now(timezone.utc).isoformat()}')
        _previo[svc] = activa


def asegurar_streamlit() -> None:
    """Streamlit (unit de SISTEMA, root): detectar caída y avisar; no puede reiniciar.

    `sudo -n systemctl restart` se intenta igual — si algún día el operador
    agrega sudoers passwordless para esta unidad, el watchdog empezará a
    levantarlo solo sin cambiar una línea.
    """
    if not STREAMLIT_CHECK:
        return
    arriba = _puerto_ok(STREAMLIT_HOST, STREAMLIT_PORT)
    if not arriba:
        logger.warning(f'Streamlit {STREAMLIT_HOST}:{STREAMLIT_PORT} no responde => sudo -n restart')
        r = _sudo_systemctl('restart', STREAMLIT_UNIT)
        if r.returncode == 0:
            logger.info(f'{STREAMLIT_UNIT} reiniciada con sudo')
        else:
            logger.error(f'no se pudo reiniciar {STREAMLIT_UNIT} '
                         f'(sudo -n rc={r.returncode}): {(r.stderr or "").strip()[:120]}')
        if _previo.get('streamlit'):
            notify('[WATCHDOG] Streamlit caído (8510)',
                   f'El dashboard Streamlit no responde en {STREAMLIT_HOST}:{STREAMLIT_PORT} '
                   f'y el watchdog no puede reiniciarlo sin sudo. Levantarlo a mano:\n'
                   f'`sudo systemctl restart {STREAMLIT_UNIT}`\n'
                   f'{datetime.now(timezone.utc).isoformat()}')
    _previo['streamlit'] = arriba


def main():
    logger.info(f'Watchdog start interval={CHECK_INTERVAL_S}s threshold={FAIL_THRESHOLD}')
    logger.info(f'Asegurar cada ciclo: {", ".join(RESTORE_UNITS)}'
                + (f' + streamlit:{STREAMLIT_PORT}' if STREAMLIT_CHECK else ''))
    fails = 0
    was_down = False
    while True:
        net = has_network()
        ag = agent_ok()
        if net and ag:
            if was_down:
                notify('[SENTINEL] Red restaurada', f'Red OK tras {fails} fallos. {datetime.now(timezone.utc).isoformat()}')
            # asegurar servicios arriba: cada ciclo sano, no solo tras caída
            asegurar_unidades()
            asegurar_streamlit()
            fails = 0
            was_down = False
            logger.info('OK net+agent')
        else:
            fails += 1
            logger.warning(f'FAIL net={net} agent={ag} fails={fails}/{FAIL_THRESHOLD}')
            if fails >= FAIL_THRESHOLD:
                was_down = True
                # si no hay red, no intentar restart inmediato (esperar red), pero si hay red y agente mal, restart
                if net and not ag:
                    try_restart(['sentinel-omega'])  # scheduler disabled: duplicate launcher fought omega
                    notify('[SENTINEL] Watchdog reinicio agente', f'Agente no OK, reiniciado. fails={fails}')
                elif not net:
                    logger.warning('Sin red, esperando restauracion...')
                    # no restart hasta que vuelva red, pero avisar una vez
                    if fails == FAIL_THRESHOLD:
                        logger.warning('Red caida, watchdog en espera')
                # si la red sigue caida, no resetear a 0 (evitar esperar 3 ciclos mas); dejar en threshold-1 para re-evaluar rapido
                fails = 0 if net else FAIL_THRESHOLD - 1
        time.sleep(CHECK_INTERVAL_S)

if __name__ == '__main__':
    main()
