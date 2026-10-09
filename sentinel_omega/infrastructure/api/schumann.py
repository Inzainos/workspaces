"""
Schumann Resonance connector — sos70.ru (sucesor de Tomsk, sosrff.tsu.ru).

Public spectrogram images, no authentication required.

Method: Computer vision (WPC — White Pixel Count) on HSV-filtered
spectrogram to estimate resonance excitation above the 7.83 Hz fundamental.

IMPORTANT (2026-09-10 ingest fix):
  - On any failure we return None (not a fake baseline) so callers can skip
    INSERT / mark LOCF instead of writing synthetic zeros.

FROZEN IMAGE (2026-09-27): the old sosrff.tsu.ru answered HTTP 200 with
``Last-Modified: Mon, 01 Sep 2025 04:20:00 GMT`` and the same image yielded
activity 21.46 % -> 7.83 + 21.46*0.02 = 8.26 Hz: the "reading" that froze PREC
from 24-jul to 26-sep. sosrff.tsu.ru is the OBSOLETE site; sos70.ru is its
successor and serves the same shm.jpg updated every ~6 h.

FUENTE NUEVA (2026-09-30): sos70.ru does NOT send Last-Modified (verified
with GET: only `date`). The freshness gate for that case is the IMAGE HASH:
the sha256 of the downloaded bytes against the sha of the image that produced
the last en_vivo=1 reading (`tbl_schumann_img_estado`, one row). Same hash =
no new data = no-signal; different hash + a value that moved = live reading.
If the source ever sends Last-Modified again, the original age gate applies
unchanged.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from sentinel_omega.infrastructure.api._http import get_session

logger = logging.getLogger(__name__)

# sosrff.tsu.ru está MUERTO (imagen congelada 13 meses, sección 26 de la
# bitácora del 28-sep). El sucesor sos70.ru sirve el mismo shm.jpg vivo.
TOMSK_URL = "https://sos70.ru/provider.php?file=shm.jpg"
UA = "Mozilla/5.0 (X11; Linux x86_64) SentinelOmega-schumann/1.0"
TIMEOUT = 15
FUNDAMENTAL_HZ = 7.83
ROI_FRACTION = 0.4
HSV_LOWER = np.array([0, 0, 180])
HSV_UPPER = np.array([180, 60, 255])
# A spectrogram older than this is not a live reading (Tomsk refreshes it
# several times a day when it works).
MAX_EDAD_IMAGEN_HORAS = 6.0
_DB_DEFAULT = Path(__file__).resolve().parents[2] / "data" / "SENTINEL_OMEGA_PRO.db"
_NO_LEIDA = object()
_LAST_MODIFIED: dict = {}  # path -> Last-Modified (UTC) of the downloaded image


def fetch_schumann_spectrogram(
    save_dir: Optional[str] = None,
) -> Optional[str]:
    """Download the current Schumann spectrogram from sos70.ru.

    Proper HTTPS (valid cert): no verify=False needed since the sosrff era
    ended. The image's Last-Modified is kept for the age gate; sos70 does not
    send it today, in which case the sha256 gate applies (see module docstring).
    """
    try:
        resp = get_session().get(
            TOMSK_URL, timeout=TIMEOUT, headers={"User-Agent": UA}
        )
        resp.raise_for_status()

        if save_dir:
            path = Path(save_dir) / "tomsk_live.jpg"
        else:
            fd, path_str = tempfile.mkstemp(suffix=".jpg", prefix="tomsk_")
            import os
            os.close(fd)
            path = Path(path_str)

        path.write_bytes(resp.content)
        logger.info(f"Tomsk spectrogram downloaded: {path} ({len(resp.content)} bytes)")
        # The image's own timestamp, kept next to its path for the freshness check.
        _LAST_MODIFIED[str(path)] = _parse_last_modified(resp.headers.get("Last-Modified"))
        return str(path)
    except Exception as e:
        logger.error(f"Tomsk spectrogram download failed: {e}")
        return None


def analyze_spectrogram(image_path: str) -> Optional[Tuple[Optional[float], float]]:
    """Cuenta de pixeles claros del espectrograma de Tomsk (WPC).

    Devuelve `(None, activity_pct)`: la ACTIVIDAD es una medicion real ---la
    fraccion de pixeles brillantes en la region de interes--- y la FRECUENCIA es
    `None` porque **de un conteo de pixeles no sale una frecuencia**.

    Hasta el 2026-10-09 esta funcion devolvia

        schumann_hz = round(FUNDAMENTAL_HZ + (activity_pct * 0.02), 2)

    o sea una RECTA sobre la actividad, guardada en una columna llamada `_hz` y
    comparada despues contra 7,83 como si fuera la fundamental medida. Medido
    ese dia: la formula se cumple exacto en **583 de 743 filas** de
    `TBL_PRECURSORES_COSMICOS`, asi que actividad y «frecuencia» eran **un
    numero con dos nombres**. Es la regla dura 2 ---un derivado etiquetado como
    dato de sensor--- en el eje del proyecto: la resonancia Schumann es el
    latido contra el que todo se correlaciona.

    Consecuencia medida de haberlo fabricado: de 4.000 firmas de beta1/padre,
    **86 llevan un rasgo de Schumann (2,2 %)** y su recorrido entero es de
    **0,03 Hz** (7,860 a 7,891). El latido nunca entro a la memoria.

    La frecuencia de verdad SI se puede tener, pero no de aqui: hace falta la
    serie calibrada de una estacion ELF (ajuste lorentziano sobre la banda
    6-25 Hz). Ver `docs/SCHUMANN_FUENTES.md`.
    """
    try:
        import cv2
    except ImportError:
        logger.error(
            "opencv-python not installed — cannot analyze Schumann spectrogram. "
            "Install: pip install opencv-python-headless"
        )
        return None

    if not image_path:
        return None

    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Could not read image: {image_path}")
            return None

        h, w, _ = img.shape
        roi = img[0:int(h * ROI_FRACTION), 0:w]

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

        total_pixels = mask.size
        active_pixels = cv2.countNonZero(mask)
        activity_pct = round((active_pixels / total_pixels) * 100, 2)

        # La frecuencia NO se fabrica. Un conteo de pixeles mide intensidad,
        # no frecuencia: devolver `7.83 + actividad*0.02` era inventar la
        # fundamental a partir del brillo. `None` = sin dato, y los consumidores
        # ya lo tratan como tal (`valor_medido`, `_es_dato`, «sin dato»).
        logger.info("Schumann WPC: actividad=%s%% (frecuencia: sin medir --- "
                    "de un conteo de pixeles no sale una frecuencia)",
                    activity_pct)
        return None, activity_pct
    except Exception as e:
        logger.error(f"Spectrogram analysis failed: {e}")
        return None


def last_modified_de(path: Optional[str]) -> Optional[datetime]:
    """Last-Modified of an image downloaded by fetch_schumann_spectrogram (popped)."""
    return _LAST_MODIFIED.pop(str(path), None) if path else None


def _parse_last_modified(valor: Optional[str]) -> Optional[datetime]:
    if not valor:
        return None
    try:
        dt = parsedate_to_datetime(valor)
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def ultima_lectura_viva(
    db_path: Optional[Path] = None, ahora: Optional[float] = None,
) -> Optional[Tuple[float, float]]:
    """Last live (en_vivo=1) reading in tbl_schumann_vivo from an EARLIER hour
    block, read-only. None if there is none or the DB is unavailable."""
    db = Path(db_path) if db_path else _DB_DEFAULT
    if not db.exists():
        return None
    blk = time.strftime("%Y-%m-%d %H:00", time.gmtime(time.time() if ahora is None else ahora))
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(tbl_schumann_vivo)")}
            filtro = " AND COALESCE(en_vivo,1)=1" if "en_vivo" in cols else ""
            r = con.execute(
                "SELECT schumann_hz, schumann_activity FROM tbl_schumann_vivo "
                "WHERE timestamp_blk < ? AND schumann_hz IS NOT NULL "
                "AND schumann_activity IS NOT NULL" + filtro +
                " ORDER BY timestamp_blk DESC LIMIT 1", (blk,)).fetchone()
        finally:
            con.close()
    except sqlite3.Error as exc:
        logger.warning("Schumann: could not read last live reading: %s", exc)
        return None
    return (float(r[0]), float(r[1])) if r else None


def motivo_lectura_no_viva(
    hz: float,
    activity: float,
    last_modified: Optional[datetime],
    previa: Optional[Tuple[float, float]],
    ahora: Optional[float] = None,
    max_edad_horas: float = MAX_EDAD_IMAGEN_HORAS,
) -> Optional[str]:
    """Why a WPC value is NOT a live reading, or None if it is."""
    if last_modified is None:
        return "spectrogram has no Last-Modified timestamp"
    now = time.time() if ahora is None else ahora
    edad_h = (now - last_modified.timestamp()) / 3600.0
    if edad_h > max_edad_horas:
        return f"spectrogram is {edad_h:.1f} h old (Last-Modified {last_modified.isoformat()})"
    if previa is not None:
        p_hz, p_act = previa
        if abs(float(hz) - p_hz) < 1e-9 and abs(float(activity) - p_act) < 1e-9:
            return f"identical to the previous stored reading ({p_hz} Hz, {p_act} %)"
    return None


def is_baseline_placeholder(hz: Optional[float], activity: Optional[float]) -> bool:
    """True when values look like the historical fake fallback (7.83, 0.0)."""
    if hz is None or activity is None:
        return True
    try:
        return abs(float(hz) - FUNDAMENTAL_HZ) < 1e-9 and float(activity) == 0.0
    except (TypeError, ValueError):
        return True


# ── Puerta de frescura por sha256 (sos70 no manda Last-Modified) ─────────────

_TABLA_IMG_ESTADO = "tbl_schumann_img_estado"


def _sha256_archivo(ruta: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            for bloque in iter(lambda: f.read(65536), b""):
                h.update(bloque)
        return h.hexdigest()
    except OSError as e:
        logger.warning("Schumann: no se pudo hashear la imagen: %s", e)
        return None


def sha_ingestado(db_path: Optional[Path] = None) -> Optional[str]:
    """sha256 de la imagen que produjo la última lectura viva; None si no hay."""
    db = Path(db_path) if db_path else _DB_DEFAULT
    if not db.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            r = con.execute(
                f"SELECT sha256 FROM {_TABLA_IMG_ESTADO} WHERE id=1"
            ).fetchone()
        finally:
            con.close()
        return r[0] if r else None
    except sqlite3.Error as e:
        logger.warning("Schumann: no se pudo leer el sha ingestado: %s", e)
        return None


def guardar_sha_ingestado(sha: str, db_path: Optional[Path] = None) -> bool:
    """Guarda el sha de la imagen recién aceptada. Una sola fila (id=1)."""
    db = Path(db_path) if db_path else _DB_DEFAULT
    try:
        con = sqlite3.connect(db, timeout=60)
        try:
            con.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLA_IMG_ESTADO} ("
                "id INTEGER PRIMARY KEY CHECK (id=1), sha256 TEXT NOT NULL, "
                "actualizado_at TEXT DEFAULT (datetime('now')))"
            )
            con.execute(
                f"INSERT INTO {_TABLA_IMG_ESTADO} (id, sha256) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET sha256=excluded.sha256, "
                "actualizado_at=datetime('now')",
                (sha,),
            )
            con.commit()
        finally:
            con.close()
        return True
    except sqlite3.Error as e:
        logger.warning("Schumann: no se pudo guardar el sha ingestado: %s", e)
        return False


def fetch_schumann_resonance(
    save_dir: Optional[str] = None,
    cleanup: bool = True,
    previa=_NO_LEIDA,
    ahora: Optional[float] = None,
    db_path: Optional[Path] = None,
) -> Optional[Tuple[float, float]]:
    """
    Full pipeline: download spectrogram → WPC analysis → (hz, activity_pct).

    Returns None on any failure (network, missing cv2, bad image), and also
    when the value is not a live reading. With Last-Modified: the age and
    repeat gates apply (original 2026-09-27 behavior). Without it (sos70
    today): the freshness proof is the image sha256 against the last
    ingested image — same sha = no new data = no-signal; new sha with a value
    that moved = live reading.
    Callers MUST NOT invent 7.83/0.0; skip persist or use LOCF instead.
    """
    import os

    path = fetch_schumann_spectrogram(save_dir=save_dir)
    if path is None:
        return None
    last_modified = last_modified_de(path)

    result = analyze_spectrogram(path)
    # El sha se calcula ANTES del cleanup: sin archivo no hay prueba de cambio.
    sha_img = _sha256_archivo(path)

    if cleanup and path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

    if result is None:
        return None

    hz, pct = result
    if is_baseline_placeholder(hz, pct):
        # Extremely quiet spectrogram is possible but indistinguishable from
        # the old fake fallback; treat as no-signal so we do not keep writing
        # identical placeholder rows every hour.
        logger.warning(
            "Schumann WPC returned baseline placeholder (7.83, 0.0) — "
            "treating as no-signal (skip persist)"
        )
        return None

    if previa is _NO_LEIDA:
        previa = ultima_lectura_viva(ahora=ahora)

    if last_modified is not None:
        motivo = motivo_lectura_no_viva(hz, pct, last_modified, previa, ahora=ahora)
    else:
        # sos70 no manda Last-Modified: la prueba de frescura es el cambio de
        # imagen (sha256 contra la última imagen ingestada).
        motivo = None
        prev_sha = sha_ingestado(db_path)
        if sha_img is None:
            motivo = "no se pudo hashear la imagen descargada"
        elif prev_sha is not None and sha_img == prev_sha:
            motivo = (
                "imagen sin cambios desde la última lectura viva "
                f"(sha256 {sha_img[:12]})"
            )
        elif (
            previa is not None
            and abs(float(hz) - float(previa[0])) < 1e-9
            and abs(float(pct) - float(previa[1])) < 1e-9
        ):
            # Regla del 2026-09-27 conservada: un valor que repite exacto la
            # última lectura viva no aporta información, venga de una imagen
            # nueva o no. El arrastre de `registrar` hace el resto.
            motivo = (
                "imagen nueva pero el valor repite la última lectura viva "
                f"({hz} Hz, {pct} %)"
            )
        if motivo is None and sha_img is not None:
            if not guardar_sha_ingestado(sha_img, db_path):
                logger.warning(
                    "Schumann: sha no guardado — la próxima imagen idéntica "
                    "volverá a evaluarse"
                )

    if motivo:
        logger.warning(
            "Schumann WPC %s Hz / %s %% is not a live reading (%s) — no-signal",
            hz, pct, motivo,
        )
        return None

    return hz, pct
