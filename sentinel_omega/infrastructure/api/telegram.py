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

NUEVA ARQUITECTURA: Sentinel escribe a cola JSON compartida.
Consensus Bot (telegram_bot.py) lee la cola y envía a Telegram.
Un solo bot token, un solo chat_id, mensajería centralizada.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

# Import alert queue from consensus-expert-agent
import sys
from pathlib import Path

# Try multiple possible locations for consensus-expert-agent
CONSENSUS_PATHS = [
    Path("/home/deamon/consensus-expert-agent"),  # Standard location
    Path(os.environ.get("CONSENSUS_EXPERT_AGENT_ROOT", "")) if os.environ.get("CONSENSUS_EXPERT_AGENT_ROOT") else None,
    Path(os.environ.get("SENTINEL_OMEGA_ROOT", "/home/deamon/workspaces/sentinel_omega")).parent / "consensus-expert-agent",
]

ALERT_QUEUE_AVAILABLE = False
for p in CONSENSUS_PATHS:
    if p and p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
        try:
            from alert_queue import (
                alert_queue, Alert, AlertPriority,
                queue_alert, queue_critical, queue_warning, queue_info,
                queue_heartbeat, queue_system
            )
            ALERT_QUEUE_AVAILABLE = True
            break
        except ImportError:
            continue
        finally:
            if str(p) in sys.path:
                sys.path.remove(str(p))

if not ALERT_QUEUE_AVAILABLE:
    logger = logging.getLogger(__name__)
    logger.warning("Alert queue not available, falling back to direct send")

from sentinel_omega.infrastructure.api._http import get_session

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"

# ─── El digesto que Telegram rechazaba entero ────────────────────────────────
#
# Medido el 2026-10-08 en el log del Concilio, que es quien despacha la cola:
#
#     ERROR Failed to send alert to …: Can't parse entities:
#           unsupported start tag "50)" at byte offset 1499
#     ERROR Cola: aviso «Direct Alert» descartado tras 5 intentos
#
# Quince digestos seguidos (13:49 → 18:25) muertos por un `(<50)` dentro del
# mensaje: el entrenador escribe «NO se reentrena: 38 muestras reales (<50) y
# sin prior» en `models_meta.json` y el digesto lo interpolaba en HTML sin
# escapar, así que el parser de Telegram leía `<50)` como una etiqueta de
# apertura y tiraba el mensaje COMPLETO con 400. No es que llegara mal
# formateado: no llegaba.
#
# El arreglo va en los dos sitios a propósito. En el constructor del texto
# (`consenso_vigilante`), porque ahí está el defecto; y aquí, en la única
# puerta de salida del repo hacia Telegram, porque hay quince constructores
# más y el siguiente texto libre que alguien interpole no puede volver a
# costar un día de avisos. Cada etiqueta permitida pasa intacta; cualquier
# otro `<` se escapa.
#
# Las etiquetas que Telegram admite (Bot API, modo HTML). `br` NO está entre
# ellas --- `cimatica_consistente` la usaba y ese aviso habría muerto igual ---
# así que se traduce al salto de línea que significa.
_TAGS_TELEGRAM = (
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "span", "tg-spoiler", "tg-emoji", "blockquote",
)
_TAGS_TELEGRAM = (
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "span", "tg-spoiler", "tg-emoji", "blockquote",
)
_TAG_PERMITIDA = re.compile(
    # El grupo (1) es el NOMBRE: lo usa `_balancear_tags` para emparejar.
    # Medido el 2026-10-17: el recorte a 3990 puede partir un <i> de su
    # </i>, y Telegram rechaza el mensaje ENTERO por una etiqueta abierta
    # («can't find end tag») — 36 avisos reenviados SIN FORMATO (con los
    # <b></b> crudos) en una semana. El saneo ahora GARANTIZA lo parseable.
    r"</?(?:" + "|".join(_TAGS_TELEGRAM) + r")(?:\s[^<>]*)?>", re.IGNORECASE
)
_TAG_NOMBRE = re.compile(r"</?(b|strong|i|em|u|ins|s|strike|del|a|code|pre|span|tg-spoiler|tg-emoji|blockquote)(?:\s[^<>]*)?>", re.IGNORECASE)
_SALTO_HTML = re.compile(r"<br\s*/?>", re.IGNORECASE)
# `&` suelta también rompe el parser; una entidad válida no.
_ENTIDAD = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#\d{1,7}|#[xX][0-9a-fA-F]{1,6});")


