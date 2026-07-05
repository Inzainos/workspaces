#!/usr/bin/env python3
"""
Genera estado/REPORTE.md desde la base de datos — los "ojos" del sistema.

Lo usa el vigilante de GitHub Actions después de cada ciclo, y se puede
correr a mano. Sin argumentos usa la DB por defecto.

El reporte está escrito para que cualquier persona lo entienda sin haber
visto el sistema antes: cada sección lleva una explicación en lenguaje
llano, barras visuales, sparklines y gráficas ASCII donde ayuda.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_DEFAULT = str(
    Path(__file__).parent.parent / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
)
OUT_DEFAULT = str(Path(__file__).parent.parent / "estado" / "REPORTE.md")

# Traducción de variables técnicas a lenguaje llano (para la sección de factores)
NOMBRES_LLANOS = {
    "bz_min": "Campo magnético solar (Bz mínimo)",
    "bz_mean": "Campo magnético solar (Bz promedio)",
    "bz_mean_72h": "Campo magnético solar (Bz, últimas 72h)",
    "viento_max": "Velocidad máxima del viento solar",
    "viento_avg": "Velocidad promedio del viento solar",
    "kp_max": "Índice Kp máximo (tormenta geomagnética)",
    "kp_mean": "Índice Kp promedio",
    "kp_max_72h": "Tormenta geomagnética en las últimas 72h",
    "proton_max": "Lluvia de protones solares (máx)",
    "sismo_count_win": "Sismos en la ventana de 14 días",
    "sismo_count_72h": "Sismos en las últimas 72h",
    "sismo_max_mag_win": "Magnitud sísmica máxima en la ventana",
    "lod_mean": "Duración del día (rotación terrestre)",
    "fase_lunar": "Fase lunar",
    "dist_lunar": "Distancia a la Luna",
    "schumann_hz": "Resonancia Schumann (latido de la Tierra)",
    "schumann_wpc": "Perturbación Schumann",
    "btc_volatilidad": "Volatilidad de Bitcoin (nerviosismo del mercado)",
    "btc_vol_max": "Pico de volatilidad de Bitcoin",
    "btc_ret_win": "Rendimiento de Bitcoin en la ventana",
    "btc_vol_72h": "Volatilidad de Bitcoin (72h)",
    "so2_kt_win": "Gas volcánico SO₂ en la ventana (kilotones)",
    "erupciones_win": "Erupciones registradas en la ventana",
    "so2_kt_90d": "Gas volcánico SO₂ (90 días)",
    "erupciones_90d": "Erupciones (90 días)",
    "delta_cross_coupling": "Acoplamiento geofísico-financiero cruzado",
    "delta_geo_coupling": "Acoplamiento campo magnético-mercado",
    "delta_schumann_coupling": "Acoplamiento Schumann-mercado",
}

# ── Utilidades visuales ─────────────────────────────────────────────────────

def _barra(pct: float, ancho: int = 10) -> str:
    """Barra visual ▓▓▓░░ para porcentajes en Markdown."""
    if pct is None:
        return ""
    llenos = round(max(0.0, min(1.0, pct)) * ancho)
    return "▓" * llenos + "░" * (ancho - llenos)


# Bloques Unicode para sparklines (8 niveles)
_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: list, width: int = 20) -> str:
    """
    Genera una línea sparkline con los últimos `width` valores.
    Usa 8 caracteres de bloque Unicode para representar la magnitud relativa.
    """
    if not values:
        return "—"
    vals = [v for v in values if v is not None]
    if not vals:
        return "—"
    # Downsample o pad si hace falta
    if len(vals) > width:
        step = len(vals) / width
        vals = [vals[int(i * step)] for i in range(width)]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1.0
    chars = []
    for v in vals:
        idx = int((v - mn) / rng * 8)
        idx = max(0, min(8, idx))
        chars.append(_SPARK_CHARS[idx])
    return "".join(chars)


def _barra_horiz(value: float, max_val: float, width: int = 20, etiqueta: str = "") -> str:
    """Barra horizontal proporcional con etiqueta: █████░░░░░ 42.5"""
    if max_val <= 0:
        return f"{'░' * width} {value:.1f}"
    ratio = min(1.0, value / max_val)
    llenos = round(ratio * width)
    barra = "█" * llenos + "░" * (width - llenos)
    label = etiqueta if etiqueta else f"{value:.1f}"
    return f"`{barra}` {label}"


def _gauge_fantasma(val: float) -> str:
    """
    Dibuja un medidor ASCII del Fantasma en escala 0-60.
    Devuelve una cadena de varias líneas formateada para bloque de código.
    """
    escala = 60.0
    ratio = min(1.0, val / escala)
    width = 30
    llenos = round(ratio * width)
    if val < 5:
        color, nivel = "🟢", "CALMA"
    elif val < 15:
        color, nivel = "🟡", "MODERADO"
    elif val < 30:
        color, nivel = "🟠", "ALTO"
    else:
        color, nivel = "🔴", "CRÍTICO"
    barra = "█" * llenos + "░" * (width - llenos)
    puntero = " " * llenos + "▲"
    lineas = [
        f"  Fantasma  {color} {nivel}",
        f"  ┌{'─'*width}┐",
        f"  │{barra}│  {val:.1f} / 60",
        f"  └{'─'*width}┘",
        f"   {puntero}",
        f"   0{'':>{llenos-1}}{'':>{width-llenos}} 60",
    ]
    return "\n".join(lineas)


def _chart_barras_h(items: list[tuple], titulo: str = "", max_ancho: int = 25) -> list[str]:
    """
    Recibe lista de (etiqueta, valor_float) y devuelve líneas de Markdown
    con un mini gráfico de barras horizontales.
    """
    if not items:
        return []
    max_val = max(v for _, v in items if v is not None) or 1.0
    lineas = []
    if titulo:
        lineas.append(f"**{titulo}**")
        lineas.append("")
    lineas.append("```")
    for etiq, val in items:
        if val is None:
            val = 0.0
        llenos = round((val / max_val) * max_ancho)
        barra = "█" * llenos + "░" * (max_ancho - llenos)
        lineas.append(f"  {etiq:<28} {barra} {val:.1f}")
    lineas.append("```")
    return lineas


def _tabla_proporciones(items: list[tuple], total: int, titulo: str = "") -> list[str]:
    """
    Tabla Markdown con porcentaje visual para cada categoría.
    items = [(nombre, conteo), ...]
    """
    if not items:
        return []
    lineas = []
    if titulo:
        lineas += [f"### {titulo}", ""]
    lineas += [
        "| Categoría | Cantidad | Proporción | Visual |",
        "|---|---|---|---|",
    ]
    for nombre, n in items:
        pct = n / total if total else 0
        lineas.append(
            f"| {nombre} | {n:,} | {pct:.1%} | `{_barra(pct, 10)}` |"
        )
    return lineas


def generar(db_path: str = DB_DEFAULT, out_path: str = OUT_DEFAULT) -> str:
    conn = sqlite3.connect(db_path)
    ahora = datetime.now(timezone.utc)
    local_ahora = ahora - timedelta(hours=6)
    lineas = [
        "# 🌍 Sentinel Omega — Estado del Sistema",
        "",
        f"**Generado:** {ahora.strftime('%Y-%m-%d %H:%M')} UTC "
        f"· {local_ahora.strftime('%Y-%m-%d %H:%M')} hora MX (UTC-6)",
        "",
        "> **¿Qué es esto?** Sentinel Omega es un sistema que vigila señales "
        "físicas del planeta (campo magnético solar, resonancia de la Tierra, "
        "actividad sísmica, gases volcánicos, incluso el nerviosismo de los "
        "mercados) buscando *precursores*: condiciones que en 32 años de "
        "historia han aparecido **antes** de eventos naturales fuertes. "
        "No predice con certeza — reconoce parecidos con el pasado y avisa "
        "cuando el presente se parece demasiado a los días previos a un "
        "evento. Este reporte es una foto de lo que el sistema ve ahora.",
        "",
    ]

    # ══════════════════════════════════════════════════════════════════
    # §1 · MEDIDOR DE RIESGO — Fantasma + Muro + Consenso
    # ══════════════════════════════════════════════════════════════════
    ciclo = conn.execute(
        "SELECT timestamp, geo_signal, geo_confidence, fantasma, nivel_riesgo, "
        "precursors_count, precursor_types, muro_walls_active, muro_breach "
        "FROM TBL_CICLOS ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if ciclo:
        ts = datetime.fromtimestamp(ciclo[0], tz=timezone.utc)
        ts_mx = ts - timedelta(hours=6)
        nivel_map = {
            "LOW": ("🟢", "calma"),
            "MODERATE": ("🟡", "actividad moderada"),
            "HIGH": ("🟠", "actividad alta"),
            "CRITICAL": ("🔴", "condiciones muy cargadas"),
        }
        emoji, nivel_txt = nivel_map.get(ciclo[4], ("⚪", ciclo[4]))
        fant_val = ciclo[3]
        fant_pct = min(1.0, fant_val / 60.0)

        lineas += [
            "## 📡 §1 · Medidor de Riesgo — el termómetro del planeta",
            "",
            "> El **Fantasma** combina en un solo número toda la agitación "
            "del campo magnético solar, el viento solar y la resonancia "
            "electromagnética de la Tierra. **Verde 🟢 <5** = calma total · "
            "**Amarillo 🟡 5-15** = actividad moderada · **Naranja 🟠 15-30** "
            "= actividad elevada · **Rojo 🔴 ≥30** = condiciones muy cargadas. "
            "El **Muro de los 5** monitorea cinco dominios físicos (tierra, "
            "atmósfera, océano, espacio, mercados): cuando ≥3 se activan "
            "simultáneamente es porque dominios independientes están alterados "
            "a la vez — eso casi nunca es coincidencia.",
            "",
        ]

        # Medidor ASCII del Fantasma
        lineas += [
            "```",
            _gauge_fantasma(fant_val),
            "```",
            "",
        ]

        # Tabla de métricas del ciclo
        consensus_txt = {
            "ALERT": "🔴 los bots coinciden en que hay señal",
            "WATCH": "🟡 vigilancia elevada — posible señal emergente",
            "NORMAL": "🟢 sin acuerdo suficiente para alertar",
        }.get(ciclo[1].upper(), "⚪ evaluando")

        muro_txt = (
            "🚨 **BREACH** — múltiples dominios físicos alterados simultáneamente"
            if ciclo[8]
            else f"{'🟡' if ciclo[7] >= 2 else '🟢'} estable"
        )
        lineas += [
            "| Métrica | Valor | Lectura |",
            "|---|---|---|",
            f"| Fantasma | {emoji} **{fant_val:.1f}** `{_barra(fant_pct)}` | {nivel_txt} |",
            f"| Consenso de los 6 bots | {ciclo[1].upper()} ({ciclo[2]:.0%}) | {consensus_txt} |",
            f"| Muro de los 5 frentes | {ciclo[7]}/5 activos | {muro_txt} |",
            f"| Precursores detectados | **{ciclo[5]}** | {ciclo[6] or '—'} |",
            f"| Medido | {ts.strftime('%Y-%m-%d %H:%M')} UTC · {ts_mx.strftime('%H:%M')} MX | |",
            "",
        ]

    # ══════════════════════════════════════════════════════════════════
    # §2 · TENDENCIA RECIENTE — Sparkline de los últimos 24 ciclos
    # ══════════════════════════════════════════════════════════════════
    ciclos_recientes = conn.execute(
        "SELECT timestamp, fantasma, nivel_riesgo, muro_walls_active "
        "FROM TBL_CICLOS ORDER BY id DESC LIMIT 48"
    ).fetchall()
    if ciclos_recientes:
        ciclos_recientes = list(reversed(ciclos_recientes))
        vals_fant = [r[1] for r in ciclos_recientes]
        vals_muro = [r[3] for r in ciclos_recientes]

        # Estadísticas
        fant_prom = sum(vals_fant) / len(vals_fant)
        fant_max = max(vals_fant)
        fant_min = min(vals_fant)

        # Frecuencia de niveles de riesgo
        nivel_counts: dict = {}
        for r in ciclos_recientes:
            nivel_counts[r[2]] = nivel_counts.get(r[2], 0) + 1
        total_n = len(ciclos_recientes)

        lineas += [
            "## 📈 §2 · Tendencia reciente — últimos ciclos",
            "",
            "> Cada carácter del sparkline representa un ciclo del sistema "
            "(aproximadamente cada 3 horas). Un carácter más alto significa "
            "Fantasma más elevado. Sirve para ver de un vistazo si el sistema "
            "está subiendo, bajando o estable.",
            "",
            "**Fantasma — evolución (últimos ciclos, más reciente a la derecha)**",
            "",
            f"```",
            f"  {_sparkline(vals_fant, width=48)}",
            f"  ↑ mín {fant_min:.1f}  prom {fant_prom:.1f}  máx {fant_max:.1f}",
            f"```",
            "",
            "**Muro de los 5 — frentes activos por ciclo**",
            "",
            f"```",
            f"  {_sparkline(vals_muro, width=48)}",
            f"  ↑ 0 frentes → 5 frentes activos",
            f"```",
            "",
        ]

        # Distribución de niveles de riesgo
        orden_niveles = ["CRITICAL", "HIGH", "MODERATE", "LOW"]
        items_niveles = [
            (f"{'🔴' if n=='CRITICAL' else '🟠' if n=='HIGH' else '🟡' if n=='MODERATE' else '🟢'} {n}",
             nivel_counts.get(n, 0))
            for n in orden_niveles if n in nivel_counts
        ]
        if items_niveles:
            lineas += [
                "**Distribución de niveles de riesgo en los últimos ciclos**",
                "",
            ] + _tabla_proporciones(items_niveles, total_n) + [""]

    # ══════════════════════════════════════════════════════════════════
    # §3 · SEÑALES ACTIVAS — Detecciones recientes con desglose
    # ══════════════════════════════════════════════════════════════════
    dets = conn.execute(
        "SELECT tipo, display_name, confidence, station, timestamp "
        "FROM TBL_DETECCIONES ORDER BY id DESC LIMIT 20"
    ).fetchall()
    if dets:
        lineas += [
            "## 🔭 §3 · Señales activas — detecciones recientes",
            "",
            "> Cada fila es una señal concreta que el escáner encontró en los "
            "datos: perturbación magnética, enjambre sísmico, pico de gas "
            "volcánico, anomalía oceánica… La **confianza** indica qué tan "
            "clara fue la señal (no es la probabilidad de un evento). "
            "Una detección aislada es normal; varias de tipos distintos a la "
            "vez es lo que eleva el riesgo.",
            "",
        ]

        # Las 8 más recientes en tabla
        lineas += [
            "### Últimas 8 detecciones",
            "",
            "| Hora MX | Precursor | Confianza | Visual | Zona |",
            "|---|---|---|---|---|",
        ]
        for d in dets[:8]:
            ts_d = datetime.fromtimestamp(d[4], tz=timezone.utc) - timedelta(hours=6)
            lineas.append(
                f"| {ts_d.strftime('%d/%m %H:%M')} | {d[1]} "
                f"| {d[2]:.0%} | `{_barra(d[2], 5)}` | {d[3] or '—'} |"
            )
        lineas.append("")

        # Frecuencia por tipo de precursor
        tipo_counts: dict = {}
        for d in dets:
            tipo_counts[d[1]] = tipo_counts.get(d[1], 0) + 1
        items_tipo = sorted(tipo_counts.items(), key=lambda x: -x[1])
        total_d = len(dets)

        lineas += [
            "### Distribución por tipo (últimas 20 detecciones)",
            "",
        ] + _tabla_proporciones(items_tipo, total_d) + [""]

        # Mini gráfico de frecuencias
        chart_items = [(t, c) for t, c in items_tipo[:8]]
        lineas += _chart_barras_h(
            chart_items, "Frecuencia de detección por precursor", max_ancho=20
        ) + [""]

    # ══════════════════════════════════════════════════════════════════
    # §4 · FIRMA MATCH — la memoria reconoce el momento actual
    # ══════════════════════════════════════════════════════════════════
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
                "## 🎯 §4 · Firma Match — el planeta se parece al pasado",
                "",
                "> Esta es la parte más importante del reporte. Durante el "
                "entrenamiento el sistema estudió los **14 días previos** a cada "
                "evento fuerte de los últimos 32 años y guardó el 'rostro' de "
                "esas vísperas como una **firma**. Aquí compara el estado actual "
                "del planeta contra esa memoria. Un **92%** significa: *lo que "
                "vemos hoy se parece en un 92% a cómo lucían los días antes de "
                "ese tipo de evento*. **Veces vista** = cuántas veces esa misma "
                "firma precedió a un evento real — a más repeticiones, más "
                "confiable el patrón.",
                "",
                "| Parecido | Visual | Precedió a | Zona (malla UVG-125) | Veces vista | Aviso típico |",
                "|---|---|---|---|---|---|",
            ]
            nodos = {
                r[0]: (r[1], r[2], r[3], r[4])
                for r in conn.execute(
                    "SELECT node_id, nombre, lat, lon, region "
                    "FROM TBL_NODOS_TOPOLOGIA"
                ).fetchall()
            }
            for m in fm[:5]:
                lag_dias = None
                fid = m.get("firma_id")
                if fid is not None:
                    try:
                        r = conn.execute(
                            "SELECT lag_promedio_h, lag_n FROM TBL_FIRMAS "
                            "WHERE id = ?",
                            (fid,),
                        ).fetchone()
                        if r and r[0] and (r[1] or 0) > 0:
                            lag_dias = r[0] / 24
                    except sqlite3.OperationalError:
                        pass
                if lag_dias is None:
                    lag_dias = m.get("ventana_tipica_dias")
                if lag_dias is None:
                    try:
                        r = conn.execute(
                            "SELECT lag_promedio_h FROM tbl_lag_anticipacion "
                            "WHERE event_class = ?",
                            (m.get("event_class"),),
                        ).fetchone()
                        if r and r[0]:
                            lag_dias = r[0] / 24
                    except sqlite3.OperationalError:
                        pass
                lag_txt = f"~{lag_dias:.0f} días" if lag_dias else "—"
                nodo = nodos.get(m["id_nodo"])
                sim = m["similitud"]
                if nodo:
                    lugar = (
                        f"**{nodo[0]}** ({nodo[1]:.1f}, {nodo[2]:.1f}) "
                        f"· nodo {m['id_nodo']}"
                    )
                else:
                    lugar = f"nodo {m['id_nodo']}"
                lineas.append(
                    f"| **{sim:.0%}** | `{_barra(sim, 5)}` | "
                    f"{m['event_class']} | {lugar} | "
                    f"{m['recurrencia']:,} | {lag_txt} |"
                )
            lineas += [
                "",
                "**Similitud visual — top matches**",
                "",
            ]
            match_chart = [
                (f"{m['event_class']} nodo {m['id_nodo']}", m["similitud"] * 100)
                for m in fm[:5]
            ]
            lineas += _chart_barras_h(match_chart, max_ancho=20) + [
                "",
                "*SISMO_M5/M6/M7 = sismo de magnitud 5+/6+/7+. Los nodos 'Ghost' "
                "son puntos teóricos de la malla UVG-125 sin estación física.*",
                "",
            ]

    # ══════════════════════════════════════════════════════════════════
    # §5 · ANTICIPACIÓN — con cuánto tiempo suele avisar cada evento
    # ══════════════════════════════════════════════════════════════════
    try:
        lags = conn.execute(
            "SELECT event_class, lag_promedio_h, lag_max_h, lag_min_h, "
            "n_eventos FROM tbl_lag_anticipacion ORDER BY lag_promedio_h DESC"
        ).fetchall()
        if lags:
            lineas += [
                "## ⏱ §5 · Anticipación — cuántos días avisa antes del evento",
                "",
                "> Medido sobre el histórico: ¿cuántos días **antes** del evento "
                "ya era reconocible su firma? No es un cronómetro exacto — es el "
                "promedio histórico. El hallazgo contraintuitivo: **los eventos "
                "más grandes avisan con más tiempo**. Un M7 se 'carga' durante "
                "más días que un M5.",
                "",
                "| Evento | Aviso promedio | Máximo | Mínimo | Casos | Visual (max=14d) |",
                "|---|---|---|---|---|---|",
            ]
            for lg in lags:
                prom_d = lg[1] / 24
                lineas.append(
                    f"| {lg[0]} | **{prom_d:.1f} días** | {lg[2]/24:.1f} d "
                    f"| {lg[3]/24:.1f} d | {lg[4]:,} | "
                    f"`{_barra(prom_d / 14.0, 10)}` |"
                )
            lineas.append("")

            # Gráfico de barras horizontales de anticipación promedio
            chart_lags = [(lg[0], lg[1] / 24) for lg in lags]
            lineas += _chart_barras_h(
                chart_lags,
                "Días de anticipación promedio por tipo de evento",
                max_ancho=25,
            ) + [
                "",
                "*In-sample sobre 32 años; ventana máxima de estudio = 14 días.*",
                "",
            ]
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §6 · FACTORES — qué acelera o retrasa el evento
    # ══════════════════════════════════════════════════════════════════
    try:
        fact = conn.execute(
            "SELECT feature, media_rapidas, media_lentas, diferencia_norm "
            "FROM tbl_factores_lag ORDER BY ABS(diferencia_norm) DESC LIMIT 8"
        ).fetchall()
        if fact:
            lineas += [
                "## 🔍 §6 · Factores que precipitan o retrasan un evento",
                "",
                "> Comparamos firmas que avisaron con **poco** tiempo (rápidas) "
                "contra las que avisaron con **mucho** (lentas). Patrón "
                "encontrado: cuando hay tormenta geomagnética el evento llega "
                "pronto — *la tormenta precipita*. Cuando el espacio está en "
                "calma, la corteza se carga despacio — *la calma carga*.",
                "",
                "| Variable | Firmas rápidas | Firmas lentas | Diferencia | Rol |",
                "|---|---|---|---|---|",
            ]
            for f in fact:
                nombre = NOMBRES_LLANOS.get(f[0], f[0])
                dif_pct = abs(f[3])
                rol = (
                    "⚡ precipita (aviso corto)"
                    if f[3] < 0
                    else "🐢 retrasa (aviso largo)"
                )
                lineas.append(
                    f"| {nombre} | {f[1]:.2f} | {f[2]:.2f} | "
                    f"`{_barra(min(1.0, dif_pct), 5)}` {f[3]:+.2f} | {rol} |"
                )
            lineas += [
                "",
                "*Rápidas = tercio con menor anticipación · lentas = tercio con mayor.*",
                "",
            ]
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §7 · MEMORIA Y CREDIBILIDAD — bots y sus pesos
    # ══════════════════════════════════════════════════════════════════
    firmas = conn.execute(
        "SELECT bot_name, COUNT(*), SUM(recurrencia) FROM TBL_FIRMAS "
        "GROUP BY bot_name ORDER BY bot_name"
    ).fetchall()
    pesos = {
        r[0]: r[1]
        for r in conn.execute("SELECT bot_name, peso FROM TBL_PESOS_BOTS").fetchall()
    }
    if firmas:
        lineas += [
            "## 🧠 §7 · Memoria entrenada — lo que cada bot ya sabe",
            "",
            "> **6 bots especializados** vigilan dominios distintos: "
            "`alfa1` = clima espacial (30 años) · `beta1` = resonancia "
            "Schumann, el latido de la Tierra (30 años) · `alfa2` = satélites "
            "Sentinel ESA (14 años) · `beta2` = gases volcánicos y atmósfera "
            "(14 años) · `delta` = mercados financieros como señal de tensión "
            "(10 años) · `padre` = árbitro que combina a todos. "
            "La **credibilidad** (peso) parte en 1.00; baja cuando falla y "
            "sube cuando acierta. Puede superar 1.00 si detectó algo que el "
            "padre dejó pasar.",
            "",
            "| Bot | Dominio | Firmas aprendidas | Confirmaciones | Credibilidad | Visual |",
            "|---|---|---|---|---|---|",
        ]
        dominios = {
            "alfa1": "Clima espacial ☀️",
            "alfa2": "Satélites ESA 🛰️",
            "beta1": "Schumann / Tierra 🌐",
            "beta2": "Volcánico / Atmósfera 🌋",
            "delta": "Mercados 📈",
            "padre": "Árbitro consenso 🧩",
        }
        for f in firmas:
            p = pesos.get(f[0], 1.0)
            dom = dominios.get(f[0], f[0])
            lineas.append(
                f"| {f[0]} | {dom} | {f[1]:,} | {f[2]:,} | "
                f"**{p:.2f}** | `{_barra(p / 1.5, 8)}` |"
            )
        lineas.append("")

        # Gráfico de credibilidad
        cred_items = [(f[0], pesos.get(f[0], 1.0)) for f in firmas]
        lineas += _chart_barras_h(
            cred_items, "Credibilidad (peso) por bot — referencia: 1.00 = normal",
            max_ancho=20
        ) + [""]

    # ══════════════════════════════════════════════════════════════════
    # §8 · ASERTIVIDAD — qué tan bien ha acertado el sistema
    # ══════════════════════════════════════════════════════════════════
    try:
        hist = {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                "SELECT bot_name, aciertos, fallos FROM TBL_PESOS_BOTS"
            ).fetchall()
        }
        viva_q = (
            "SELECT bot_name, resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA "
            "WHERE resultado != 'PENDIENTE' "
            "AND detalles_json NOT LIKE '%\"fase\": \"backtest\"%' {extra} "
            "GROUP BY bot_name, resultado"
        )

        def _agrupar_veredictos(rows):
            t: dict = {}
            for bot, res, n in rows:
                d = t.setdefault(bot, {"ACIERTO": 0, "FALLO": 0, "FALSO_POSITIVO": 0})
                d[res] = n
            return t

        viva = _agrupar_veredictos(conn.execute(viva_q.format(extra="")).fetchall())
        hace7d = ahora.timestamp() - 7 * 86400
        viva7 = _agrupar_veredictos(
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
            "## 🎯 §8 · Asertividad — resultados del sistema",
            "",
            "> **Histórica** = examen sobre 32 años de datos ya conocidos "
            "(por eso es alta — es como aprobar un examen con el libro abierto). "
            "**Viva** = operación real: cada aviso se registra y el Juez lo "
            "califica 72 h después contra la realidad, sin trampa. "
            "**7 días** = solo la última semana. La viva comienza en '—' hasta "
            "que cierran las primeras ventanas de 72 h.",
            "",
            "| Métrica | Valor | Descripción |",
            "|---|---|---|",
            f"| **Histórica** | {_pct(ha, hf)} | Reconocimiento en los 32 años de entrenamiento |",
            f"| **Viva** | {_viva_pct(viva)} | Predicciones reales auditadas por el Juez |",
            f"| **Últimos 7 días** | {_viva_pct(viva7)} | Solo la semana en curso |",
            "",
        ]

        pesos_tbl = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT bot_name, peso FROM TBL_PESOS_BOTS"
            ).fetchall()
        }

        # Totales vivos por bot para tabla de proporciones
        lineas += ["### Por bot", ""]
        lineas += [
            "| Bot | Histórica | Viva | Viva 7d | Credibilidad |",
            "|---|---|---|---|---|",
        ]
        for bot in sorted(set(hist) | set(viva) | set(pesos_tbl)):
            h = hist.get(bot)
            lineas.append(
                f"| {bot} | {_pct(h[0], h[1]) if h else '—'} | "
                f"{_viva_pct(viva, bot)} | {_viva_pct(viva7, bot)} | "
                f"**{pesos_tbl.get(bot, 1.0):.2f}** |"
            )

        # Tabla de proporciones de resultados vivos globales
        res_global: dict = {}
        for d in viva.values():
            for k, v in d.items():
                res_global[k] = res_global.get(k, 0) + v
        total_res = sum(res_global.values())
        if total_res:
            etiq_map = {
                "ACIERTO": "✅ ACIERTO",
                "FALLO": "❌ FALLO",
                "FALSO_POSITIVO": "⚠️ FALSO POSITIVO",
            }
            items_res = [
                (etiq_map.get(k, k), v)
                for k, v in sorted(res_global.items(), key=lambda x: -x[1])
            ]
            lineas += ["", "**Distribución de resultados vivos globales**", ""]
            lineas += _tabla_proporciones(items_res, total_res)
        lineas += [
            "",
            "*La histórica mide reconocimiento in-sample (libro abierto). "
            "La viva es la prueba honesta: predicciones a futuro calificadas "
            "contra la realidad.*",
            "",
        ]
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §9 · SESGO DE APRENDIZAJE — realidad vs fantasía
    # ══════════════════════════════════════════════════════════════════
    try:
        sesgo = conn.execute(
            "SELECT bot, recon_insample, recon_causal, sesgo FROM "
            "tbl_sesgo_aprendizaje ORDER BY sesgo DESC"
        ).fetchall()
        if sesgo:
            lineas += [
                "## 🪞 §9 · Sesgo de aprendizaje — cuánto era ilusión",
                "",
                "> La asertividad histórica alta es *in-sample*: el bot reconoce "
                "las firmas con las que se entrenó. La columna "
                "**Causal (real)** es honesta: ¿reconoció el evento con la "
                "memoria que ya tenía **antes** de que ocurriera? El **sesgo** "
                "es la diferencia — cuánto de la competencia aparente era "
                "comodidad de libro abierto.",
                "",
                "| Bot | In-sample | **Causal (real)** | Sesgo | Diagnóstico |",
                "|---|---|---|---|---|",
            ]
            for b in sesgo:
                if b[3] > 0.20:
                    diag = "⚠️ sesgo alto — generaliza poco"
                elif b[3] < 0.05:
                    diag = "✅ sólido — generaliza bien"
                else:
                    diag = "🟡 sesgo moderado"
                lineas.append(
                    f"| {b[0]} | {b[1]:.1%} | **{b[2]:.1%}** | "
                    f"{b[3]:+.1%} | {diag} |"
                )
            lineas += [
                "",
                "*Sesgo < 5% = generaliza de verdad. Sesgo > 20% = "
                "su rendimiento real es mucho más bajo que el histórico.*",
                "",
            ]
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §10 · MAPA DE CORRELACIONES — qué precede a cada tipo de evento
    # ══════════════════════════════════════════════════════════════════
    try:
        corr_rows = conn.execute(
            "SELECT event_class, feature, ratio, n_firmas "
            "FROM tbl_patrones_correlacion ORDER BY event_class, feature"
        ).fetchall()
        if corr_rows:
            event_classes = sorted(set(r[0] for r in corr_rows))
            feat_dev: dict = {}
            for _, feat, ratio, _ in corr_rows:
                d = abs(ratio - 1.0)
                if d > feat_dev.get(feat, 0.0):
                    feat_dev[feat] = d
            top_feats = [
                f for f, _ in sorted(feat_dev.items(), key=lambda x: -x[1])[:8]
            ]
            lookup = {(r[0], r[1]): r[2] for r in corr_rows}

            def _celda(ratio):
                if ratio is None:
                    return "  —  "
                if ratio >= 2.0:
                    return f"🔴{ratio:.1f}×"
                if ratio >= 1.5:
                    return f"🟠{ratio:.1f}×"
                if ratio >= 1.2:
                    return f"🟡{ratio:.1f}×"
                if ratio >= 0.8:
                    return f"⬜{ratio:.1f}×"
                return f"🔵{ratio:.1f}×"

            lineas += [
                "## 🗺 §10 · Mapa de correlaciones — qué precede a cada evento",
                "",
                "> Mapa de calor: qué tan elevada está cada variable en los "
                "**14 días previos** a cada tipo de evento, comparado con "
                "su nivel habitual. **🔴≥2×** · **🟠≥1.5×** · **🟡≥1.2×** "
                "· ⬜~normal · **🔵** baja. Un 🔴 en SO₂ para ERUPCION_VEI4 "
                "significa que justo antes de esas erupciones el SO₂ estaba "
                "el doble de lo habitual. Un 🔵 en Kp para SISMO_M7 confirma "
                "el 'Silent Trigger': los grandes sismos a veces llegan en "
                "calma geomagnética.",
                "",
            ]
            short = {
                ec: ec.replace("SISMO_M", "M").replace("ERUPCION_", "🌋VEI")
                       .replace("TORMENTA_", "☀️Kp")
                for ec in event_classes
            }
            header = "| Variable |" + "".join(f" {short[ec]} |" for ec in event_classes)
            sep = "|---|" + "---|" * len(event_classes)
            lineas += [header, sep]
            for feat in top_feats:
                nombre = NOMBRES_LLANOS.get(feat, feat)[:38]
                row = f"| {nombre} |"
                for ec in event_classes:
                    row += f" {_celda(lookup.get((ec, feat)))} |"
                lineas.append(row)
            lineas.append("")
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §11 · TOP 10 PATRONES — los más vistos en 32 años
    # ══════════════════════════════════════════════════════════════════
    try:
        top_firmas = conn.execute(
            "SELECT firma_id, bot_name, event_class, id_nodo, recurrencia, "
            "estado, lag_promedio_h FROM TBL_FIRMAS "
            "WHERE estado IN ('consolidada','recurrente') "
            "ORDER BY recurrencia DESC LIMIT 10"
        ).fetchall()
        if top_firmas:
            nodos_top = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT node_id, nombre FROM TBL_NODOS_TOPOLOGIA"
                ).fetchall()
            }
            lineas += [
                "## 🏆 §11 · Top 10 patrones más consolidados",
                "",
                "> Las firmas que el sistema reconoció más veces en 32 años de "
                "historia. A mayor recurrencia, más confiable es ese patrón "
                "como precursor. Solo se muestran firmas **consolidadas** (≥3 "
                "eventos confirmados) o **recurrentes** (≥2).",
                "",
                "| # | Evento | Bot | Zona / Nodo | Veces | Estado | Aviso |",
                "|---|---|---|---|---|---|---|",
            ]
            estado_icon = {"consolidada": "✅", "recurrente": "🔁"}
            event_icon = {
                "SISMO": "🌎", "ERUPCION": "🌋", "TORMENTA": "☀️",
                "HURACAN": "🌀", "TSUNAMI": "🌊",
            }
            max_rec = top_firmas[0][4] if top_firmas else 1
            for i, (fid, bot, ec, nodo_id, rec, estado, lag_h) in enumerate(
                top_firmas, 1
            ):
                zona = (
                    nodos_top.get(nodo_id) or f"nodo {nodo_id}"
                ) if nodo_id else "global"
                lag_txt = f"~{lag_h/24:.0f}d" if lag_h else "—"
                eicon = next(
                    (v for k, v in event_icon.items() if ec.startswith(k)), "📍"
                )
                barra_rec = _barra(rec / max_rec, 5)
                lineas.append(
                    f"| {i} | {eicon} **{ec}** | {bot} | {zona} | "
                    f"{rec:,} `{barra_rec}` | {estado_icon.get(estado, '🆕')} | "
                    f"{lag_txt} |"
                )
            lineas.append("")
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §12 · PATRONES POR TIPO DE EVENTO — top 5 por clase
    # ══════════════════════════════════════════════════════════════════
    try:
        event_classes_all = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT event_class FROM TBL_FIRMAS ORDER BY event_class"
            ).fetchall()
        ]
        if event_classes_all:
            nodos_ev = {
                r[0]: (r[1], r[2], r[3])
                for r in conn.execute(
                    "SELECT node_id, nombre, lat, lon FROM TBL_NODOS_TOPOLOGIA"
                ).fetchall()
            }
            lineas += [
                "## 📊 §12 · Patrones por tipo de evento — top 5 por clase",
                "",
                "> Para cada tipo de evento que el sistema ha aprendido, las "
                "5 firmas más consolidadas. La **zona** es el nodo de la malla "
                "UVG-125 donde se aprendió la firma (nombre + coordenadas).",
                "",
            ]
            ev_icons = {
                "SISMO": "🌎", "ERUPCION": "🌋", "TORMENTA": "☀️",
                "HURACAN": "🌀", "TSUNAMI": "🌊",
            }
            estado_icon2 = {"consolidada": "✅", "recurrente": "🔁"}
            for ec in event_classes_all:
                firmas_ec = conn.execute(
                    "SELECT bot_name, id_nodo, recurrencia, estado, lag_promedio_h "
                    "FROM TBL_FIRMAS WHERE event_class = ? "
                    "ORDER BY recurrencia DESC LIMIT 5",
                    (ec,),
                ).fetchall()
                if not firmas_ec:
                    continue
                eicon = next(
                    (v for k, v in ev_icons.items() if ec.startswith(k)), "📍"
                )
                max_rec_ec = firmas_ec[0][2] if firmas_ec else 1
                lineas += [
                    f"### {eicon} {ec}",
                    "",
                    "| Bot | Zona (nodo de la malla) | Veces | Visual | Estado | Aviso típico |",
                    "|---|---|---|---|---|---|",
                ]
                for bot, nodo_id, rec, estado, lag_h in firmas_ec:
                    if nodo_id and nodo_id in nodos_ev:
                        n = nodos_ev[nodo_id]
                        zona = f"{n[0]} ({n[1]:.1f}, {n[2]:.1f})"
                    else:
                        zona = f"nodo {nodo_id}" if nodo_id else "global"
                    lag_txt = f"~{lag_h/24:.0f} días" if lag_h else "—"
                    lineas.append(
                        f"| {bot} | {zona} | {rec:,} | "
                        f"`{_barra(rec / max_rec_ec, 5)}` | "
                        f"{estado_icon2.get(estado, '🆕')} {estado} | "
                        f"{lag_txt} |"
                    )
                lineas.append("")
    except sqlite3.OperationalError:
        pass

    # ══════════════════════════════════════════════════════════════════
    # §13 · EL JUEZ — auditoría independiente
    # ══════════════════════════════════════════════════════════════════
    juez = conn.execute(
        "SELECT resultado, COUNT(*) FROM TBL_JUEZ_AUDITORIA "
        "WHERE resultado != 'PENDIENTE' GROUP BY resultado"
    ).fetchall()
    pendientes = conn.execute(
        "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA WHERE resultado = 'PENDIENTE'"
    ).fetchone()[0]
    if juez or pendientes:
        traduccion = {
            "ACIERTO": "✅ ACIERTO — avisó y el evento ocurrió",
            "FALLO": "❌ FALLO — el evento ocurrió sin aviso (más castigado ×10)",
            "FALSO_POSITIVO": "⚠️ FALSO POSITIVO — avisó y no pasó nada",
        }
        total_juez = sum(r[1] for r in juez) + pendientes
        lineas += [
            "## ⚖️ §13 · El Juez — auditoría independiente",
            "",
            "> El Juez **nunca predice**: solo registra cada aviso de los bots "
            "y, cuando se cierra la ventana de 72 horas, lo compara contra el "
            "catálogo sísmico real (USGS) y dicta sentencia. "
            "Dejar pasar un evento castiga **10 veces más** que una falsa "
            "alarma — el sistema prefiere ser nervioso a ser dormido.",
            "",
            "| Veredicto | Cantidad | Proporción | Visual |",
            "|---|---|---|---|",
        ]
        items_juez = [(traduccion.get(r[0], r[0]), r[1]) for r in juez]
        items_juez.append((f"⏳ PENDIENTES (ventana 72h abierta)", pendientes))
        total_juez_all = sum(n for _, n in items_juez)
        for nombre, n in items_juez:
            pct = n / total_juez_all if total_juez_all else 0
            lineas.append(
                f"| {nombre} | {n:,} | {pct:.1%} | `{_barra(pct, 10)}` |"
            )
        lineas.append("")

    # ══════════════════════════════════════════════════════════════════
    # CIERRE
    # ══════════════════════════════════════════════════════════════════
    total_ciclos = conn.execute("SELECT COUNT(*) FROM TBL_CICLOS").fetchone()[0]
    total_firmas_db = conn.execute("SELECT COUNT(*) FROM TBL_FIRMAS").fetchone()[0]
    total_dets_db = conn.execute("SELECT COUNT(*) FROM TBL_DETECCIONES").fetchone()[0]

    lineas += [
        "---",
        "",
        "### 📋 Resumen estadístico del sistema",
        "",
        "| Contador | Valor |",
        "|---|---|",
        f"| Ciclos completados | {total_ciclos:,} |",
        f"| Firmas en memoria | {total_firmas_db:,} |",
        f"| Detecciones acumuladas | {total_dets_db:,} |",
        "",
        "---",
        "",
        "*Todos los datos provienen de fuentes públicas oficiales (NOAA, "
        "USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección "
        "civil: es investigación de precursores en curso.*",
        "",
        f"*Sentinel Omega · Fractal Core Research · "
        f"Generado {local_ahora.strftime('%Y-%m-%d %H:%M')} hora MX*",
    ]

    conn.close()
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    contenido = "\n".join(lineas) + "\n"
    out.write_text(contenido, encoding="utf-8")

    # Versionado: cada corte queda en estado/historial/AAAA/MM/
    version_dir = (
        out.parent / "historial"
        / local_ahora.strftime("%Y")
        / local_ahora.strftime("%m")
    )
    version_dir.mkdir(parents=True, exist_ok=True)
    version_file = version_dir / f"{local_ahora.strftime('%Y-%m-%d_%H-%M')}_MX.md"
    version_file.write_text(contenido, encoding="utf-8")

    print(f"Reporte generado: {out}")
    print(f"Versión guardada: {version_file}")
    return contenido


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_DEFAULT
    out = sys.argv[2] if len(sys.argv) > 2 else OUT_DEFAULT
    generar(db, out)
