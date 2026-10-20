"""Report visibility: live-only agents must appear even with 0 firmas.

jupiter retired 2026-10-18; alfa2 is the remaining live-only agent.
"""

import importlib.util
from pathlib import Path

from sentinel_omega.infrastructure.database.schema import get_connection

ROOT = Path(__file__).resolve().parents[2]


def _load_generar():
    spec = importlib.util.spec_from_file_location(
        "generar_reporte", ROOT / "deploy" / "generar_reporte.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_live_only_agents_appear_without_firmas(tmp_path):
    db = str(tmp_path / "test.db")
    conn = get_connection(db)
    # A backcast bot with firmas so the "Memoria entrenada" section renders.
    conn.execute(
        "INSERT INTO TBL_FIRMAS (bot_name, event_class, id_nodo, features_json, "
        "recurrencia, estado) VALUES ('beta1','sismo_M5',1,'{}',3,'consolidada')"
    )
    # alfa2 accumulates live in tbl_cobertura_satelital (no firmas yet).
    for zona in ("guerrero_gap", "oaxaca_costa"):
        conn.execute(
            "INSERT INTO tbl_cobertura_satelital "
            "(timestamp_blk, zona, coverage_score, thermal_anomalies, clear_passes, "
            "total_passes, revisit_days) VALUES ('2026-07-16 01:00:00', ?, 0.3, 0, 0, 0, 0.0)",
            (zona,),
        )
    conn.commit()
    conn.close()

    out = str(tmp_path / "REPORTE.md")
    gr = _load_generar()
    gr.generar(db, out)
    text = Path(out).read_text()

    # Live-only agent must be visible even though it has no firmas.
    assert "| alfa2 |" in text, "alfa2 missing from report"
    # alfa2 shows its live state; with 0 satellite passes it flags the missing feed.
    assert "sin feed satelital" in text
    # jupiter retired 2026-10-18 — must NOT appear in live agent list.
    assert "| jupiter |" not in text, "jupiter should not appear (retired)"