def sanear_html_telegram(texto: str) -> str:
    """Deja el texto parseable por Telegram sin perder su formato.

    Recorre una sola vez: las etiquetas permitidas se copian tal cual, `<br>`
    pasa a salto de línea, y cualquier otro `<` o `&` se escapa. Lo que entra
    ya sano sale idéntico.
    """
    if not texto:
        return texto
    texto = _SALTO_HTML.sub("\n", texto)
    salida = []
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if c == "<":
            m = _TAG_PERMITIDA.match(texto, i)
            if m:
                salida.append(m.group(0))
                i = m.end()
                continue
            salida.append("&lt;")
        elif c == "&":
            m = _ENTIDAD.match(texto, i)
            if m:
                salida.append(m.group(0))
                i = m.end()
                continue
            salida.append("&amp;")
        else:
            salida.append(c)
        i += 1
    return _balancear_tags("".join(salida))


def _balancear_tags(texto: str) -> str:
    """Cierra lo abierto, tira lo huérfano: lo que sale, Telegram lo parsea.

    El recorte de 3990 caracteres puede caer entre un ``<i>`` y su ``</i>``
    (digestos largos con 93 avisos agrupados): el mensaje sale con una
    etiqueta abierta y Telegram lo rechaza ENTERO («can't find end tag
    corresponding to start tag "i"», 36 veces medido entre el 10 y el 17
    de octubre). Aquí se cierra lo que quedó abierto, en orden y al final;
    los ``</x>`` sin apertura se tiran; y un cierre que salta anidación
    cierra primero los intermedios (Telegram exige anidado correcto).
    """
    pila: List[str] = []
    salida: List[str] = []
    ultimo = 0
    for m in _TAG_NOMBRE.finditer(texto):
        salida.append(texto[ultimo:m.start()])
        token = m.group(0)
        nombre = m.group(1).lower()
        if token.startswith("</"):
            if nombre in pila:
                while pila and pila[-1] != nombre:
                    salida.append(f"</{pila.pop()}>")
                pila.pop()
                salida.append(token)
            # </x> huérfano: fuera — mejor perder un cierre suelto
            # que perder el mensaje entero
        else:
            pila.append(nombre)
            salida.append(token)
        ultimo = m.end()
    salida.append(texto[ultimo:])
    while pila:
        salida.append(f"</{pila.pop()}>")
    return "".join(salida)


def sin_token(texto: object) -> str:
    """El texto con cualquier token de bot enmascarado.

    Encontrado el 2026-09-27 auditando el repo: el token viejo estaba en el log
    rotado `data/sentinel_omega.log.1` **195 veces**, y de ahí pasó a cuatro
    commits de git en un repo PÚBLICO. No lo puso nadie a mano: la URL de la API
    lleva el token dentro (`/bot<token>/sendMessage`), así que cuando `requests`
    falla su excepción TRAE la URL, y estos tres `logger.error(f"...: {e}")` la
    escribían entera.

    Rotar el token no arregla esto: el siguiente fallo de red vuelve a filtrar
    el nuevo. Se enmascara por patrón --- `<dígitos>:<35 caracteres>` --- y no
    comparando contra la variable de entorno, para que también cubra un token
    de otro bot que aparezca en el mismo mensaje.
    """
    import re

    # Dos detalles que hacen la diferencia entre enmascarar y fingir que se
    # enmascara, los dos aprendidos a golpes el 2026-09-27:
    #
    #   * sin `\b` delante: en `.../bot8412345678:AAH…` la `t` y el dígito son
    #     los dos caracteres de palabra, así que NO hay frontera y el patrón con
    #     `\b` no casaba --- por eso una primera pasada dejó el log intacto
    #   * `{30,}` en vez de `{35}`: el token suele traer 35 caracteres tras los
    #     dos puntos, pero no está garantizado, y un patrón clavado en 35 falla
    #     EN SILENCIO con uno de 36. Enmascarar de más es inofensivo; de menos,
    #     es una fuga
    texto = re.sub(
        r"(?<![0-9])[0-9]{8,10}:[A-Za-z0-9_-]{30,}",
        "<TOKEN>", str(texto),
    )
    # Segunda red: el tramo `/bot<lo-que-sea>:<lo-que-sea>/` de la URL de la
    # API se redacta aunque el token no tenga la forma canónica (uno truncado,
    # uno de pruebas), para que la URL de la petición nunca salga con token.
    return re.sub(r"/bot[^/\s]*:[^/\s]*/", "/bot<TOKEN>/", texto)


