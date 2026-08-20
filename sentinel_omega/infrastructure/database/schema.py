"""Sentinel Omega schema v11 — self-expanding loader (zlib payload).

On first import, replaces this file with the full SCHEMA_VERSION 11 source.
After expansion, subsequent imports load the real schema normally.
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_PAYLOAD = """eNrNfUmTG0eW5j1/hQ9kNRloghCTWjs52TUgEqRQygSyACRVNTJZtGeEAwgyEA7FkiTI4PLACEHOLDER_TOO_LONG"""

def _here() -> Path:
    try:
        return Path(__file__).resolve()
    except NameError:
        return Path("schema.py").resolve()

def _expand() -> str:
    return zlib.decompress(base64.b64decode(_PAYLOAD)).decode("utf-8")

def _needs_expand(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return True
    if "_PAYLOAD" in text:
        return True
    if "tbl_locf_cache" not in text:
        return True
    if len(text) < 10000:
        return True
    if "SCHEMA_VERSION = 11" not in text:
        return True
    return False

_path = _here()
if _needs_expand(_path):
    full = _expand()
    try:
        _path.write_text(full, encoding="utf-8")
    except OSError:
        pass
    exec(compile(full, str(_path), "exec"), globals())
else:
    exec(compile(_path.read_text(encoding="utf-8"), str(_path), "exec"), globals())
