#!/usr/bin/env python3
"""
Genera estado/REPORTE.md desde la base de datos — los "ojos" del sistema.

Lo usa el vigilante de GitHub Actions después de cada ciclo, y se puede
correr a mano. Sin argumentos usa la DB por defecto.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_DEFAULT = str(
    Path(__file__).parent.parent / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
)
OUT_DEFAULT = str(Path(__file__).parent.parent / "estado" / "REPORTE.md")


def generar(db_path: str = DB_DEFAULT, out_path: str = OUT_DEFAULT) -> str:
    conn = sqlite3.connect(db_path)
    ahora = datetime.now(timezone.utc)
    lineas = [
        "# 🌍 Sentinel Omega — Estado del Sistema",
        "",
        f"**Generado:** {ahora.strftime('%Y-%m-%d %H:%M')} UTC "
        f"({(ahora.hour - 6) % 24:02d}:{ahora.minute:02d} UTC-6)",
        "",
    ]

    # ── Último ciclo ──
    ciclo = conn.execute(
        "SELECT timestamp, geo_signal, geo_confidence, fantasma, nivel_riesgo, "
        "precursors_count, precursor_types, muro_walls_active, muro_breach "
        "FROM TBL_CICLOS ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if ciclo:
        ts = datetime.fromtimestamp(ciclo[0], tz=timezone.utc)
        emoji = {"LOW": "🟢", "MODERATE": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(
            ciclo[4], "⚪"
        )
        lineas += [
            "## Último ciclo",
            "",
            f"| Métrica | Valor |",
            f"|---|---|",
            f"| Fantasma | {emoji} **{ciclo[3]:.1f}** ({ciclo[4]}) |",
            f"| Señal / consenso | {ciclo[1].upper()} ({ciclo[2]:.0%}) |",
            f"| Muro de los 5 | {'🚨 BREACH' if ciclo[8] else 'estable'} — "
            f"{ciclo[7]}/5 muros |",
            f"| Precursores activos | {ciclo[5]}: {ciclo[6]} |",
            f"| Hora del ciclo | {ts.strftime('%Y-%m-%d %H:%M')} UTC |",
            "",
        ]

    # ── Detecciones recientes ──
    dets = conn.execute(
        "SELECT tipo, display_name, confidence, station FROM TBL_DETECCIONES "
        "ORDER BY id DESC LIMIT 8"
    ).fetchall()
    if dets:
        lineas += ["## Detecciones recientes", "", "| Precursor | Confianza | Zona |", "|---|---|---|"]
        for d in dets:
            lineas.append(f"| {d[1]} | {d[2]:.0%} | {d[3] or '—'} |")
        lineas.append("")

    # ── Firma matches (memoria de 30 años) ──
    matches = conn.execute(
        "SELECT detalles_json, timestamp FROM TBL_JUEZ_AUDITORIA "
        "WHERE bot_name = 'padre' AND detalles_json LIKE '%firma_matches%' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if matches:
        det = json.loads(matches[0])
        fm = det.get("firma_matches", [])
        if fm:
            lineas += [
                "## 🎯 Firma Match — la memoria reconoce el estado actual",
                "",
                "| Similitud | Precedió a | Nodo | Veces vista |",
                "|---|---|---|---|",
            ]
            for m in fm[:5]:
                lineas.append(
                    f"| **{m['similitud']:.0%}** | {m['event_class']} | "
                    f"{m['id_nodo']} | {m['recurrencia']:,} |"
                )
            lineas.append("")

    # ── Lag de anticipación por tipo de evento ──
    try:
        lags = conn.execute(
            "SELECT event_class, lag_promedio_h, lag_max_h, lag_min_h, "
            "n_eventos FROM tbl_lag_anticipacion ORDER BY event_class"
        ).fetchall()
        if lags:
            lineas += [
                "## ⏱ Anticipación — con cuánto tiempo avisa la firma",
                "",
                "| Evento | Lag promedio | Máximo | Mínimo | Eventos medidos |",
                "|---|---|---|---|---|",
            ]
            for l in lags:
                lineas.append(
                    f"| {l[0]} | **{l[1]/24:.1f} días** | {l[2]/24:.1f} d | "
                    f"{l[3]/24:.1f} d | {l[4]} |"
                )
            lineas += [
                "",
                "*Lag = desde cuándo (antes del evento) la firma ya era "
                "reconocible en el histórico (in-sample).*",
                "",
            ]
    except sqlite3.OperationalError:
        pass

    # ── Factores: qué distingue firmas lentas de rápidas ──
    try:
        fact = conn.execute(
            "SELECT feature, media_rapidas, media_lentas, diferencia_norm "
            "FROM tbl_factores_lag ORDER BY ABS(diferencia_norm) DESC LIMIT 6"
        ).fetchall()
        if fact:
            lineas += [
                "## 🔍 Factores del lag — qué comparten las que avisan antes",
                "",
                "| Variable | Firmas rápidas | Firmas lentas | Sesgo |",
                "|---|---|---|---|",
            ]
            for f in fact:
                sesgo = "⬆ más en LENTAS" if f[3] > 0 else "⬆ más en RÁPIDAS"
                lineas.append(
                    f"| {f[0]} | {f[1]:.2f} | {f[2]:.2f} | {sesgo} ({f[3]:+.2f}) |"
                )
            lineas += [
                "",
                "*Rápidas = tercil con menor anticipación; lentas = tercil "
                "con mayor. El sesgo revela qué condiciones alargan o "
                "acortan la preparación del evento.*",
                "",
            ]
    except sqlite3.OperationalError:
        pass

    # ── Memoria y disciplina ──
    firmas = conn.execute(
        "SELECT bot_name, COUNT(*), SUM(recurrencia) FROM TBL_FIRMAS "
        "GROUP BY bot_name ORDER BY bot_name"
    ).fetchall()
    pesos = {
        r[0]: r[1]
        for r in conn.execute("SELECT bot_name, peso FROM TBL_PESOS_BOTS").fetchall()
    }
    if firmas:
        lineas += ["## Memoria entrenada (30 años)", "", "| Bot | Firmas | Recurrencias | Peso |", "|---|---|---|---|"]
        for f in firmas:
            lineas.append(
                f"| {f[0]} | {f[1]:,} | {f[2]:,} | {pesos.get(f[0], 1.0):.2f} |"
            )
        lineas.append("")

    # ── Asertividad: global, histórica, individual y a 7 días ──
    try:
        # Histórica (backtest 30 años): contadores acumulados por bot
        hist = {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                "SELECT bot_name, aciertos, fallos FROM TBL_PESOS_BOTS"
            ).fetchall()
        }
        # Viva (operación): predicciones resueltas del Juez, sin backtest
        viva_q = (
            "SELECT bot_name, resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA "
            "WHERE resultado != 'PENDIENTE' "
            "AND detalles_json NOT LIKE '%\"fase\": \"backtest\"%' {extra} "
            "GROUP BY bot_name, resultado"
        )

        def _tabla(rows):
            t = {}
            for bot, res, n in rows:
                d = t.setdefault(
                    bot, {"ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0}
                )
                d[res] = n
            return t

        viva = _tabla(conn.execute(viva_q.format(extra="")).fetchall())
        hace7d = ahora.timestamp() - 7 * 86400
        viva7 = _tabla(
            conn.execute(
                viva_q.format(extra="AND timestamp >= ?"), (hace7d,)
            ).fetchall()
        )

        def _pct(a, f, fp=0):
            total = a + f + fp
            return f"{a/total:.1%}" if total else "—"

        def _viva_pct(t, bot=None):
            if bot is not None:
                d = t.get(bot)
                if not d:
                    return "—"
                return _pct(d["ACIERTO"], d["FALLO"], d["FALSO_POSITIVO"])
            a = sum(d["ACIERTO"] for d in t.values())
            f = sum(d["FALLO"] for d in t.values())
            fp = sum(d["FALSO_POSITIVO"] for d in t.values())
            return _pct(a, f, fp)

        ha = sum(v[0] for v in hist.values())
        hf = sum(v[1] for v in hist.values())

        lineas += [
            "## 🎯 Asertividad",
            "",
            "| Métrica | Valor |",
            "|---|---|",
            f"| **Global histórica** (backtest 30 años) | {_pct(ha, hf)} |",
            f"| **Global viva** (operación resuelta) | {_viva_pct(viva)} |",
            f"| **Últimos 7 días** (viva) | {_viva_pct(viva7)} |",
            "",
            "### Individual por bot",
            "",
            "| Bot | Histórica (30a) | Viva | Viva 7d | Peso |",
            "|---|---|---|---|---|",
        ]
        pesos_tbl = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT bot_name, peso FROM TBL_PESOS_BOTS"
            ).fetchall()
        }
        for bot in sorted(set(hist) | set(viva) | set(pesos_tbl)):
            h = hist.get(bot)
            lineas.append(
                f"| {bot} | {_pct(h[0], h[1]) if h else '—'} | "
                f"{_viva_pct(viva, bot)} | {_viva_pct(viva7, bot)} | "
                f"{pesos_tbl.get(bot, 1.0):.2f} |"
            )
        lineas += [
            "",
            "*Histórica = reconocimiento de firmas consolidadas en el "
            "backtest. Viva = predicciones en operación calificadas por el "
            "Juez al cerrar su ventana de 72h.*",
            "",
        ]
    except sqlite3.OperationalError:
        pass

    # ── Auditoría del Juez ──
    juez = conn.execute(
        "SELECT resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE resultado != 'PENDIENTE' GROUP BY resultado"
    ).fetchall()
    pendientes = conn.execute(
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA WHERE resultado = 'PENDIENTE'"
    ).fetchone()[0]
    if juez or pendientes:
        lineas += ["## Juez (auditoría)", ""]
        for r in juez:
            lineas.append(f"- {r[0]}: {r[1]:,}")
        lineas.append(f"- PENDIENTES (ventana abierta): {pendientes:,}")
        lineas.append("")

    total_ciclos = conn.execute("SELECT COUNT(*) FROM TBL_CICLOS").fetchone()[0]
    lineas += [
        "---",
        f"*Ciclos totales: {total_ciclos:,} · Sentinel Omega · Fractal Core Research*",
    ]

    conn.close()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    contenido = "\n".join(lineas) + "\n"
    out.write_text(contenido, encoding="utf-8")

    # Versionado: cada corte queda guardado en estado/historial/AAAA/MM/
    # con fecha y hora local (UTC-6) en el nombre. El operador va vaciando
    # carpetas viejas cuando quiera; REPORTE.md siempre es el último.
    from datetime import timedelta
    local = ahora - timedelta(hours=6)
    version_dir = out.parent / "historial" / local.strftime("%Y") / local.strftime("%m")
    version_dir.mkdir(parents=True, exist_ok=True)
    version_file = version_dir / f"{local.strftime('%Y-%m-%d_%H-%M')}_MX.md"
    version_file.write_text(contenido, encoding="utf-8")

    print(f"Reporte generado: {out}")
    print(f"Versión guardada: {version_file}")
    return contenido


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_DEFAULT
    out = sys.argv[2] if len(sys.argv) > 2 else OUT_DEFAULT
    generar(db, out)
