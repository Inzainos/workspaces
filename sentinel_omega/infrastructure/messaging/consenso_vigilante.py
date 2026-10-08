"""
Consenso vigilante (Padre) — buffers routine alerts, hourly digest always,
immediate Telegram only for unprecedented events.

Policy (Elán, 2026-09-03):
  1. ALWAYS send one hourly REPORT (digest). Never skip the hour because
     things look calm. Content is a concentrado of precursors, fantasma,
     muro and telemetry — not a pile of "precursores revisar" pings.
  2. Immediate Telegram ONLY if is_unprecedented(event): no prior record
     in the system (sin precedentes). Qualifies:
       - cimática patrón NUEVO (frecuencia == 1)
       - firma never seen (TBL_FIRMAS estado='nueva' / recurrencia <= 1)
       - novel muro breach type (first time that breach kind is recorded)
       - SYSTEM_DEAD (loop died — no healthy cycle recently)
     Recurring firma matches and routine precursor watches do NOT page.
  3. Mini App button (TELEGRAM_WEBAPP_URL, HTTPS public URL) on digest
     and immediate pages. This module does not create a tunnel.

Dry-run: SENTINEL_DRY_RUN=1 / dry_run=True never calls the Telegram API.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from sentinel_omega.infrastructure.messaging.alert_service import (
    AlertTemplates,
    FormattedMessage,
)

logger = logging.getLogger(__name__)

DEFAULT_DIGEST_MINUTES = 60
IMMEDIATE_COOLDOWN_S = int(os.environ.get("TELEGRAM_COOLDOWN_S", "1800"))

# Marca del último digesto, COMPARTIDA ENTRE PROCESOS.
#
# `TG_DIGEST_MINUTES` era un mando muerto en la ruta que de verdad despacha
# (2026-10-07). La cadena medida: `sentinel-omega-rutinas.timer` corre cada 15
# min, el script llama `deploy/enviar_correos.py`, y ese es un `Type=oneshot` ---
# **cada corrida es un proceso nuevo**. `last_digest_ts` nacía en 0.0 en el
# `__init__` y no se guardaba en ninguna parte, así que la compuerta de
# `maybe_flush` (`now - last_digest_ts < due_s`) no podía cerrarse NUNCA.
# Resultado en el teléfono del operador: **54 digestos en un día, 4 por hora
# exactas**, con `TG_DIGEST_MINUTES=60` declarado en tres documentos.
#
# Es la tercera vez que aparece el mismo bicho: el `days` de `fetch_kp_index` y
# el `confidence_threshold` de los ocho ONNX también estaban declarados y leídos
# por nadie. Aquí el mando SÍ se leía --- `digest_minutes()` lo lee --- pero el
# estado contra el que se comparaba moría con el proceso, que para el caso es lo
# mismo.
#
# Se persiste en un archivo junto a la base y NO en la base: esta clase abre la
# DB en `mode=ro` en todas sus rutas, y la DB de producción tiene un escritor
# vivo 24/7. Un archivo de dos campos no necesita migración ni compite por el
# candado. `data/` está en `.gitignore`, así que se crea al vuelo (regla 3).
DIGEST_STATE_FILE = "estado_digesto.json"

# Alert types that are always unprecedented (loop / health).
_ALWAYS_IMMEDIATE_TYPES = frozenset(
    {"SYSTEM_DEAD", "DEAD", "FALLO", "FALLO_CICLO"}
)

# Routine types that never page, even if severity is rojo/amarillo.
# They belong in the hourly concentrado.
_ALWAYS_BUFFER_PREFIXES = (
    "PRECURSOR_",
    "PREC_",
    "ADVERTENCIA",
    "CONSENSUS_",
    "CONSENSO_",
    "HEARTBEAT",
    "RESUMEN",
    "ONLINE",
    "RISK_ELEVATED",
    "OMEGA_DUAL",
    "CIMATICA",  # consistente / increment — NUEVO is flagged via extra
)


def digest_minutes() -> int:
    raw = os.environ.get("TG_DIGEST_MINUTES", str(DEFAULT_DIGEST_MINUTES))
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = DEFAULT_DIGEST_MINUTES
    return max(1, n)


def webapp_url() -> str:
    return (os.environ.get("TELEGRAM_WEBAPP_URL") or "").strip()


def webapp_reply_markup() -> Optional[Dict[str, Any]]:
    """Inline keyboard with a Telegram Mini App button, or None.

    Telegram Mini Apps require a public HTTPS URL. Localhost / missing env
    means no button — we do not fake a tunnel.
    """
    url = webapp_url()
    if not url:
        return None
    if not url.lower().startswith("https://"):
        logger.warning(
            "TELEGRAM_WEBAPP_URL is not HTTPS (%s) — Mini App button omitted. "
            "Telegram requires a public HTTPS URL; set the env after exposing "
            "the dashboard API yourself (reverse proxy / Cloudflare / etc.).",
            url.split("://", 1)[0] if "://" in url else "no-scheme",
        )
        return None
    return {
        "inline_keyboard": [
            [{"text": "📊 Abrir panel Sentinel", "web_app": {"url": url}}],
            [{"text": "🤖 Modelos ONNX", "web_app": {"url": url + "/models"}}]
        ]
    }


# ─── El ✅ del digesto era «el archivo existe» ────────────────────────────────
#
# Medido el 2026-10-08, leyendo lo que de verdad llega al teléfono: el digesto
# horario decía «🤖 Modelos ONNX activos: ✅ ALFA1 (791KB) ✅ BETA1 …» con la
# única comprobación de `os.path.exists`. Un `.onnx` en disco no es un modelo
# que sirva, y el operador leía seis palomas verdes como «seis modelos
# funcionando».
#
# Lo que había en disco ese día:
#
#     seis .onnx del 2 al 4 de octubre      la compuerta se escribió el día 7
#     models_meta.json SIN clave «habilidad» ni «compuerta»
#
# O sea: ninguno de los seis ha pasado por `medir_habilidad`, y el aviso los
# presentaba aprobados. Es el vicio de siempre --- un número (aquí, un icono)
# que no mide lo que su nombre promete --- y en la superficie que más se lee.
#
# Ahora el estado sale del METADATO que escribe el reentrenamiento
# (`models/models_meta.json`, con `habilidad.auc` / `ganancia_sobre_nulo` /
# `aprueba` por bot), y cuando el metadato no lo trae se DICE que no está
# medido en vez de pintar una paloma. La ruta ya no se arma con ocho ternarios
# y un prefijo absoluto: viene del mismo diccionario `NOMBRES_ONNX` que usa el
# entrenador.
NOMBRES_ONNX = {
    "alfa1": "alfa1_spaceweather_rf.onnx",
    "alfa2": "alfa2_satellite_cnn.onnx",
    "beta1": "beta1_schumann_fft.onnx",
    "beta2": "beta2_atmospheric_cnn.onnx",
    "delta": "delta_financial_lstm.onnx",
    "omega": "omega_espacial_rf.onnx",
    "loki": "loki_unificado_rf.onnx",
    "jupiter": "jupiter_attention_rf.onnx",
}

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def _habilidad_por_bot() -> tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    """Lee `models_meta.json`. Devuelve (por_bot, fecha_del_metadato)."""
    meta_path = MODELS_DIR / "models_meta.json"
    try:
        meta = json.loads(meta_path.read_text())
    except Exception:
        return {}, None
    bots = meta.get("bots")
    if not isinstance(bots, dict):
        return {}, None
    return bots, meta.get("retrained_at")


def get_model_status(db_path: str) -> str:
    """Estado de los ONNX para el digesto: habilidad MEDIDA, no existencia."""
    try:
        por_bot, medido_at = _habilidad_por_bot()
        lineas: List[str] = []
        # Dos razones DISTINTAS para no tener AUC, y confundirlas fue un defecto
        # de este mismo archivo (2026-10-08, dos horas después de escribirlo):
        # la nota decía «son anteriores a la compuerta» de alfa2 y jupiter
        # cuando acababan de PASAR por ella y no se pudieron medir por falta de
        # muestras (38 y 53). Un motivo medido no es un metadato viejo.
        sin_evidencia = 0      # la compuerta los miró y no alcanzó la muestra
        sin_metadato = 0       # nunca pasaron: el metadato no los menciona
        for bot, nombre in NOMBRES_ONNX.items():
            ruta = MODELS_DIR / nombre
            if not ruta.exists():
                lineas.append(f"❌ {bot.upper()} — sin modelo en disco")
                continue
            kb = ruta.stat().st_size // 1024
            entrada = por_bot.get(bot) or {}
            hab = entrada.get("habilidad")
            hab = hab if isinstance(hab, dict) else {}
            if hab.get("auc") is None:
                # ¿Hay un motivo medido, o simplemente nadie lo evaluó?
                motivo = str(hab.get("motivo") or entrada.get("source") or "")
                if motivo:
                    sin_evidencia += 1
                    lineas.append(
                        f"❔ {bot.upper()} ({kb} KB) — <b>sin habilidad "
                        f"medible</b>: {motivo[:120]}")
                else:
                    sin_metadato += 1
                    lineas.append(
                        f"❔ {bot.upper()} ({kb} KB) — <b>habilidad sin medir</b>")
                continue
            auc = float(hab["auc"])
            gan = hab.get("ganancia_sobre_nulo")
            gan_s = f" · ganancia {float(gan):+.3f}" if gan is not None else ""
            if hab.get("aprueba"):
                lineas.append(
                    f"✅ {bot.upper()} ({kb} KB) — AUC {auc:.3f}{gan_s}")
            else:
                motivo = str(hab.get("motivo") or "la compuerta lo negó")
                lineas.append(
                    f"⚠️ {bot.upper()} ({kb} KB) — AUC {auc:.3f}{gan_s} · "
                    f"se usa el anterior: {motivo[:120]}")

        fecha = f" del {medido_at[:10]}" if medido_at else ""
        partes = []
        if sin_metadato:
            partes.append(
                f"{sin_metadato} modelo(s) no aparecen en el metadato{fecha}: "
                f"son anteriores a la compuerta y su habilidad nunca se calculó")
        if sin_evidencia:
            partes.append(
                f"{sin_evidencia} pasaron por la compuerta{fecha} y no hubo "
                f"muestra suficiente para medirlos --- es falta de evidencia, "
                f"no una mala nota")
        nota = (
            "\n<i>" + ". ".join(partes) + ". Un .onnx que existe no es un "
            "modelo que acierte: trátalos como desconocidos.</i>"
        ) if partes else ""

        lag_info = ""
        conn = None
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            lags = conn.execute(
                "SELECT event_class, lag_promedio_h FROM tbl_lag_anticipacion "
                "WHERE event_class LIKE 'SISMO_M%' ORDER BY event_class"
            ).fetchall()
            if lags:
                lag_lines = [
                    f"   {r['event_class']}: ~{r['lag_promedio_h']:.0f}h"
                    for r in lags if r["lag_promedio_h"] is not None
                ]
                if lag_lines:
                    lag_info = "\n📉 <b>Lag de anticipación:</b>\n" + "\n".join(lag_lines)
        except Exception as exc:
            logger.warning("digesto: no se pudo leer el lag de anticipación: %s", exc)
        finally:
            if conn is not None:
                conn.close()

        return (
            "🤖 <b>Modelos ONNX (habilidad medida):</b>\n"
            + "\n".join(lineas) + nota + lag_info
        )
    except Exception as e:
        logger.warning("digesto: error armando el estado de modelos: %s", e)
        return f"🤖 Modelos: error leyendo estado ({e})"


def get_vara_juez(db_path: str) -> str:
    """La vara del Juez para el digesto: asertividad JUNTO a su ganancia.

    `CLAUDE.md` lo pide como regla del tablero --- «la asertividad nunca se
    muestra sola» --- y el digesto horario era la última superficie donde no
    aparecía NINGUNA de las dos. El operador leía Fantasma, muro, telemetría y
    seis palomas verdes, y nada le decía si las alarmas del sistema superan a
    alarmar a ciegas.

    Medido el 2026-10-08 sobre `viva_real` (306 filas): asertividad 0,353 con
    **0,971 de un bot mudo** y ganancia 1,172×. Que la asertividad esté POR
    DEBAJO del silencio es el dato: el sistema alarmó en 203 de 306 ventanas.
    """
    conn = None
    try:
        from sentinel_omega.core.precursor.baseline import evaluar_veredictos

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        # `COALESCE(en_vivo,1)=1`: la vista `viva_real` NO filtra `en_vivo` y
        # arrastra los veredictos duplicados del 27-sep (trampa 3 del tablero).
        filas = conn.execute(
            "SELECT verdad, resultado FROM viva_real "
            "WHERE resultado != 'PENDIENTE' AND COALESCE(en_vivo, 1) = 1"
        ).fetchall()
        if not filas:
            return (
                "⚖️ <b>Vara del Juez:</b> <code>sin veredictos cerrados</code> — "
                "aún no hay con qué medir si las alarmas aportan."
            )
        m = evaluar_veredictos([(v or "", r or "") for v, r in filas])
        if m is None or m.ganancia is None:
            return (
                "⚖️ <b>Vara del Juez:</b> "
                f"{len(filas)} ventanas, <code>ganancia indefinida</code> — "
                "sin alarmas o sin eventos en el tramo."
            )
        icono = "✅" if m.ganancia > 1.5 else "⚠️" if m.ganancia > 1.0 else "🔴"
        return (
            f"⚖️ <b>Vara del Juez:</b> ganancia <code>{m.ganancia:.2f}×</code> {icono} "
            f"· asertividad <code>{m.asertividad * 100:.1f}%</code> contra "
            f"<code>{m.asertividad_muda * 100:.1f}%</code> de un bot que nunca "
            f"alarma ({m.alarmas} alarmas en {m.ventanas} ventanas, "
            f"{m.con_evento} con evento).\n"
            f"<i>{m.veredicto}. La ganancia es la que manda: 1× significa que "
            f"alertar a ciegas habría rendido lo mismo.</i>"
        )
    except Exception as exc:
        logger.warning("digesto: no se pudo medir la vara del Juez: %s", exc)
        return (
            "⚖️ <b>Vara del Juez:</b> <code>error de lectura</code> — "
            "no se midió la ganancia en esta hora."
        )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_utc_str() -> str:
    return _now_utc().strftime("%Y-%m-%d %H:%M UTC")


def _mx_str() -> str:
    # America/Mexico_City is UTC-6 (no DST as of 2026).
    return datetime.fromtimestamp(time.time() - 6 * 3600, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M MX"
    )


@dataclass
class BufferedAlert:
    ts: float
    msg: FormattedMessage
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchRecord:
    """What would have been (or was) sent. Tests inspect this; no network."""

    kind: str  # "immediate" | "digest"
    alert_type: str
    html: str
    subject: str
    ts: float
    dry_run: bool
    reply_markup: Optional[Dict[str, Any]] = None
    sent: bool = False


class ConsensoVigilante:
    """Padre watcher: buffer routine noise, hourly digest, page only the new."""

    def __init__(
        self,
        dry_run: Optional[bool] = None,
        digest_minutes_override: Optional[int] = None,
        now_fn: Callable[[], float] = time.time,
        db_path: Optional[str] = None,
        snapshot_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        if dry_run is None:
            dry_run = os.environ.get("SENTINEL_DRY_RUN", "").lower() in (
                "1",
                "true",
                "yes",
            )
        self.dry_run = bool(dry_run)
        self._digest_minutes = (
            digest_minutes_override
            if digest_minutes_override is not None
            else digest_minutes()
        )
        self._now = now_fn
        self.db_path = db_path or os.environ.get(
            "SENTINEL_DB",
            "/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db",
        )
        self._snapshot_fn = snapshot_fn
        self.buffer: List[BufferedAlert] = []
        # Se LEE del disco, no nace en cero: ver `DIGEST_STATE_FILE`. Sin esto
        # cada proceso nuevo creía que nunca se había mandado un digesto.
        self.last_digest_ts: float = self._load_last_digest_ts()
        self.dispatched: List[DispatchRecord] = []
        self._immediate_last: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def ingest(
        self,
        msg: FormattedMessage,
        *,
        extra: Optional[Dict[str, Any]] = None,
        conn: Any = None,
    ) -> Dict[str, Any]:
        """Route one alert: immediate if unprecedented, else buffer.

        Never talks to Telegram when dry_run is set. Returns a dict the
        caller (AlertService / orchestrator) can log.
        """
        extra = dict(extra or {})
        unprecedented = self.is_unprecedented(msg, extra=extra, conn=conn)
        if unprecedented:
            rec = self._dispatch_immediate(msg, extra=extra)
            return {
                "action": "immediate",
                "alert_type": msg.alert_type,
                "dry_run": self.dry_run,
                "sent": rec.sent,
                "unprecedented": True,
            }
        self.buffer.append(BufferedAlert(ts=self._now(), msg=msg, extra=extra))
        logger.info(
            "CONSENSO buffer [%s/%s] %s (pendientes=%d)",
            msg.severity.value,
            msg.alert_type,
            msg.subject,
            len(self.buffer),
        )
        return {
            "action": "buffered",
            "alert_type": msg.alert_type,
            "dry_run": self.dry_run,
            "sent": False,
            "unprecedented": False,
            "pending": len(self.buffer),
        }

    # ------------------------------------------------------------------ #
    # Cadencia del digesto — estado que sobrevive al proceso
    # ------------------------------------------------------------------ #

    def _digest_state_path(self) -> Optional[Path]:
        """Dónde vive la marca, o None si esta instancia no debe tocarla.

        `TG_DIGEST_STATE` la mueve, y los tests la apuntan a un `tmp_path`.

        **En dry-run no hay archivo**, a propósito y por dos razones. Una: en
        dry-run no sale ningún digesto, así que no hay nada que marcar. Dos, y
        es la que importa: si una instancia dry-run leyera la marca de
        producción, el resultado de un test dependería de cuándo salió el
        último digesto de verdad --- y una prueba podría escribirla y dejar al
        operador una hora sin reporte. La cadencia en dry-run vuelve a ser la
        del proceso, que es lo que el `launcher.py` de siempre ya hacía bien.
        """
        override = (os.environ.get("TG_DIGEST_STATE") or "").strip()
        if override:
            return Path(override)
        if self.dry_run or not self.db_path:
            return None
        return Path(self.db_path).parent / DIGEST_STATE_FILE

    def _load_last_digest_ts(self) -> float:
        """La marca del último digesto enviado, o 0.0 si no hay ninguna.

        0.0 significa «manda ahora». Es el default correcto: ante la duda se
        envía, porque la política 1 del módulo es no saltarse la hora. Lo que
        NO se hace es callar el motivo --- un archivo ilegible se registra
        (regla 10), porque si no la cadencia volvería al bicho de 4/hora sin
        que nadie viera por qué.
        """
        ruta = self._digest_state_path()
        if ruta is None:
            return 0.0
        try:
            crudo = ruta.read_text(encoding="utf-8")
        except FileNotFoundError:
            return 0.0          # primera corrida: normal, no es un fallo
        except OSError as exc:
            logger.warning(
                "no se pudo leer la marca del digesto en %s (%s) --- esta "
                "corrida manda digesto", ruta, exc)
            return 0.0
        try:
            ts = float(json.loads(crudo)["last_digest_ts"])
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning(
                "marca del digesto ilegible en %s (%s) --- esta corrida manda "
                "digesto y la reescribe", ruta, exc)
            return 0.0
        # Un reloj que salta al futuro silenciaría el digesto durante horas sin
        # que nada lo delate. Se desconfía del valor, no del operador (regla 7).
        if ts > self._now() + 60.0:
            logger.warning(
                "la marca del digesto (%.0f) está en el futuro respecto al "
                "reloj (%.0f) --- se ignora y esta corrida manda digesto",
                ts, self._now())
            return 0.0
        return ts

    def _persist_last_digest_ts(self, ts: float) -> None:
        """Guarda la marca de forma atómica. Un fallo aquí NO tumba el envío:
        el digesto ya salió, y lo peor que pasa es volver a la cadencia en
        memoria --- pero queda dicho en el log."""
        ruta = self._digest_state_path()
        if ruta is None:
            return
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            tmp = ruta.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"last_digest_ts": float(ts)}), encoding="utf-8")
            os.replace(tmp, ruta)
        except OSError as exc:
            logger.warning(
                "no se pudo guardar la marca del digesto en %s (%s) --- la "
                "cadencia vuelve a depender de la memoria del proceso y "
                "`TG_DIGEST_MINUTES` deja de valer entre corridas", ruta, exc)

    def maybe_flush(self, snapshot: Optional[Dict[str, Any]] = None) -> Optional[DispatchRecord]:
        """Flush the hourly digest if the timer is due. Always sends when due,
        even if the buffer is empty (calm hour still gets a concentrado).

        La compuerta funciona **entre procesos** desde el 2026-10-07: la marca
        se lee del disco en el `__init__`, así que un `Type=oneshot` que corre
        cada 15 min respeta `TG_DIGEST_MINUTES=60`. Ver `DIGEST_STATE_FILE`.
        """
        due_s = self._digest_minutes * 60
        now = self._now()
        if self.last_digest_ts and (now - self.last_digest_ts) < due_s:
            faltan = (due_s - (now - self.last_digest_ts)) / 60.0
            logger.info(
                "CONSENSO digesto aún no toca: faltan %.0f min de los %d "
                "declarados en TG_DIGEST_MINUTES", faltan, self._digest_minutes)
            return None
        return self.flush_digest(force=True, snapshot=snapshot)

    def flush_digest(
        self,
        force: bool = False,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> DispatchRecord:
        """Build and send the hourly concentrado. `force` ignores the timer."""
        if not force:
            rec = self.maybe_flush(snapshot=snapshot)
            if rec is None:
                return DispatchRecord(
                    kind="digest",
                    alert_type="DIGESTO_HORARIO",
                    html="",
                    subject="[SENTINEL] Digest skipped (timer)",
                    ts=self._now(),
                    dry_run=self.dry_run,
                    sent=False,
                )
            return rec

        snap = dict(snapshot or {})
        if not snap and self._snapshot_fn:
            try:
                snap = dict(self._snapshot_fn() or {})
            except Exception as exc:
                logger.debug("snapshot_fn failed: %s", exc)
        if not snap:
            snap = self._load_snapshot()

        drained = list(self.buffer)
        self.buffer.clear()
        html, subject = self._build_digest(snap, drained)
        markup = webapp_reply_markup()
        rec = DispatchRecord(
            kind="digest",
            alert_type="DIGESTO_HORARIO",
            html=html,
            subject=subject,
            ts=self._now(),
            dry_run=self.dry_run,
            reply_markup=markup,
        )
        rec.sent = self._send(html, "DIGESTO_HORARIO", cooldown=0, reply_markup=markup)
        self.last_digest_ts = rec.ts
        # La marca en disco solo se mueve si el digesto SALIÓ de verdad. Si
        # Telegram falló, la siguiente corrida (15 min) reintenta en vez de
        # callarse una hora; y un `dry_run` no toca el estado de producción.
        if rec.sent and not self.dry_run:
            self._persist_last_digest_ts(rec.ts)
        self.dispatched.append(rec)
        logger.info(
            "CONSENSO digest horario (%s, buffered=%d, dry_run=%s)",
            "DRY" if self.dry_run else "sent" if rec.sent else "fail",
            len(drained),
            self.dry_run,
        )
        return rec

    def pending_count(self) -> int:
        return len(self.buffer)

    # ------------------------------------------------------------------ #
    # Unprecedented?
    # ------------------------------------------------------------------ #

    def is_unprecedented(
        self,
        msg: FormattedMessage,
        extra: Optional[Dict[str, Any]] = None,
        conn: Any = None,
    ) -> bool:
        """True only when there is no prior record of this event in the system.

        Explicit extra['unprecedented'] wins. Recurring firma / precursor /
        cimática-increment NEVER page, regardless of severity.
        """
        extra = extra or {}
        if extra.get("unprecedented") is True:
            return True
        if extra.get("unprecedented") is False:
            return False

        at = (msg.alert_type or "").upper()

        if at in _ALWAYS_IMMEDIATE_TYPES or "SYSTEM_DEAD" in at:
            return True

        # Cimática: NUEVO / frecuencia==1 pages; repeats go to digest.
        if extra.get("es_nuevo") is True or extra.get("frecuencia") == 1:
            return True
        if extra.get("frecuencia") is not None and int(extra["frecuencia"]) > 1:
            return False
        if at in ("CIMATICA_NUEVO", "CIMATICA_NUEVA") or at.endswith("_NUEVO"):
            return True
        if at == "CIMATICA" or at.startswith("CIMATICA"):
            if conn is not None:
                return self._cimatica_is_nuevo(conn, extra)
            return False

        # Firma: estado nueva / recurrencia <= 1 / never in TBL_FIRMAS.
        if extra.get("es_nueva") is True or extra.get("estado") == "nueva":
            recu = extra.get("recurrencia")
            if recu is None or int(recu) <= 1:
                return True
            return False
        if extra.get("recurrencia") is not None:
            return int(extra["recurrencia"]) <= 1
        if "FIRMA" in at:
            if conn is not None:
                return self._firma_is_nueva(conn, extra)
            # Without DB, only page if the type itself says NUEVA.
            return "NUEVA" in at or "NUEVO" in at

        # Muro: only a breach KIND never recorded before.
        if "MURO" in at:
            if extra.get("novel_muro") is True:
                return True
            if conn is not None:
                return self._muro_type_unseen(conn, extra)
            return False

        # Routine watches: precursors, consensus, advertencia, heartbeat…
        for prefix in _ALWAYS_BUFFER_PREFIXES:
            if at.startswith(prefix) or at == prefix.rstrip("_"):
                return False

        # Default: do not page. Hourly digest is the contract.
        return False

    def _cimatica_is_nuevo(self, conn: Any, extra: Dict[str, Any]) -> bool:
        patron_id = extra.get("patron_id")
        clave = extra.get("clave")
        try:
            if patron_id:
                row = conn.execute(
                    "SELECT frecuencia FROM tbl_cimatica_patrones WHERE patron_id = ?",
                    (patron_id,),
                ).fetchone()
                if row is None:
                    return True
                freq = int(row[0] if not isinstance(row, sqlite3.Row) else row["frecuencia"])
                return freq <= 1
            if clave:
                row = conn.execute(
                    "SELECT frecuencia FROM tbl_cimatica_patrones WHERE clave = ? "
                    "ORDER BY patron_id DESC LIMIT 1",
                    (clave,),
                ).fetchone()
                if row is None:
                    return True
                freq = int(row[0] if not isinstance(row, sqlite3.Row) else row["frecuencia"])
                return freq <= 1
        except Exception as exc:
            logger.debug("cimatica unprecedented check failed: %s", exc)
        return False

    def _firma_is_nueva(self, conn: Any, extra: Dict[str, Any]) -> bool:
        firma_id = extra.get("firma_id")
        bot_name = extra.get("bot_name")
        event_class = extra.get("event_class")
        try:
            if firma_id:
                row = conn.execute(
                    "SELECT estado, recurrencia FROM TBL_FIRMAS WHERE firma_id = ?",
                    (firma_id,),
                ).fetchone()
            elif bot_name and event_class:
                row = conn.execute(
                    "SELECT estado, recurrencia FROM TBL_FIRMAS "
                    "WHERE bot_name = ? AND event_class = ?",
                    (bot_name, event_class),
                ).fetchone()
            else:
                return False
            if row is None:
                return True
            if isinstance(row, sqlite3.Row):
                estado, recu = row["estado"], row["recurrencia"]
            else:
                estado, recu = row[0], row[1]
            if str(estado or "").lower() == "nueva":
                return int(recu or 1) <= 1
            return int(recu or 99) <= 1
        except Exception as exc:
            logger.debug("firma unprecedented check failed: %s", exc)
        return False

    def _muro_type_unseen(self, conn: Any, extra: Dict[str, Any]) -> bool:
        """Novel muro breach type: no prior row with this kind/label."""
        kind = (
            extra.get("muro_tipo")
            or extra.get("breach_type")
            or extra.get("risk_label")
            or extra.get("muro_kind")
        )
        if not kind:
            return False
        sql_candidates = (
            (
                "SELECT COUNT(*) FROM tbl_muro_eventos WHERE muro_breach = 1 "
                "AND (risk_label = ? OR walls_active = ?)",
                (kind, kind),
            ),
            (
                "SELECT COUNT(*) FROM tbl_muro WHERE muro_breach = 1 "
                "AND (risk_label = ? OR walls_active = ?)",
                (kind, kind),
            ),
            (
                "SELECT COUNT(*) FROM TBL_CICLOS WHERE muro_breach = 1 "
                "AND CAST(muro_walls_active AS TEXT) = ?",
                (str(kind),),
            ),
        )
        for sql, params in sql_candidates:
            try:
                row = conn.execute(sql, params).fetchone()
                n = int(row[0]) if row else 0
                # COUNT includes the row just written; novel means 0 or 1.
                return n <= 1
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    # Digest body (Spanish, non-expert, no lottery claims)
    # ------------------------------------------------------------------ #

    def _build_digest(
        self,
        snap: Dict[str, Any],
        drained: Sequence[BufferedAlert],
    ) -> tuple[str, str]:
        fantasma = snap.get("fantasma")
        nivel = snap.get("nivel") or snap.get("nivel_riesgo") or _nivel_from_fantasma(fantasma)
        muro_n = snap.get("muro_n")
        muro_den = snap.get("muro_den") or 5
        muro_breach = bool(snap.get("muro_breach"))
        loop_alive = snap.get("loop_alive")
        if loop_alive is None:
            age_min = snap.get("ciclo_age_min")
            loop_alive = age_min is None or float(age_min) < 20
        telemetry = snap.get("telemetry") or {}
        precursores = list(snap.get("precursores") or [])

        # Merge buffered precursor names into top list (unique, keep order).
        seen = {str(p.get("tipo") or p.get("display_name") or "") for p in precursores}
        for item in drained:
            name = item.extra.get("display_name") or item.extra.get("tipo")
            if not name:
                subj = (item.msg.subject or "").replace("[SENTINEL]", "")
                for prefix in ("PRECURSOR", "CONSENSO", "CONSENSUS"):
                    subj = subj.replace(prefix, "")
                name = subj.split("—")[0].split("-")[0].strip()
            if not name:
                name = item.msg.alert_type
            if name and name not in seen:
                seen.add(str(name))
                precursores.append(
                    {
                        "tipo": name,
                        "display_name": item.extra.get("display_name") or name,
                        "conf": item.extra.get("conf") or item.extra.get("confidence"),
                        "zona": item.extra.get("zona") or item.extra.get("lugar") or "",
                        "lugar": item.extra.get("lugar") or item.extra.get("zona") or "",
                        "lag_horas": item.extra.get("lag_horas"),
                        "detalle": item.extra.get("detalle") or "",
                        "id_nodo": item.extra.get("id_nodo"),
                        "nodo_nombre": item.extra.get("nodo_nombre"),
                        "lat": item.extra.get("lat"),
                        "lon": item.extra.get("lon"),
                    }
                )

        if fantasma is None:
            fant_line = "Fantasma: <code>n/d</code> — índice de estrés geofísico (Bz² + viento solar + Schumann). Sin lectura en esta hora."
        else:
            try:
                fv = float(fantasma)
            except (TypeError, ValueError):
                fv = 0.0
            meaning = (
                "calma relativa"
                if fv < 3
                else "actividad elevada — vigilar, no es un sismo"
                if fv < 6
                else "estrés alto — el índice subió; no es un pronóstico de sismo ni de epicentro"
            )
            fant_line = (
                f"👻 <b>Fantasma:</b> <code>{fv:.1f}</code> "
                f"(nivel {nivel or 'n/d'}) — {meaning}."
            )

        if muro_n is None:
            muro_line = "🧱 <b>Muro:</b> <code>n/d</code>/5 — cinco muros de precursores (geofísico, solar, volcánico, sísmico, cósmico)."
        else:
            try:
                mn = int(muro_n)
            except (TypeError, ValueError):
                mn = 0
            muro_txt = (
                f"rotos {mn}/{muro_den}" if muro_breach or mn > 0 else f"{mn}/{muro_den} activos"
            )
            muro_line = (
                f"🧱 <b>Muro:</b> <code>{muro_txt}</code> — cuántas de las 5 barreras "
                f"de precursores están encendidas. No significa que 'va a temblar'."
            )

        tel_bits = []
        bz = telemetry.get("bz_nT") or telemetry.get("bz")
        wind = telemetry.get("viento_km_s") or telemetry.get("wind")
        sch = telemetry.get("schumann_hz") or telemetry.get("schumann")
        kp = telemetry.get("kp")
        if bz is not None:
            try:
                tel_bits.append(f"Bz {float(bz):.1f} nT (campo magnético; negativo = grieta)")
            except (TypeError, ValueError):
                tel_bits.append(f"Bz {bz}")
        if wind is not None:
            try:
                tel_bits.append(f"viento solar {float(wind):.0f} km/s")
            except (TypeError, ValueError):
                tel_bits.append(f"viento {wind}")
        if sch is not None:
            try:
                tel_bits.append(f"Schumann {float(sch):.2f} Hz (latido de la Tierra)")
            except (TypeError, ValueError):
                tel_bits.append(f"Schumann {sch}")
        if kp is not None:
            tel_bits.append(f"Kp {kp} (tormenta geomagnética 0–9)")
        tel_line = (
            "🛰 <b>Telemetría:</b> " + " · ".join(tel_bits)
            if tel_bits
            else "🛰 <b>Telemetría:</b> sin one-liners en esta hora (APIs en silencio o ciclo sin datos)."
        )

        if precursores:
            prec_lines = ["📡 <b>Precursores (detalle):</b>"]
            for row in precursores[:8]:
                tipo = row.get("display_name") or row.get("tipo") or "?"
                conf = row.get("conf") or row.get("confidence") or row.get("value")
                conf_s = ""
                if conf is not None:
                    try:
                        cf = float(conf)
                        conf_s = ("%.0f%%" % (cf * 100)) if cf <= 1.5 else ("%.1f" % cf)
                    except (TypeError, ValueError):
                        conf_s = str(conf)
                lugar = row.get("lugar") or row.get("zona") or ""
                lag_h = row.get("lag_horas")
                lag_s = ""
                if lag_h:
                    try:
                        lh = float(lag_h)
                        lag_s = f" · lag ~{lh:.0f}h"
                    except (TypeError, ValueError):
                        pass
                det = row.get("detalle") or ""
                line = "  · <b>%s</b>" % tipo
                if conf_s:
                    line += " · conf <code>%s</code>" % conf_s
                if lugar:
                    line += chr(10) + "     📍 " + str(lugar)
                if lag_s:
                    line += lag_s
                if det:
                    line += chr(10) + "     📋 " + str(det)
                prec_lines.append(line)
            prec_block = chr(10).join(prec_lines)
        else:
            prec_block = "📡 <b>Precursores:</b> ninguno nuevo esta hora — el sistema igual sigue midiendo."

        alive_txt = (
            "💓 Loop <b>vivo</b> — el ciclo del Padre corrió."
            if loop_alive
            else "💀 Loop <b>sin pulso reciente</b> — si ves esto en el digest y no llegó un aviso inmediato, revisa launcher."
        )

        n_buf = len(drained)
        buf_note = (
            f"Se agruparon <code>{n_buf}</code> avisos rutinarios (precursores / firmas ya vistas) en este reporte."
            if n_buf
            else "Hora calma: no hubo avisos rutinarios que agrupar. El reporte sale igual."
        )

        url = webapp_url()
        if url.lower().startswith("https://"):
            dash = f"🔗 <b>Mini App:</b> {url}"
        else:
            dash = (
                "🔗 Mini App: configura <code>TELEGRAM_WEBAPP_URL</code> "
                "(HTTPS público del dashboard /mini). Este bot no abre túneles."
            )

        model_status = get_model_status(self.db_path)
        vara = get_vara_juez(self.db_path)

        html = (
            f"<b>SENTINEL OMEGA — REPORTE HORARIO</b>\n"
            f"<i>{_now_utc_str()} · {_mx_str()}</i>\n\n"
            f"{fant_line}\n"
            f"{muro_line}\n"
            f"{tel_line}\n"
            f"{prec_block}\n"
            f"{alive_txt}\n\n"
            f"{vara}\n\n"
            f"{model_status}\n\n"
            f"{buf_note}\n"
            f"{dash}\n\n"
            f"<i>Esto no es un pronóstico de sismo ni de epicentro. "
            f"Es el concentrado de lo que midió el Padre en la última hora.</i>"
        )
        fv_s = f"{float(fantasma):.1f}" if fantasma is not None else "n/d"
        subject = f"[SENTINEL] REPORTE HORARIO Fantasma {fv_s} muro {muro_n or 'n'}/{muro_den}"
        return html, subject

    def _load_snapshot(self) -> Dict[str, Any]:
        path = self.db_path
        snap: Dict[str, Any] = {}
        if not path or not os.path.exists(path):
            return snap
        conn = None
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT fantasma, schumann_hz, kp, bz_nT, viento_km_s, nivel_riesgo "
                    "FROM tbl_precursores_cosmicos ORDER BY ts DESC LIMIT 1"
                ).fetchone()
            except Exception:
                row = None
            if row is None:
                try:
                    row = conn.execute(
                        "SELECT fantasma FROM tbl_salud_sistema ORDER BY ts DESC LIMIT 1"
                    ).fetchone()
                except Exception:
                    row = None
            if row is not None:
                keys = row.keys() if isinstance(row, sqlite3.Row) else []
                if "fantasma" in keys:
                    snap["fantasma"] = row["fantasma"]
                elif row[0] is not None:
                    snap["fantasma"] = row[0]
                if "nivel_riesgo" in keys:
                    snap["nivel"] = row["nivel_riesgo"]
                tel = {}
                for src, dst in (
                    ("bz_nT", "bz_nT"),
                    ("viento_km_s", "viento_km_s"),
                    ("schumann_hz", "schumann_hz"),
                    ("kp", "kp"),
                ):
                    if src in keys:
                        tel[dst] = row[src]
                if tel:
                    snap["telemetry"] = tel
            try:
                mrow = conn.execute(
                    "SELECT walls_active, muro_breach, risk_label "
                    "FROM tbl_muro ORDER BY ts DESC LIMIT 1"
                ).fetchone()
            except Exception:
                try:
                    mrow = conn.execute(
                        "SELECT muro_walls_active, muro_breach "
                        "FROM TBL_CICLOS ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                except Exception:
                    mrow = None
            if mrow is not None:
                if isinstance(mrow, sqlite3.Row):
                    keys = mrow.keys()
                    snap["muro_n"] = mrow["walls_active"] if "walls_active" in keys else (
                        mrow["muro_walls_active"] if "muro_walls_active" in keys else None
                    )
                    snap["muro_breach"] = bool(mrow["muro_breach"]) if "muro_breach" in keys else False
                else:
                    snap["muro_n"] = mrow[0]
                    snap["muro_breach"] = bool(mrow[1]) if len(mrow) > 1 else False
            try:
                crow = conn.execute(
                    "SELECT ts FROM tbl_salud_sistema ORDER BY ts DESC LIMIT 1"
                ).fetchone()
                if crow and crow[0]:
                    # ts may be epoch or ISO.
                    ts_val = crow[0]
                    age_min = None
                    try:
                        age_min = (time.time() - float(ts_val)) / 60.0
                    except (TypeError, ValueError):
                        try:
                            dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            age_min = (time.time() - dt.timestamp()) / 60.0
                        except Exception:
                            age_min = None
                    if age_min is not None:
                        snap["ciclo_age_min"] = age_min
                        snap["loop_alive"] = age_min < 20
            except Exception:
                pass
            try:
                dets = conn.execute(
                    "SELECT tipo, display_name, station, lat, lon, confidence, values_json "
                    "FROM TBL_DETECCIONES ORDER BY id DESC LIMIT 8"
                ).fetchall()
                from sentinel_omega.infrastructure.messaging.alert_enrichment import (
                    enrich_precursor_row,
                )
                enriched = []
                for r in dets:
                    if isinstance(r, sqlite3.Row):
                        tipo = r["tipo"]; dn = r["display_name"]; st = r["station"]
                        lat = r["lat"]; lon = r["lon"]; conf = r["confidence"]; vals = r["values_json"]
                    else:
                        tipo, dn, st, lat, lon, conf, vals = r
                    enriched.append(
                        enrich_precursor_row(
                            conn,
                            tipo=str(tipo or ""),
                            display_name=dn,
                            station=st,
                            lat=lat,
                            lon=lon,
                            values=vals,
                            confidence=conf,
                        )
                    )
                # keep newest unique by tipo (avoid 4x same cluster in digest)
                seen = set()
                uniq = []
                for row in enriched:
                    key = str(row.get("tipo") or row.get("display_name") or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    uniq.append(row)
                snap["precursores"] = uniq
            except Exception:
                try:
                    dets = conn.execute(
                        "SELECT tipo, confidence, station FROM tbl_detecciones "
                        "ORDER BY id DESC LIMIT 5"
                    ).fetchall()
                    snap["precursores"] = [
                        {
                            "tipo": r[0] if not isinstance(r, sqlite3.Row) else r["tipo"],
                            "conf": r[1] if not isinstance(r, sqlite3.Row) else r["confidence"],
                            "zona": r[2] if not isinstance(r, sqlite3.Row) else r["station"],
                        }
                        for r in dets
                    ]
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("digest snapshot DB failed: %s", exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        return snap

    # ------------------------------------------------------------------ #
    # Send (gated for immediate; never on dry_run)
    # ------------------------------------------------------------------ #

    def _dispatch_immediate(
        self, msg: FormattedMessage, extra: Dict[str, Any]
    ) -> DispatchRecord:
        html = AlertTemplates.sin_precedente(msg)
        markup = webapp_reply_markup()
        rec = DispatchRecord(
            kind="immediate",
            alert_type=msg.alert_type,
            html=html,
            subject=msg.subject,
            ts=self._now(),
            dry_run=self.dry_run,
            reply_markup=markup,
        )
        rec.sent = self._send(
            html,
            msg.alert_type,
            cooldown=IMMEDIATE_COOLDOWN_S,
            reply_markup=markup,
        )
        self.dispatched.append(rec)
        return rec

    def _send(
        self,
        html: str,
        alert_type: str,
        cooldown: int,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> bool:
        # Local cooldown so we don't spam the same unprecedented type
        # (applies in dry_run too — tests assert this; prod uses send_alert_gated).
        if cooldown > 0:
            last = self._immediate_last.get(alert_type, 0.0)
            if last and (self._now() - last) < cooldown:
                logger.debug("CONSENSO cooldown skip: %s", alert_type)
                return False
        if self.dry_run:
            self._immediate_last[alert_type] = self._now()
            logger.info(
                "[DRY_RUN] CONSENSO %s: %s",
                alert_type,
                html[:180].replace("\n", " "),
            )
            return True
        try:
            from sentinel_omega.infrastructure.api.telegram import send_alert_gated

            ok = bool(
                send_alert_gated(
                    html,
                    alert_type,
                    cooldown=cooldown if cooldown > 0 else 1,
                    reply_markup=reply_markup,
                )
            )
            if ok:
                self._immediate_last[alert_type] = self._now()
            return ok
        except Exception as exc:
            # `sin_token`: la excepción de `requests` trae la URL, y la URL de la
            # API de Telegram lleva el token DENTRO (/bot<token>/sendMessage).
            # Rotar el token no arregla esto --- el siguiente fallo filtra el nuevo.
            from sentinel_omega.infrastructure.api.telegram import sin_token
            logger.error("CONSENSO telegram failed: %s", sin_token(exc))
            return False


_VIGILANTE: Optional[ConsensoVigilante] = None


def get_vigilante(dry_run: Optional[bool] = None, **kwargs: Any) -> ConsensoVigilante:
    """Process-wide watcher. Tests should construct ConsensoVigilante() directly."""
    global _VIGILANTE
    if _VIGILANTE is None:
        _VIGILANTE = ConsensoVigilante(dry_run=dry_run, **kwargs)
    elif dry_run is not None:
        _VIGILANTE.dry_run = bool(dry_run)
    return _VIGILANTE


def reset_vigilante() -> None:
    """Tests only."""
    global _VIGILANTE
    _VIGILANTE = None


def _nivel_from_fantasma(fantasma: Any) -> str:
    try:
        v = float(fantasma)
    except (TypeError, ValueError):
        return "n/d"
    if v >= 6:
        return "alto"
    if v >= 3:
        return "medio"
    return "bajo"