def _registrar_si_no_ok(resp: object, operacion: str) -> None:
    """Registra (logger.error) una respuesta de Telegram que no fue OK.

    Antes un 401 (token revocado) o un 200 con `{"ok": false}` pasaban en
    silencio o sin la `description` de Telegram. Aquí se registra el código
    HTTP, el `error_code` y la `description` --- pasados por `sin_token` ---
    y NUNCA la URL ni el token. No cambia qué devuelve el llamador.
    """
    status = getattr(resp, "status_code", None)
    if not isinstance(status, int):
        return  # doble de prueba sin status real: nada que decir
    ok = None
    error_code = None
    descripcion = None
    try:
        cuerpo = resp.json()
        if isinstance(cuerpo, dict):
            ok = cuerpo.get("ok")
            error_code = cuerpo.get("error_code")
            descripcion = cuerpo.get("description")
    except Exception:
        pass
    if status != 200 or ok is False:
        logger.error(
            "Telegram %s no OK: status=%s ok=%s error_code=%s description=%s",
            operacion, status, ok, error_code,
            sin_token(descripcion) if descripcion is not None else "-",
        )


TIMEOUT = 10

# Umbrales estilo Centinela V2 (fantasma 0–10 o 0–1 se normaliza)
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


def send_alert(message: str, parse_mode: str = "HTML", reply_markup: Optional[dict] = None) -> bool:
    """Envío directo (sin gate). Preferir send_alert_gated en ciclos.
    
    NUEVO: Si alert queue está disponible, escribe a cola en lugar de enviar directo.
    """
    # Recortar ANTES de sanear, y sanear en los DOS caminos.
    #
    # El orden importa: un recorte después del saneo puede partir una etiqueta
    # o una entidad por la mitad (`<b`, `&l`) y eso rompe el parser igual que
    # el `(<50)` --- mensaje entero rechazado. Saneando al final, lo que quede
    # cortado se escapa y el aviso llega, feo pero entero.
    #
    # El recorte cubría solo la rama legada, y por la cola va TODO desde que
    # existe: un mensaje de más de 4.096 lo rechaza Telegram («message is too
    # long»), y el Concilio no recorta --- cinco reintentos y al archivo de
    # descartados, el mismo final que los quince digestos de hoy.
    if len(message) > 4000:
        message = message[:3990] + "…"
    if (parse_mode or "").upper() == "HTML":
        message = sanear_html_telegram(message)
    if ALERT_QUEUE_AVAILABLE:
        queue_alert("Direct Alert", message, AlertPriority.MEDIUM, parse_mode)
        return True

    # Fallback: envío directo legacy
    creds = _get_credentials()
    if not creds:
        return False
    token, chat_id = creds
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = get_session().post(url, json=payload, timeout=TIMEOUT)
        _registrar_si_no_ok(resp, "sendMessage")
        resp.raise_for_status()
        logger.info("Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", sin_token(e))
        return False


def send_alert_gated(
    message: str,
    alert_type: str,
    parse_mode: str = "HTML",
    cooldown: int = COOLDOWN_S,
    reply_markup: Optional[dict] = None,
) -> bool:
    """Envía solo si el gate anti-spam lo permite."""
    if not _GATE.allow(alert_type, cooldown=cooldown):
        logger.debug(f"Telegram gated skip: {alert_type}")
        return False
    return send_alert(message, parse_mode=parse_mode, reply_markup=reply_markup)




