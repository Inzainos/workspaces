"""
Schumann Resonance connector — Tomsk Observatory (sosrff.tsu.ru).
Public spectrogram images, no authentication required.

Method: Computer vision (WPC — White Pixel Count) on HSV-filtered
spectrogram to estimate resonance excitation above the 7.83 Hz fundamental.

IMPORTANT (2026-09-10 ingest fix):
  - Tomsk HTTP redirects to HTTPS with an *expired* certificate. We must
    fetch with verify=False for sosrff.tsu.ru only, otherwise every cycle
    silently falls back to (7.83, 0.0) and poisons tbl_schumann_vivo.
  - On any failure we return None (not a fake baseline) so callers can skip
    INSERT / mark LOCF instead of writing synthetic zeros.

FROZEN IMAGE (2026-09-27): shm.jpg answers HTTP 200 with
``Last-Modified: Mon, 01 Sep 2025 04:20:00 GMT``. The same image yields
activity 21.46 % -> 7.83 + 21.46*0.02 = 8.26 Hz (25.0 Hz with the old *0.8
scale): the "reading" that froze PREC from 24-jul to 26-sep and came back at
19:45 CST on 27-sep. A WPC value is only a live reading when the image carries
its own timestamp (Last-Modified), that timestamp is recent, and the value is
not an exact repeat of the last stored live reading of an earlier hour.
"""

from __future__ import annotations

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

TOMSK_URL = "http://sosrff.tsu.ru/new/shm.jpg"
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
    """Download today's Schumann spectrogram from Tomsk Observatory.

    Uses verify=False because sosrff.tsu.ru presents an expired TLS cert
    after the HTTP→HTTPS redirect (confirmed 2026-09-10).
    """
    try:
        resp = get_session().get(TOMSK_URL, timeout=TIMEOUT, verify=False)
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


def analyze_spectrogram(image_path: str) -> Optional[Tuple[float, float]]:
    """
    Analyze Tomsk spectrogram via WPC (White Pixel Count).

    Returns:
        (schumann_hz, activity_pct) or None on failure / missing opencv.
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

        schumann_hz = round(FUNDAMENTAL_HZ + (activity_pct * 0.02), 2)

        logger.info(
            f"Schumann WPC: {schumann_hz} Hz, activity={activity_pct}%"
        )
        return schumann_hz, activity_pct
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


def fetch_schumann_resonance(
    save_dir: Optional[str] = None,
    cleanup: bool = True,
    previa=_NO_LEIDA,
    ahora: Optional[float] = None,
) -> Optional[Tuple[float, float]]:
    """
    Full pipeline: download spectrogram → WPC analysis → (hz, activity_pct).

    Returns None on any failure (network, SSL, missing cv2, bad image), and
    also when the value is not a live reading: image without Last-Modified,
    older than MAX_EDAD_IMAGEN_HORAS, or identical to the previous stored live
    reading (``previa``; read from tbl_schumann_vivo when not given).
    Callers MUST NOT invent 7.83/0.0; skip persist or use LOCF instead.
    """
    import os
    import urllib3

    # Tomsk cert is expired; silence the single-host InsecureRequestWarning noise.
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    path = fetch_schumann_spectrogram(save_dir=save_dir)
    if path is None:
        return None
    last_modified = last_modified_de(path)

    result = analyze_spectrogram(path)

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
    motivo = motivo_lectura_no_viva(hz, pct, last_modified, previa, ahora=ahora)
    if motivo:
        logger.warning(
            "Schumann WPC %s Hz / %s %% is not a live reading (%s) — no-signal", hz, pct, motivo
        )
        return None

    return hz, pct
