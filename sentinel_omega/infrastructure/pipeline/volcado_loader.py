"""Volcado 24h vivo\u2192hist\u00f3rico + cascada. Expands from volcado_24h.b64."""
from __future__ import annotations
import base64, zlib
from pathlib import Path

_src = zlib.decompress(
    base64.b64decode(
        (Path(__file__).with_name("volcado_24h.b64")).read_text(encoding="ascii").strip()
    )
).decode("utf-8")

def apply_to_mantenimiento():
    import sentinel_omega.infrastructure.pipeline.mantenimiento as m
    ns = {}
    import logging, sqlite3, time
    from datetime import datetime, timezone, timedelta
    from typing import Any, Dict, Optional
    ns.update(dict(
        logging=logging, sqlite3=sqlite3, time=time,
        datetime=datetime, timezone=timezone, timedelta=timedelta,
        Any=Any, Dict=Dict, Optional=Optional,
        logger=logging.getLogger(m.__name__),
    ))
    exec(compile(_src, "volcado_expanded", "exec"), ns)
    for name, obj in ns.items():
        if name in ("volcar_telemetria_viva", "_ensure_hist_tables") or (
            name.startswith("_ensure") and callable(obj)
        ):
            setattr(m, name, obj)
    if "volcar_telemetria_viva" in ns:
        setattr(m, "volcar_telemetria_viva", ns["volcar_telemetria_viva"])
        return True
    return False

try:
    apply_to_mantenimiento()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("volcado apply failed: %s", e)