def send_photo(photo_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
    if os.environ.get("SENTINEL_DRY_RUN", "").lower() in ("1", "true", "yes"):
        logger.info("[DRY_RUN] Telegram photo skipped: %s", photo_path)
        return True
    """Envia una foto con caption a Telegram. photo_path debe ser archivo local."""
    creds = _get_credentials()
    if not creds:
        return False
    token, chat_id = creds
    url = f"{TELEGRAM_API}/bot{token}/sendPhoto"
    if len(caption) > 1000:
        caption = caption[:998] + "…"
    if (parse_mode or "").upper() == "HTML":
        caption = sanear_html_telegram(caption)
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": parse_mode}
            resp = get_session().post(url, data=data, files=files, timeout=TIMEOUT + 10)
            _registrar_si_no_ok(resp, "sendPhoto")
            resp.raise_for_status()
            logger.info(f"Telegram photo sent: {photo_path}")
            return True
    except Exception as e:
        logger.error("Telegram photo failed: %s", sin_token(e))
        return False


def send_document(doc_path: str, caption: str = "") -> bool:
    creds = _get_credentials()
    if not creds:
        return False
    token, chat_id = creds
    url = f"{TELEGRAM_API}/bot{token}/sendDocument"
    try:
        with open(doc_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption[:1000] if caption else ""}
            resp = get_session().post(url, data=data, files=files, timeout=TIMEOUT + 10)
            _registrar_si_no_ok(resp, "sendDocument")
            resp.raise_for_status()
            logger.info(f"Telegram document sent: {doc_path}")
            return True
    except Exception as e:
        logger.error("Telegram document failed: %s", sin_token(e))
        return False

def notify_online() -> bool:
    return send_alert(
        "🔵 <b>SISTEMA ONLINE</b>\nSentinel Omega vigilando telemetría y precursores."
    )


def notify_system_dead(minutes: float) -> bool:
    if _GATE.system_dead_alerted:
        return False
    try:
        from sentinel_omega.infrastructure.messaging.alert_service import AlertService, AlertTemplates
        out = AlertService().dispatch(AlertTemplates.sistema_dead(minutes), channels=["telegram", "log"])
        ok = bool(out.get("telegram"))
    except Exception:
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
    """Legacy 4h ping — now ingested as HEARTBEAT (hourly digest covers this)."""
    try:
        from sentinel_omega.infrastructure.messaging.alert_service import AlertService, AlertTemplates
        out = AlertService().dispatch(AlertTemplates.heartbeat(status_line), channels=["telegram", "log"])
        if out.get("telegram"):
            _GATE.mark_heartbeat()
            return True
        return False
    except Exception:
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


# Rango en el que un número puede ser la resonancia Schumann. La fundamental es
# 7,83 Hz y los armónicos suben a 14,3 · 20,8 · 27,3 · 33,8; nada por debajo de
# 1 Hz ni por encima de 60 es esa señal.
#
# Es la SEGUNDA capa. La primera está en `orchestrator.py`, que solo deja pasar
# Hz de verdad --- antes mandaba `schumann_wpc`, una fracción 0–1, y el parte
# publicaba «0,21 Hz» con toda naturalidad. Medido el 2026-09-27: el formateador
# imprimía esa fracción sin pestañear, así que la defensa era de una sola capa.
# Un número en la unidad equivocada es peor que no dar el dato.
HZ_SCHUMANN_MIN = 1.0
HZ_SCHUMANN_MAX = 60.0


def hz_schumann_valido(v) -> Optional[float]:
    """El valor si puede ser Hz de Schumann; None si no, con aviso.

    Un 0,0 MEDIDO no pasa: cero hercios no es una lectura de la cavidad, es
    ausencia de señal. Eso lo distingue del `or` falsy que se arregló antes ---
    ahí el problema era descartar un cero legítimo de Bz o de Kp.
    """
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    if not (HZ_SCHUMANN_MIN <= f <= HZ_SCHUMANN_MAX):
        logger.warning(
            "Schumann fuera de rango (%.4f): no se publica. Por debajo de %.0f Hz "
            "suele ser la fracción de actividad (schumann_wpc), no hercios",
            f, HZ_SCHUMANN_MIN,
        )
        return None
    return f


def format_centinela_threat(
    risk: float,
    bz: float,
    wind: float,
    schumann: Optional[float] = None,
    schumann_act: Optional[float] = None,
) -> Optional[Tuple[str, str]]:
    """
    Prioridades Centinela V2. Devuelve (alert_type, html) o None.
    risk: fantasma 0–1 (si viene 0–10 se escala).
    """
    r = float(risk)
    if r > 1.5:  # escala antigua 0–10
        r = r / 10.0
    bz = float(bz)
    wind = float(wind)
    schumann = hz_schumann_valido(schumann)
    # La actividad WPC es lo único medido en vivo desde el retiro del Hz
    # (2026-10-09). El parte CRÍTICO la reporta con la frecuencia declarada
    # SIN MEDIR --- nunca como si estuviera medida.
    act_linea = ""
    if schumann_act is not None:
        try:
            act_linea = (f"\n🌐 Schumann: actividad {float(schumann_act):.1f} %"
                         " (frecuencia sin medir)")
        except (TypeError, ValueError):
            act_linea = ""

    if r >= TH_RISK_CRIT:
        return (
            "CRITICO",
            f"🔴 <b>ALERTA CRÍTICA</b>\n\n"
            f"⚠️ Fantasma: <b>{r:.2f}</b>\n"
            f"🧲 Bz: {bz:.1f} nT\n"
            f"💨 Viento: {wind:.0f} km/s"
            # `is not None`, no `if schumann`: con el falsy, un 0 medido
            # desaparecía del parte igual que un None. Aquí sólo llegan Hz
            # (ver orchestrator.py); antes podía llegar una fracción de WPC.
            + (f"\n🌐 Schumann: {schumann:.2f} Hz"
               if schumann is not None else "")
            + act_linea,
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
    schumann_act: Optional[float] = None,
    consensus_signal: Optional[str] = None,
    consensus_conf: float = 0.0,
    agents_n: int = 0,
    metadata: Optional[Dict] = None,
    muro_msg: Optional[str] = None,
    elevated_risk_msg: Optional[str] = None,
) -> int:
    """
    Un solo punto de despacho por ciclo: Centinela + consenso + dual-ask + muro.
    Retorna número de mensajes enviados.
    """
    sent = 0
    meta = metadata or {}
    try:
        from sentinel_omega.infrastructure.messaging.alert_service import (
            AlertService, FormattedMessage, Severity,
        )
        svc = AlertService()
    except Exception:
        svc = None

    def _ingest(html: str, atype: str, sev: "Severity", extra=None) -> None:
        nonlocal sent
        from sentinel_omega.infrastructure.messaging.alert_service import FormattedMessage as _FM2
        if svc is None:
            # last-resort: still do not fire raw unless dry-run is off AND no vigilante
            from sentinel_omega.infrastructure.messaging.consenso_vigilante import get_vigilante
            from sentinel_omega.infrastructure.messaging.alert_service import Severity as _S
            get_vigilante().ingest(_FM2(html=html, markdown=html, plain=html, subject=atype, severity=_S.AZUL, alert_type=atype), extra=extra)
            sent += 1
            return
        msg = _FM2(
            html=html, markdown=html, plain=html,
            subject=f"[SENTINEL] {atype}", severity=sev, alert_type=atype,
        )
        svc.dispatch(msg, channels=["telegram", "log"], extra=extra)
        sent += 1

    if fantasma is not None and bz is not None and wind is not None:
        threat = format_centinela_threat(fantasma, bz, wind, schumann, schumann_act)
        if threat:
            atype, html = threat
            sev = Severity.ROJO if atype in ("CRITICO", "GRIETA") else Severity.AMARILLO
            # Routine centinela watches go to the hourly digest (not a page).
            _ingest(html, atype, sev)

    if consensus_signal and consensus_signal.lower() in ("alert", "watch"):
        msg = format_consensus_alert(
            "geodynamic",
            consensus_signal,
            consensus_conf,
            agents_n,
            dual_ask=meta.get("dual_ask"),
            omega_voto=meta.get("omega_voto"),
        )
        _ingest(msg, f"CONSENSUS_{consensus_signal.upper()}", Severity.AMARILLO)

    omega_msg = format_omega_dual_ask(meta)
    if omega_msg and meta.get("dual_ask"):
        _ingest(omega_msg, "OMEGA_DUAL", Severity.AZUL)

    if elevated_risk_msg:
        _ingest(elevated_risk_msg, "RISK_ELEVATED", Severity.AMARILLO)

    if muro_msg:
        extra = {"muro_tipo": "MURO_BREACH"}
        _ingest(muro_msg, "MURO_BREACH", Severity.AMARILLO, extra=extra)

    return sent
