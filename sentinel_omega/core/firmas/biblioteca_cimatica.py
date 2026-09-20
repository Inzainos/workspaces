"""Helpers para consulta de biblioteca cimática en modo lectura.

Este módulo se usa por el dashboard (/api/cimatica/ahora).
No inventa datos: si la biblioteca no existe o está vacía, consulta
contra tbl_cimatica_patrones como fallback de similitud por clave.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, List, Tuple

from .cimatica import clave_patron


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return bool(row)


def ensure_biblioteca(conn: sqlite3.Connection) -> None:
    """Crea tabla de biblioteca cuando la conexión es writable.

    En dashboard RO esto puede fallar (expected) y el caller debe tolerarlo.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tbl_cimatica_biblioteca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave_figura TEXT,
            event_class TEXT,
            n_eventos INTEGER DEFAULT 0,
            figura_json TEXT,
            factores_json TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cimatica_bib_clave ON tbl_cimatica_biblioteca(clave_figura)"
    )


def _norm(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _items_from_dict(d: Dict[str, Any]) -> List[Tuple[str, float]]:
    out: List[Tuple[str, float]] = []
    for k, v in sorted((d or {}).items()):
        if isinstance(v, (int, float)):
            out.append((str(k), _norm(v)))
    return out


def _similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Similitud simple [0..1] sobre features numéricas compartidas."""
    ia = dict(_items_from_dict(a))
    ib = dict(_items_from_dict(b))
    if not ia and not ib:
        return 0.0
    keys = sorted(set(ia.keys()) | set(ib.keys()))
    if not keys:
        return 0.0
    score = 0.0
    for k in keys:
        va = ia.get(k, 0.0)
        vb = ib.get(k, 0.0)
        den = abs(va) + abs(vb) + 1e-9
        score += max(0.0, 1.0 - abs(va - vb) / den)
    return round(score / len(keys), 4)


def _load_pattern_rows(conn: sqlite3.Connection, limit: int = 250) -> Iterable[sqlite3.Row]:
    if not _table_exists(conn, "tbl_cimatica_patrones"):
        return []
    return conn.execute(
        """
        SELECT patron_id, clave, ambito, id_nodo, event_class, frecuencia,
               primera_vez, ultima_vez, telemetria_json
        FROM tbl_cimatica_patrones
        ORDER BY ultima_vez DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def consultar(
    conn: sqlite3.Connection,
    figura: Dict[str, Any],
    factores: Dict[str, Any],
    clave_figura: str = "",
) -> Dict[str, Any]:
    """Busca similares de manera robusta.

    Prioridad:
    1) coincidencias en tbl_cimatica_biblioteca (si existe y hay filas)
    2) fallback en tbl_cimatica_patrones por similitud de telemetría
    """
    query = {**(figura or {}), **(factores or {})}
    if not clave_figura:
        try:
            clave_figura = clave_patron(query)
        except Exception:
            clave_figura = ""

    similares: List[Dict[str, Any]] = []

    # 1) Biblioteca explícita
    if _table_exists(conn, "tbl_cimatica_biblioteca"):
        rows = conn.execute(
            """
            SELECT clave_figura, event_class, n_eventos, updated_at
            FROM tbl_cimatica_biblioteca
            ORDER BY n_eventos DESC, updated_at DESC
            LIMIT 300
            """
        ).fetchall()
        for r in rows:
            k = str(r["clave_figura"] or "")
            if not k:
                continue
            sim = 1.0 if clave_figura and k == clave_figura else 0.0
            if sim <= 0 and clave_figura:
                # similitud tokenizada sobre clave "k:v|..."
                a = set(clave_figura.split("|"))
                b = set(k.split("|"))
                inter = len(a & b)
                union = max(1, len(a | b))
                sim = round(inter / union, 4)
            if sim > 0:
                similares.append(
                    {
                        "source": "tbl_cimatica_biblioteca",
                        "clave": k,
                        "event_class": r["event_class"],
                        "n_eventos": int(r["n_eventos"] or 0),
                        "similarity": sim,
                        "updated_at": r["updated_at"],
                    }
                )

    # 2) Fallback patrones
    if not similares:
        for r in _load_pattern_rows(conn, limit=500):
            row_features: Dict[str, Any] = {}
            txt = r["telemetria_json"]
            if isinstance(txt, str) and txt.strip().startswith("{"):
                import json

                try:
                    row_features = json.loads(txt)
                except Exception:
                    row_features = {}
            sim = 0.0
            if row_features and query:
                sim = _similarity(query, row_features)
            elif clave_figura:
                rk = str(r["clave"] or "")
                if rk:
                    a = set(clave_figura.split("|"))
                    b = set(rk.split("|"))
                    inter = len(a & b)
                    union = max(1, len(a | b))
                    sim = round(inter / union, 4)
            if sim <= 0:
                continue
            similares.append(
                {
                    "source": "tbl_cimatica_patrones",
                    "patron_id": r["patron_id"],
                    "clave": r["clave"],
                    "ambito": r["ambito"],
                    "id_nodo": r["id_nodo"],
                    "event_class": r["event_class"],
                    "frecuencia": int(r["frecuencia"] or 0),
                    "ultima_vez": r["ultima_vez"],
                    "similarity": sim,
                }
            )

    similares.sort(key=lambda x: (float(x.get("similarity") or 0.0), int(x.get("frecuencia") or x.get("n_eventos") or 0)), reverse=True)
    similares = similares[:20]
    best = float(similares[0]["similarity"]) if similares else 0.0

    return {
        "similares": similares,
        "n_hits": len(similares),
        "best_similarity": best,
        "live_train": False,
    }
