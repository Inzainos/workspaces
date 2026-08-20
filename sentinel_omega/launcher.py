"""Sentinel Omega — Launcher (self-expanding from launcher_hex/)."""
from __future__ import annotations
import zlib
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "launcher_hex"

def _load() -> str:
    parts = sorted(_DIR.glob("h*.hex"))
    if not parts:
        raise RuntimeError(f"launcher_hex missing under {_DIR}")
    hx = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    return zlib.decompress(bytes.fromhex(hx)).decode("utf-8")

exec(compile(_load(), str(Path(__file__).resolve()), "exec"), globals())
