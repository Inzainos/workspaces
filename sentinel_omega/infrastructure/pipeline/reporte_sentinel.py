"""
Sentinel Omega — Generador de Reportes
=======================================
Dos reportes independientes tras el entrenamiento:

  1. reporte_general(db_path)  → resumen global de todos los bots,
     firmas, juez, lags, patrones y estado del sistema.

  2. reporte_padre(db_path)    → análisis profundo solo del Padre:
     correlaciones cruzadas, patrones de patrones, comparativa de
     sus predicciones vs realidad, factores de lag, correlaciones
     por dominio.

Ambos se generan en texto enriquecido (compatible con terminal y logs)
y devuelven también un dict estructurado para consumo programático.

Uso:
    from sentinel_omega.infrastructure.pipeline.reporte_sentinel import (
        reporte_general, reporte_padre,
    )
    reporte_general(db_path)
    reporte_padre(db_path)
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de formato
# ──────────────────────────────────────────────────────────────────────────────

WIDTH = 72


def _sep(char="─", n=WIDTH):
    return char * n


def _title(text, char="═"):
    pad = max(0, WIDTH - len(text) - 4)
    left = pad // 2
    right = pad - left
    return f"{char * (left + 2)}  {text}  {char * (right + 2)}"


def _section(text):
    return f"\n{'▌'} {text.upper()}\n{_sep('╌')}"


def _bar(value: float, max_val: float, width: int = 30, fill="█", empty="░") -> str:
    if max_val <= 0:
        return empty * width
    filled = int(round(value / max_val * width))
    filled = max(0, min(filled, width))
    return fill * filled + empty * (width - filled)


def _pct_bar(pct: float, width: int = 20) -> str:
    """0–1 float → barra de porcentaje con etiqueta."""
    return f"{_bar(pct, 1.0, width)} {pct * 100:5.1f}%"


def _tabla(headers: List[str], rows: List[List[Any]], col_min: int = 10) -> str:
    widths = [max(col_min, len(str(h))) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    sep = "┼".join("─" * (w + 2) for w in widths)
    sep = f"├{sep}┤"
    header_row = "│".join(f" {str(h):<{w}} " for h, w in zip(headers, widths))
    header_row = f"│{header_row}│"
    top = "┬".join("─" * (w + 2) for w in widths)
    top = f"┌{top}┐"
    bottom = "┴".join("─" * (w + 2) for w in widths)
    bottom = f"└{bottom}┘"
    data_rows = []
    for row in rows:
        cells = []
        for i, w in enumerate(widths):
            cell = str(row[i]) if i < len(row) else ""
            cells.append(f" {cell:<{w}} ")
        data_rows.append(f"│{'│'.join(cells)}│")
    lines = [top, header_row, sep]
    lines.extend(data_rows)
    lines.append(bottom)
    return "\n".join(lines)


def _sparkline(values: List[float], width: int = 20) -> str:
    """Mini gráfica de línea usando bloques unicode."""
    blocks = " ▁▂▃▄▅▆▇█"
    if not values:
        return "─" * width
    mn, mx = min(values), max(values)
    rng = mx - mn or 1e-9
    sampled = values
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    return "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in sampled)


def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def _safe_query(conn, query, params=()):
    try:
        return conn.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        return []


# ──────────────────────────────────────────────────────────────────────────────
# REPORTE GENERAL
# ──────────────────────────────────────────────────────────────────────────────

def reporte_general(db_path: str) -> Dict:
    """
    Reporte global del sistema Sentinel Omega post-entrenamiento.
    Imprime en stdout y devuelve el dict con todos los datos.
    """
    conn = _conn(db_path)
    lines = []
    data = {}

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(_title(f"SENTINEL OMEGA — REPORTE GENERAL  [{now_str}]"))
    lines.append("")

    # ── 1. Estado de la Base de Datos ────────────────────────────────────────
    lines.append(_section("1. Estado de la Base de Datos"))

    db_size_mb = Path(db_path).stat().st_size / 1_048_576 if Path(db_path).exists() else 0
    table_counts = {}
    for tbl in [
        "TBL_FIRMAS", "TBL_CICLOS", "TBL_DETECCIONES", "TBL_JUEZ_AUDITORIA",
        "TBL_PESOS_BOTS", "tbl_historico_sismico_raw", "tbl_correlaciones_padre",
        "tbl_lag_anticipacion", "tbl_sesgo_aprendizaje",
    ]:
        row = _safe_query(conn, f"SELECT COUNT(*) FROM {tbl}")
        table_counts[tbl] = row[0][0] if row else "N/A"

    lines.append(f"  Ruta:      {db_path}")
    lines.append(f"  Tamaño:    {db_size_mb:.1f} MB")
    lines.append("")

    tbl_headers = ["Tabla", "Registros"]
    tbl_rows = [[t, str(c)] for t, c in table_counts.items()]
    lines.append(_tabla(tbl_headers, tbl_rows))
    data["db"] = {"size_mb": db_size_mb, "tables": table_counts}

    # ── 2. Firmas por Bot y Estado ───────────────────────────────────────────
    lines.append(_section("2. Firmas por Bot y Estado"))

    firma_rows = _safe_query(
        conn,
        "SELECT bot_name, estado, COUNT(*) as n "
        "FROM TBL_FIRMAS GROUP BY bot_name, estado ORDER BY bot_name, estado"
    )
    # Pivot
    bots_order = ["alfa1", "alfa2", "beta1", "beta2", "delta", "padre"]
    estados_order = ["nueva", "observada", "recurrente", "consolidada"]
    pivot: Dict[str, Dict[str, int]] = {b: {e: 0 for e in estados_order} for b in bots_order}
    for row in firma_rows:
        b, e, n = row["bot_name"], row["estado"], row["n"]
        if b in pivot and e in pivot[b]:
            pivot[b][e] = n

    headers = ["Bot", "Nueva", "Observada", "Recurrente", "Consolidada", "Total", "Barra"]
    trows = []
    for b in bots_order:
        d = pivot[b]
        total = sum(d.values())
        cons = d["consolidada"]
        bar = _bar(cons, max(1, total), width=20)
        trows.append([b, d["nueva"], d["observada"], d["recurrente"], cons, total, bar])
    lines.append(_tabla(headers, trows))

    # Totales globales
    total_firmas = _safe_query(conn, "SELECT COUNT(*) FROM TBL_FIRMAS")
    total_cons = _safe_query(conn, "SELECT COUNT(*) FROM TBL_FIRMAS WHERE estado='consolidada'")
    n_total = total_firmas[0][0] if total_firmas else 0
    n_cons = total_cons[0][0] if total_cons else 0
    lines.append(f"\n  Total firmas: {n_total}  |  Consolidadas: {n_cons}  "
                 f"({n_cons/max(1,n_total)*100:.1f}%)")
    data["firmas"] = {"total": n_total, "consolidadas": n_cons, "por_bot": dict(pivot)}

    # ── 3. Pesos Disciplinarios ──────────────────────────────────────────────
    lines.append(_section("3. Pesos Disciplinarios (credibilidad)"))

    pesos_rows = _safe_query(
        conn,
        "SELECT bot_name, peso FROM TBL_PESOS_BOTS ORDER BY peso DESC"
    )
    if not pesos_rows:
        lines.append("  Sin pesos en TBL_PESOS_BOTS aún.")
    else:
        p_headers = ["Bot", "Peso", "Barra de credibilidad"]
        p_rows = []
        max_peso = max(r["peso"] for r in pesos_rows) or 1.0
        for r in pesos_rows:
            bar = _bar(r["peso"], max_peso, width=30)
            p_rows.append([r["bot_name"], f"{r['peso']:.4f}", bar])
        lines.append(_tabla(p_headers, p_rows))
    data["pesos"] = {r["bot_name"]: r["peso"] for r in pesos_rows}

    # ── 4. Auditoría del Juez ────────────────────────────────────────────────
    lines.append(_section("4. Auditoría del Juez — Asertividad por Bot"))

    juez_rows = _safe_query(
        conn,
        "SELECT bot_name, resultado, COUNT(*) as n, COALESCE(SUM(severidad),0) as sev "
        "FROM TBL_JUEZ_AUDITORIA WHERE resultado != 'PENDIENTE' "
        "GROUP BY bot_name, resultado ORDER BY bot_name, resultado"
    )
    juez_pivot: Dict[str, Dict] = {}
    for r in juez_rows:
        b = r["bot_name"]
        if b not in juez_pivot:
            juez_pivot[b] = {"ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0, "sev": 0.0}
        juez_pivot[b][r["resultado"]] = r["n"]
        juez_pivot[b]["sev"] += r["sev"]

    j_headers = ["Bot", "Aciertos", "Fallos", "FP", "Asertividad", "Severidad", "Barra"]
    j_rows = []
    for b in bots_order:
        d = juez_pivot.get(b, {"ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0, "sev": 0.0})
        total = d["ACIERTO"] + d["FALLO"] + d["FALSO_POSITIVO"]
        asert = d["ACIERTO"] / max(1, total)
        bar = _pct_bar(asert, width=20)
        j_rows.append([
            b, d["ACIERTO"], d["FALLO"], d["FALSO_POSITIVO"],
            f"{asert*100:.1f}%", f"{d['sev']:.1f}", bar
        ])
    lines.append(_tabla(j_headers, j_rows))
    data["juez"] = juez_pivot

    # ── 5. Sesgo de Aprendizaje (Realidad vs Fantasía) ───────────────────────
    lines.append(_section("5. Sesgo de Aprendizaje — In-Sample vs Causal"))

    sesgo_rows = _safe_query(
        conn,
        "SELECT bot, n, recon_insample, recon_causal, sesgo, castigos "
        "FROM tbl_sesgo_aprendizaje ORDER BY sesgo DESC"
    )
    if not sesgo_rows:
        lines.append("  Sin datos de sesgo. Ejecutar barrido_diario().")
    else:
        lines.append(
            "  In-sample = el bot reconoce con lo que se entrenó (favorecido).\n"
            "  Causal    = solo reconoce con memoria anterior al evento (honesto).\n"
            "  Sesgo alto → el bot 'recuerda el futuro'; necesita más training.\n"
        )
        s_headers = ["Bot", "N", "In-Sample", "Causal", "Sesgo", "Castigos", "Calidad"]
        s_rows = []
        for r in sesgo_rows:
            calidad = "✓ SANO" if r["sesgo"] < 0.15 else ("⚠ SOBREFIT" if r["sesgo"] < 0.4 else "✗ CRÍTICO")
            s_rows.append([
                r["bot"], r["n"],
                f"{r['recon_insample']*100:.1f}%",
                f"{r['recon_causal']*100:.1f}%",
                f"{r['sesgo']*100:.1f}%",
                r["castigos"], calidad
            ])
        lines.append(_tabla(s_headers, s_rows))
    data["sesgo"] = [dict(r) for r in sesgo_rows]

    # ── 6. Lags de Anticipación ──────────────────────────────────────────────
    lines.append(_section("6. Lags de Anticipación por Clase de Evento"))

    lag_rows = _safe_query(
        conn,
        "SELECT event_class, lag_promedio_h, lag_max_h, lag_min_h, n_eventos "
        "FROM tbl_lag_anticipacion ORDER BY lag_promedio_h DESC"
    )
    if not lag_rows:
        lines.append("  Sin lags calculados. Ejecutar calcular_lags_anticipacion().")
    else:
        lines.append(
            "  Tiempo de ANTICIPACIÓN real antes del evento (in-sample, Padre).\n"
            "  Un lag mayor = el sistema detecta la firma más temprano.\n"
        )
        l_headers = ["Clase", "Prom (días)", "Máx (días)", "Mín (días)", "N evts", "Barra"]
        l_rows = []
        max_lag = max(r["lag_promedio_h"] for r in lag_rows) or 1
        for r in lag_rows:
            prom_d = r["lag_promedio_h"] / 24
            max_d = r["lag_max_h"] / 24
            min_d = r["lag_min_h"] / 24
            bar = _bar(r["lag_promedio_h"], max_lag, width=20)
            l_rows.append([
                r["event_class"],
                f"{prom_d:.1f}", f"{max_d:.1f}", f"{min_d:.1f}",
                r["n_eventos"], bar
            ])
        lines.append(_tabla(l_headers, l_rows))
    data["lags"] = [dict(r) for r in lag_rows]

    # ── 7. Top Patrones Cruzados del Padre ───────────────────────────────────
    lines.append(_section("7. Top Patrones Cruzados — Padre"))

    corr_rows = _safe_query(
        conn,
        "SELECT patron, event_class, n, fuerza "
        "FROM tbl_correlaciones_padre ORDER BY fuerza DESC LIMIT 20"
    )
    if not corr_rows:
        lines.append("  Sin correlaciones del Padre. Ejecutar construir_correlaciones_padre().")
    else:
        lines.append(
            "  Patrón cruzado = qué dominios estaban activos simultáneamente\n"
            "  antes del evento. Fuerza = proporción del total observado.\n"
        )
        c_headers = ["Patrón dominante", "Clase evento", "N visto", "Fuerza", "Barra"]
        c_rows = []
        max_f = max(r["fuerza"] for r in corr_rows) or 1
        for r in corr_rows:
            bar = _bar(r["fuerza"], max_f, width=18)
            c_rows.append([r["patron"], r["event_class"], r["n"], f"{r['fuerza']:.4f}", bar])
        lines.append(_tabla(c_headers, c_rows))
    data["correlaciones_padre"] = [dict(r) for r in corr_rows]

    # ── 8. Últimas 10 Alertas Despachadas ────────────────────────────────────
    lines.append(_section("8. Últimas Alertas del Sistema"))

    alert_rows = _safe_query(
        conn,
        "SELECT timestamp, bot_name, prediccion, confianza, detalles_json "
        "FROM TBL_JUEZ_AUDITORIA "
        "WHERE prediccion IN ('alert','watch') "
        "ORDER BY timestamp DESC LIMIT 10"
    )
    if not alert_rows:
        lines.append("  Sin alertas recientes en el ledger.")
    else:
        a_headers = ["Timestamp", "Bot", "Señal", "Conf", "Detalle"]
        a_rows = []
        for r in alert_rows:
            ts = datetime.utcfromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
            det = r["detalles_json"]
            try:
                d = json.loads(det)
                detalle = d.get("clase", d.get("nivel", ""))
            except Exception:
                detalle = ""
            a_rows.append([ts, r["bot_name"], r["prediccion"],
                           f"{r['confianza']:.0%}", detalle])
        lines.append(_tabla(a_headers, a_rows))
    data["ultimas_alertas"] = [dict(r) for r in alert_rows]

    # ── 9. Resumen Ejecutivo ──────────────────────────────────────────────────
    lines.append(_section("9. Resumen Ejecutivo"))

    total_eventos = _safe_query(
        conn, "SELECT COUNT(*) FROM tbl_historico_sismico_raw WHERE sismo_max_mag >= 4.5"
    )
    n_ev = total_eventos[0][0] if total_eventos else 0

    mejor_bot = max(juez_pivot.items(),
                    key=lambda x: x[1]["ACIERTO"] / max(1, x[1]["ACIERTO"] + x[1]["FALLO"]),
                    default=(None, {}))

    lines.append(f"  ▸ Eventos M4.5+ en catálogo:   {n_ev}")
    lines.append(f"  ▸ Total firmas registradas:    {n_total}")
    lines.append(f"  ▸ Firmas consolidadas:         {n_cons}  ({n_cons/max(1,n_total)*100:.1f}%)")
    if pesos_rows:
        top_peso = pesos_rows[0]
        lines.append(f"  ▸ Bot más confiable (peso):    {top_peso['bot_name']}  ({top_peso['peso']:.4f})")
    if mejor_bot[0]:
        b, d = mejor_bot
        asert = d["ACIERTO"] / max(1, d["ACIERTO"] + d["FALLO"])
        lines.append(f"  ▸ Mayor asertividad:           {b}  ({asert*100:.1f}%)")
    if lag_rows:
        mejor_lag = lag_rows[0]
        lines.append(f"  ▸ Evento con más anticipación: {mejor_lag['event_class']}  "
                     f"({mejor_lag['lag_promedio_h']/24:.1f} días prom)")
    lines.append("")
    lines.append(_sep("═"))
    lines.append("")

    conn.close()
    output = "\n".join(lines)
    print(output)
    logger.info(f"Reporte general generado — {n_total} firmas, {n_cons} consolidadas.")
    return data


# ──────────────────────────────────────────────────────────────────────────────
# REPORTE DEL PADRE
# ──────────────────────────────────────────────────────────────────────────────

def reporte_padre(db_path: str) -> Dict:
    """
    Reporte profundo SOLO del Padre: patrones de patrones, correlaciones
    cruzadas, factores de lag, sesgo, historial de predicciones y ranking
    de firmas más fuertes.
    """
    conn = _conn(db_path)
    lines = []
    data = {}

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(_title(f"SENTINEL OMEGA — PADRE  [{now_str}]", char="▓"))
    lines.append("  El Padre correlaciona TODOS los dominios simultáneamente.")
    lines.append("  Patrón de patrones: síntesis multi-bot → veredicto final.")
    lines.append("")

    # ── P1. Firmas del Padre por Clase y Estado ──────────────────────────────
    lines.append(_section("P1. Firmas del Padre — Inventario"))

    padre_firmas = _safe_query(
        conn,
        "SELECT event_class, estado, COUNT(*) as n, AVG(recurrencia) as rec_prom "
        "FROM TBL_FIRMAS WHERE bot_name = 'padre' "
        "GROUP BY event_class, estado ORDER BY event_class, estado"
    )

    pivot2: Dict[str, Dict] = {}
    for r in padre_firmas:
        cl = r["event_class"]
        if cl not in pivot2:
            pivot2[cl] = {"nueva": 0, "observada": 0, "recurrente": 0, "consolidada": 0}
        pivot2[cl][r["estado"]] = r["n"]

    p1_headers = ["Clase", "Nueva", "Observada", "Recurrente", "Consolidada", "Total"]
    p1_rows = []
    for cl, d in sorted(pivot2.items()):
        total = sum(d.values())
        p1_rows.append([cl, d["nueva"], d["observada"], d["recurrente"], d["consolidada"], total])
    lines.append(_tabla(p1_headers, p1_rows))

    total_padre = sum(sum(d.values()) for d in pivot2.values())
    cons_padre = sum(d["consolidada"] for d in pivot2.values())
    lines.append(f"\n  Total firmas Padre: {total_padre}  |  Consolidadas: {cons_padre}")
    data["firmas_padre"] = pivot2

    # ── P2. Correlaciones Cruzadas (Patrones de Patrones) ────────────────────
    lines.append(_section("P2. Correlaciones Cruzadas — Patrones de Patrones"))

    corr_rows = _safe_query(
        conn,
        "SELECT patron, event_class, n, fuerza "
        "FROM tbl_correlaciones_padre ORDER BY n DESC LIMIT 30"
    )

    if not corr_rows:
        lines.append("  Sin correlaciones aún. Correr construir_correlaciones_padre().")
    else:
        lines.append(
            "  Cada fila = un patrón cruzado (qué dominios estaban activos juntos)\n"
            "  que el Padre vio ANTES de un tipo de evento.\n"
            "  SOLAR+SISMICO = tormenta solar coincidente con actividad sísmica.\n"
            "  CALMA         = periodo de calma solar que precede el evento.\n"
            "  DIFUSO        = sin patrón dominante claro.\n"
        )

        # Agrupar por patrón para mostrar cuántos tipos de evento activa
        patron_resumen: Dict[str, Dict] = {}
        for r in corr_rows:
            p = r["patron"]
            if p not in patron_resumen:
                patron_resumen[p] = {"clases": [], "total_n": 0, "max_fuerza": 0}
            patron_resumen[p]["clases"].append(r["event_class"])
            patron_resumen[p]["total_n"] += r["n"]
            patron_resumen[p]["max_fuerza"] = max(patron_resumen[p]["max_fuerza"], r["fuerza"])

        p2_headers = ["Patrón activo", "Tipos evento", "Total N", "Max fuerza", "Barra"]
        p2_rows = []
        max_n = max(v["total_n"] for v in patron_resumen.values()) or 1
        for pat, v in sorted(patron_resumen.items(), key=lambda x: -x[1]["total_n"]):
            clases_str = ", ".join(sorted(set(v["clases"]))[:3])
            if len(v["clases"]) > 3:
                clases_str += f" +{len(v['clases'])-3}"
            bar = _bar(v["total_n"], max_n, width=18)
            p2_rows.append([pat, clases_str, v["total_n"], f"{v['max_fuerza']:.4f}", bar])
        lines.append(_tabla(p2_headers, p2_rows))

        # Detalle completo por patrón → clase
        lines.append("\n  Detalle por patrón → clase de evento:")
        c_headers = ["Patrón", "Clase evento", "N observado", "Fuerza", "Barra"]
        c_rows = []
        max_f = max(r["fuerza"] for r in corr_rows) or 1
        for r in corr_rows:
            bar = _bar(r["fuerza"], max_f, width=16)
            c_rows.append([r["patron"], r["event_class"], r["n"], f"{r['fuerza']:.4f}", bar])
        lines.append(_tabla(c_headers, c_rows))
    data["correlaciones"] = [dict(r) for r in corr_rows]

    # ── P3. Top Firmas Consolidadas del Padre (por recurrencia) ──────────────
    lines.append(_section("P3. Top Firmas Consolidadas — Mayor Recurrencia"))

    top_firmas = _safe_query(
        conn,
        "SELECT firma_id, event_class, recurrencia, lag_promedio_h, "
        "primera_vista, ultima_vista "
        "FROM TBL_FIRMAS WHERE bot_name='padre' AND estado='consolidada' "
        "ORDER BY recurrencia DESC LIMIT 15"
    )
    if not top_firmas:
        lines.append("  Sin firmas consolidadas del Padre aún.")
    else:
        tf_headers = ["ID", "Clase", "Recurrencias", "Lag prom (d)", "Primera vista", "Última vista"]
        tf_rows = []
        for r in top_firmas:
            lag_d = f"{r['lag_promedio_h']/24:.1f}" if r["lag_promedio_h"] else "—"
            tf_rows.append([
                r["firma_id"], r["event_class"], r["recurrencia"],
                lag_d, str(r["primera_vista"])[:10], str(r["ultima_vista"])[:10]
            ])
        lines.append(_tabla(tf_headers, tf_rows))
    data["top_firmas"] = [dict(r) for r in top_firmas]

    # ── P4. Lags de Anticipación del Padre ───────────────────────────────────
    lines.append(_section("P4. Ventana de Anticipación — Tiempo de Aviso"))

    lag_rows = _safe_query(
        conn,
        "SELECT event_class, lag_promedio_h, lag_max_h, lag_min_h, n_eventos "
        "FROM tbl_lag_anticipacion ORDER BY lag_promedio_h DESC"
    )
    if not lag_rows:
        lines.append("  Sin lags calculados.")
    else:
        lines.append(
            "  ¿Con cuántos días de anticipación detectó el Padre la firma?\n"
            "  Escala: 336h = 14 días (máximo de la ventana de firma).\n"
        )
        max_lag = max(r["lag_promedio_h"] for r in lag_rows) or 1
        for r in lag_rows:
            prom_d = r["lag_promedio_h"] / 24
            max_d = r["lag_max_h"] / 24
            min_d = r["lag_min_h"] / 24
            bar = _bar(r["lag_promedio_h"], max_lag, width=25)
            lines.append(
                f"  {r['event_class']:<18} {bar}  "
                f"{prom_d:.1f}d prom  [{min_d:.1f}d – {max_d:.1f}d]  N={r['n_eventos']}"
            )
    data["lags_padre"] = [dict(r) for r in lag_rows]

    # ── P5. Factores que Aceleran o Retrasan la Firma ────────────────────────
    lines.append(_section("P5. Factores de Lag — Qué Acelera la Detección"))

    factor_rows = _safe_query(
        conn,
        "SELECT feature, media_rapidas, media_lentas, diferencia_norm "
        "FROM tbl_factores_lag ORDER BY ABS(diferencia_norm) DESC LIMIT 12"
    )
    if not factor_rows:
        lines.append("  Sin análisis de factores. Ejecutar analizar_factores_lag().")
    else:
        lines.append(
            "  dif > 0 → el feature es más alto en firmas que avisan TARDE\n"
            "           (ese valor 'oscurece' la señal).\n"
            "  dif < 0 → el feature es más alto cuando la firma llega TEMPRANO\n"
            "           (ese valor 'acelera' el reconocimiento).\n"
        )
        f_headers = ["Feature", "Media rápidas", "Media lentas", "Dif norm", "Efecto"]
        f_rows = []
        for r in factor_rows:
            efecto = ("⬆ retrasa" if r["diferencia_norm"] > 0 else "⬇ acelera")
            f_rows.append([
                r["feature"],
                f"{r['media_rapidas']:.3f}",
                f"{r['media_lentas']:.3f}",
                f"{r['diferencia_norm']:+.3f}",
                efecto,
            ])
        lines.append(_tabla(f_headers, f_rows))
    data["factores_lag"] = [dict(r) for r in factor_rows]

    # ── P6. Sesgo del Padre (Realidad vs Fantasía) ───────────────────────────
    lines.append(_section("P6. Sesgo del Padre — Causalidad Real"))

    sesgo = _safe_query(
        conn,
        "SELECT n, recon_insample, recon_causal, sesgo, castigos "
        "FROM tbl_sesgo_aprendizaje WHERE bot = 'padre'"
    )
    if not sesgo:
        lines.append("  Sin datos de sesgo para el Padre.")
    else:
        r = sesgo[0]
        insample = r["recon_insample"]
        causal = r["recon_causal"]
        sesgo_v = r["sesgo"]
        lines.append(f"  Eventos evaluados:  {r['n']}")
        lines.append(f"  Reconocimiento in-sample:  {_pct_bar(insample, 30)}")
        lines.append(f"  Reconocimiento causal:     {_pct_bar(causal, 30)}")
        lines.append(f"  Sesgo (dif):               {sesgo_v*100:.1f}%")
        lines.append(f"  Castigos aplicados:        {r['castigos']}")
        if sesgo_v < 0.10:
            lines.append("  ✓ Padre SANO: reconoce eventos con memoria anterior a ellos.")
        elif sesgo_v < 0.30:
            lines.append("  ⚠ Padre con SESGO MODERADO: parte del reconocimiento es in-sample.")
        else:
            lines.append("  ✗ Padre con SESGO ALTO: reconocimiento principalmente in-sample.")
    data["sesgo_padre"] = dict(sesgo[0]) if sesgo else {}

    # ── P7. Correlación Feature × Clase (Heatmap ASCII) ─────────────────────
    lines.append(_section("P7. Heatmap: Feature × Clase de Evento (ratio vs global)"))

    heat_rows = _safe_query(
        conn,
        "SELECT event_class, feature, ratio FROM tbl_patrones_correlacion "
        "ORDER BY event_class, feature"
    )
    if not heat_rows:
        lines.append("  Sin datos de correlación. Ejecutar calcular_correlaciones_evento().")
    else:
        lines.append(
            "  ratio > 1.0 → el feature está ELEVADO antes de ese evento.\n"
            "  ratio < 1.0 → el feature está SUPRIMIDO.\n"
            "  ████ = muy elevado  ▒▒▒▒ = normal  ░░░░ = suprimido\n"
        )
        classes = sorted(set(r["event_class"] for r in heat_rows))
        features_heat = [
            "bz_mean", "kp_max", "schumann_mean", "sismo_count_win",
            "btc_volatilidad", "so2_kt_win", "fase_lunar", "proton_max"
        ]
        heat_data: Dict[str, Dict[str, float]] = {}
        for r in heat_rows:
            heat_data.setdefault(r["event_class"], {})[r["feature"]] = r["ratio"]

        def _heat_cell(ratio: Optional[float]) -> str:
            if ratio is None:
                return "  ·   "
            if ratio > 1.5:
                return " ████ "
            if ratio > 1.2:
                return " ▓▓▓▓ "
            if ratio > 1.0:
                return " ▒▒▒▒ "
            if ratio > 0.8:
                return " ░░░░ "
            return "  --  "

        cl_short = [c[:10] for c in classes[:8]]
        classes_display = classes[:8]
        header = f"  {'Feature':<24}" + "".join(f"{c:<8}" for c in cl_short)
        lines.append(header)
        lines.append("  " + _sep("─", WIDTH - 2))
        for feat in features_heat:
            row_str = f"  {feat:<24}"
            for cl in classes_display:
                ratio = heat_data.get(cl, {}).get(feat)
                row_str += _heat_cell(ratio)
            lines.append(row_str)
        lines.append("")
    data["heatmap"] = [dict(r) for r in heat_rows]

    # ── P8. Auditoría del Padre en el Juez ───────────────────────────────────
    lines.append(_section("P8. Historial del Juez — Solo Padre"))

    padre_juez = _safe_query(
        conn,
        "SELECT resultado, COUNT(*) as n, COALESCE(SUM(severidad),0) as sev "
        "FROM TBL_JUEZ_AUDITORIA WHERE bot_name='padre' AND resultado != 'PENDIENTE' "
        "GROUP BY resultado"
    )
    juez_dict = {r["resultado"]: {"n": r["n"], "sev": r["sev"]} for r in padre_juez}
    aciertos = juez_dict.get("ACIERTO", {}).get("n", 0)
    fallos = juez_dict.get("FALLO", {}).get("n", 0)
    fps = juez_dict.get("FALSO_POSITIVO", {}).get("n", 0)
    total_j = aciertos + fallos + fps
    asert = aciertos / max(1, total_j)
    sev_total = sum(v["sev"] for v in juez_dict.values())

    lines.append(f"  Aciertos:        {aciertos:>6}")
    lines.append(f"  Fallos:          {fallos:>6}   (severidad total: {sev_total:.1f})")
    lines.append(f"  Falsos positivos:{fps:>6}")
    lines.append(f"  Asertividad:     {_pct_bar(asert, 30)}")

    # Trend de aciertos recientes (últimos 200 registros)
    recientes = _safe_query(
        conn,
        "SELECT resultado FROM TBL_JUEZ_AUDITORIA "
        "WHERE bot_name='padre' AND resultado != 'PENDIENTE' "
        "ORDER BY timestamp DESC LIMIT 200"
    )
    if recientes:
        vals = [1.0 if r["resultado"] == "ACIERTO" else 0.0 for r in reversed(recientes)]
        window = 10
        smoothed = [sum(vals[max(0,i-window):i+1]) / len(vals[max(0,i-window):i+1])
                    for i in range(len(vals))]
        lines.append(f"\n  Tendencia aciertos (últimos {len(vals)} registros):")
        lines.append(f"  {_sparkline(smoothed, width=50)}")
        lines.append(f"  └── tendencia {'↑ MEJORANDO' if smoothed[-1] > smoothed[0] else '↓ AJUSTANDO'}")
    data["juez_padre"] = juez_dict

    # ── P9. Reincidencia y Peso del Padre ─────────────────────────────────────
    lines.append(_section("P9. Reincidencia y Credibilidad del Padre"))

    reincid = _safe_query(
        conn,
        "SELECT COUNT(*) as n FROM TBL_JUEZ_AUDITORIA "
        "WHERE bot_name='padre' AND resultado='FALLO'"
    )
    n_reincid = reincid[0]["n"] if reincid else 0
    pesos_padre = _safe_query(
        conn, "SELECT peso FROM TBL_PESOS_BOTS WHERE bot_name='padre'"
    )
    peso_padre = pesos_padre[0]["peso"] if pesos_padre else None

    lines.append(f"  Fallos históricos acumulados:  {n_reincid}")
    if peso_padre is not None:
        health = "✓ ÓPTIMO" if peso_padre > 0.7 else ("⚠ DEGRADADO" if peso_padre > 0.4 else "✗ CRÍTICO")
        lines.append(f"  Peso actual del Padre:         {peso_padre:.4f}")
        lines.append(f"  Barra de credibilidad:         {_pct_bar(peso_padre, 30)}")
        lines.append(f"  Estado:                        {health}")

    # ── Cierre ────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(_sep("▓"))
    lines.append("")

    conn.close()
    output = "\n".join(lines)
    print(output)
    logger.info("Reporte del Padre generado.")
    return data
