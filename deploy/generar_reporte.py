#!/usr/bin/env python3
"""
Genera estado/REPORTE.md desde la base de datos — los "ojos" del sistema.

Lo usa el vigilante de GitHub Actions después de cada ciclo, y se puede
correr a mano. Sin argumentos usa la DB por defecto.

El reporte está escrito para que cualquier persona lo entienda sin haber
visto el sistema antes: cada sección lleva una explicación en lenguaje
llano y barras visuales donde ayuda.
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
}


def _barra(pct: float, ancho: int = 10) -> str:
    """Barra visual ▓▓▓░░ para porcentajes en Markdown."""
    if pct is None:
        return ""
    llenos = round(max(0.0, min(1.0, pct)) * ancho)
    return "▓" * llenos + "░" * (ancho - llenos)


def generar(db_path: str = DB_DEFAULT, out_path: str = OUT_DEFAULT) -> str:
    conn = sqlite3.connect(db_path)
    ahora = datetime.now(timezone.utc)
    lineas = [
        "# 🌍 Sentinel Omega — Estado del Sistema",
        "",
        f"**Generado:** {ahora.strftime('%Y-%m-%d %H:%M')} UTC "
        f"({(ahora.hour - 6) % 24:02d}:{ahora.minute:02d} UTC-6)",
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
        # Escala visual del fantasma: CRITICAL arranca en 30
        fant_pct = min(1.0, ciclo[3] / 60.0)
        lineas += [
            "## 📡 Último ciclo — lo que el sistema midió hace un momento",
            "",
            "> El **Fantasma** es el termómetro principal: combina en un solo "
            "número la agitación del campo magnético, el viento solar y la "
            "resonancia de la Tierra. Verde 🟢 <5 = calma · Amarillo 🟡 5-15 · "
            "Naranja 🟠 15-30 · Rojo 🔴 ≥30 = condiciones muy cargadas. "
            "El **Muro de los 5** son cinco frentes de vigilancia "
            "(tierra, atmósfera, océano, sol, mercados); si 3 o más se activan "
            "a la vez, distintos dominios físicos están alterados al mismo "
            "tiempo — eso casi nunca es coincidencia.",
            "",
            f"| Métrica | Valor | Lectura |",
            f"|---|---|---|",
            f"| Fantasma | {emoji} **{ciclo[3]:.1f}** `{_barra(fant_pct)}` | "
            f"{ {'LOW': 'calma', 'MODERATE': 'actividad moderada', 'HIGH': 'actividad alta', 'CRITICAL': 'condiciones muy cargadas'}.get(ciclo[4], ciclo[4]) } |",
            f"| Consenso de los 6 bots | {ciclo[1].upper()} ({ciclo[2]:.0%}) | "
            f"{'los bots coinciden en que hay señal' if ciclo[1].upper() == 'ALERT' else 'sin acuerdo suficiente para alertar' if ciclo[1].upper() in ('WATCH', 'NORMAL') else 'evaluando'} |",
            f"| Muro de los 5 frentes | {ciclo[7]}/5 activos | "
            f"{'🚨 **BREACH** — varios dominios alterados a la vez' if ciclo[8] else 'estable — sin convergencia crítica'} |",
            f"| Precursores detectados | {ciclo[5]} | {ciclo[6] or '—'} |",
            f"| Hora de la medición | {ts.strftime('%Y-%m-%d %H:%M')} UTC | |",
            "",
        ]

    # ── Detecciones recientes ──
    dets = conn.execute(
        "SELECT tipo, display_name, confidence, station FROM TBL_DETECCIONES "
        "ORDER BY id DESC LIMIT 8"
    ).fetchall()
    if dets:
        lineas += [
            "## 🔭 Detecciones recientes — las señales individuales",
            "",
            "> Cada fila es una señal concreta que el escáner encontró en los "
            "datos: una perturbación magnética, un enjambre sísmico, un pico "
            "de gas volcánico… La **confianza** dice qué tan clara fue la "
            "señal (no la probabilidad de un evento). Una detección aislada "
            "es normal; varias juntas de tipos distintos es lo que sube el "
            "riesgo.",
            "",
            "| Precursor | Confianza | Zona |",
            "|---|---|---|",
        ]
        for d in dets:
            lineas.append(
                f"| {d[1]} | {d[2]:.0%} `{_barra(d[2], 5)}` | {d[3] or '—'} |"
            )
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
                "## 🎯 Firma Match — la memoria reconoce el momento actual",
                "",
                "> Esta es la parte más importante del reporte. Durante el "
                "entrenamiento, el sistema estudió los **14 días previos** a "
                "cada sismo fuerte de los últimos 32 años y guardó el 'rostro' "
                "de esas vísperas como una **firma**. Aquí compara el estado "
                "actual del planeta contra esa memoria. Un match del 84% "
                "significa: *lo que estamos viendo hoy se parece en un 84% a "
                "cómo se veían los días previos a ese tipo de evento*. "
                "**Veces vista** = cuántas veces esa misma firma precedió a un "
                "evento real en el histórico — a más repeticiones, más "
                "confiable el parecido.",
                "",
                "| Parecido | Precedió a | Zona (nodo de la malla) | Veces vista | Suele avisar con |",
                "|---|---|---|---|---|",
            ]
            nodos = {
                r[0]: (r[1], r[2], r[3], r[4])
                for r in conn.execute(
                    "SELECT node_id, nombre, lat, lon, region "
                    "FROM TBL_NODOS_TOPOLOGIA"
                ).fetchall()
            }
            for m in fm[:5]:
                # Lag propio de la firma si ya lo tiene medido; si no, el
                # típico de su clase de evento (ventana_tipica_dias).
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
                if nodo:
                    lugar = (
                        f"**{nodo[0]}** ({nodo[1]:.1f}, {nodo[2]:.1f}) "
                        f"· nodo {m['id_nodo']}"
                    )
                else:
                    lugar = f"nodo {m['id_nodo']}"
                lineas.append(
                    f"| **{m['similitud']:.0%}** `{_barra(m['similitud'], 5)}` | "
                    f"{m['event_class']} | {lugar} | "
                    f"{m['recurrencia']:,} | {lag_txt} |"
                )
            lineas += [
                "",
                "*SISMO_M5 / M6 / M7 = sismo de magnitud 5+, 6+ o 7+. La zona "
                "es el punto de la malla global UVG-125 donde se aprendió la "
                "firma (nombre y coordenadas lat, lon); los nodos 'Ghost' son "
                "puntos teóricos de la malla sin estación física encima.*",
                "",
            ]

    # ── Lag de anticipación por tipo de evento ──
    try:
        lags = conn.execute(
            "SELECT event_class, lag_promedio_h, lag_max_h, lag_min_h, "
            "n_eventos FROM tbl_lag_anticipacion ORDER BY event_class"
        ).fetchall()
        if lags:
            lineas += [
                "## ⏱ Anticipación — con cuánto tiempo suele avisar",
                "",
                "> Medido sobre el histórico: ¿cuántos días **antes** del "
                "evento ya era reconocible su firma? No es un cronómetro "
                "exacto — es el promedio de lo que ha pasado. El hallazgo "
                "contraintuitivo: **los eventos más grandes avisan con más "
                "tiempo**. Un M7 se 'carga' durante más días que un M5.",
                "",
                "| Evento | Aviso promedio | Máximo | Mínimo | Casos medidos |",
                "|---|---|---|---|---|",
            ]
            for l in lags:
                lineas.append(
                    f"| {l[0]} | **{l[1]/24:.1f} días** | {l[2]/24:.1f} d | "
                    f"{l[3]/24:.1f} d | {l[4]} |"
                )
            lineas += [
                "",
                "*Medición in-sample sobre 32 años de histórico; la ventana "
                "de estudio llega a 14 días, así que los máximos pueden estar "
                "recortados.*",
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
                "## 🔍 ¿Qué acelera o retrasa un evento?",
                "",
                "> Comparamos las firmas que avisaron con **poco** tiempo "
                "(rápidas) contra las que avisaron con **mucho** (lentas). "
                "El patrón que salió: cuando hay tormenta geomagnética, el "
                "evento llega pronto — *la tormenta precipita*. Cuando el "
                "espacio está en calma, la corteza se carga despacio y avisa "
                "con más días — *la calma carga*.",
                "",
                "| Variable | En firmas rápidas | En firmas lentas | Qué indica |",
                "|---|---|---|---|",
            ]
            for f in fact:
                nombre = NOMBRES_LLANOS.get(f[0], f[0])
                sesgo = (
                    "más presente cuando el aviso es LARGO"
                    if f[3] > 0
                    else "más presente cuando el evento llega PRONTO"
                )
                lineas.append(
                    f"| {nombre} | {f[1]:.2f} | {f[2]:.2f} | {sesgo} |"
                )
            lineas += [
                "",
                "*Rápidas = tercio de firmas con menor anticipación; lentas = "
                "tercio con mayor.*",
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
        lineas += [
            "## 🧠 Memoria entrenada — lo que el sistema ya aprendió",
            "",
            "> El sistema son **6 bots especializados**: `alfa1` vigila el "
            "clima espacial (30 años), `beta1` la resonancia Schumann — el "
            "latido electromagnético de la Tierra (30 años), `alfa2` los "
            "satélites Sentinel (14 años), `beta2` la desgasificación "
            "volcánica y la atmósfera (14 años), `delta` el humor de los "
            "mercados (10 años), y `padre` arbitra entre todos. Cada uno "
            "guarda sus propias **firmas** (patrones de vísperas de evento). "
            "El **peso** es su credibilidad ante el padre: 1.00 = normal; "
            "baja cuando falla y se recupera cuando acierta; puede superar "
            "1.00 solo si detectó algo que el padre dejó pasar.",
            "",
            "| Bot | Firmas aprendidas | Veces confirmadas | Credibilidad |",
            "|---|---|---|---|",
        ]
        for f in firmas:
            p = pesos.get(f[0], 1.0)
            lineas.append(
                f"| {f[0]} | {f[1]:,} | {f[2]:,} | {p:.2f} `{_barra(p / 1.5, 6)}` |"
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
            "## 🎯 Asertividad — ¿qué tan bien le ha ido?",
            "",
            "> Tres formas de medir lo mismo. **Histórica**: al repasar los "
            "32 años de datos como examen, ¿reconoció las vísperas de los "
            "eventos que ya sabemos que ocurrieron? **Viva**: desde que opera "
            "en tiempo real, cada aviso queda registrado y un auditor "
            "independiente (el Juez) lo califica 72 horas después contra los "
            "sismos que realmente ocurrieron — sin trampa posible. "
            "**7 días**: lo mismo, pero solo la última semana. La viva "
            "empieza en '—' hasta que las primeras ventanas de 72h se "
            "cierran.",
            "",
            "| Métrica | Valor |",
            "|---|---|",
            f"| **Histórica** (examen sobre 32 años) | {_pct(ha, hf)} |",
            f"| **Viva** (operación real, auditada) | {_viva_pct(viva)} |",
            f"| **Últimos 7 días** (viva) | {_viva_pct(viva7)} |",
            "",
            "### Por bot",
            "",
            "| Bot | Histórica | Viva | Viva 7d | Credibilidad |",
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
            "*La histórica mide reconocimiento de patrones dentro de los "
            "mismos datos con que se entrenó (por eso es tan alta). La viva "
            "es la prueba honesta: predicciones a futuro calificadas contra "
            "la realidad.*",
            "",
        ]
    except sqlite3.OperationalError:
        pass

    # ── Sesgo de aprendizaje: realidad vs fantasía ──
    try:
        sesgo = conn.execute(
            "SELECT bot, recon_insample, recon_causal, sesgo FROM "
            "tbl_sesgo_aprendizaje ORDER BY sesgo DESC"
        ).fetchall()
        if sesgo:
            lineas += [
                "## 🪞 Realidad vs fantasía — el sesgo de aprendizaje",
                "",
                "> La asertividad histórica alta es *in-sample*: el bot reconoce "
                "las firmas con las que se entrenó (comodidad). La columna "
                "**Causal (real)** mide lo honesto: ¿reconoció el evento con la "
                "memoria que ya tenía **antes** de que ocurriera? El **sesgo** "
                "es la diferencia — cuánto de esa competencia era fantasía. "
                "Aunque el número real sea más bajo, es la verdad.",
                "",
                "| Bot | In-sample | **Causal (real)** | Sesgo (fantasía) |",
                "|---|---|---|---|",
            ]
            for b in sesgo:
                flag = " ⚠️" if b[3] > 0.20 else (" ✅" if b[3] < 0.05 else "")
                lineas.append(
                    f"| {b[0]} | {b[1]:.1%} | **{b[2]:.1%}** | "
                    f"{b[3]:+.1%}{flag} |"
                )
            lineas += [
                "",
                "*Sesgo < 5% = el bot generaliza de verdad. Sesgo alto = su "
                "competencia era comodidad in-sample; su decisión real es más "
                "floja de lo que aparentaba.*",
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
        traduccion = {
            "ACIERTO": "ACIERTO — avisó y el evento ocurrió",
            "FALLO": "FALLO — el evento ocurrió sin aviso (lo más castigado)",
            "FALSO_POSITIVO": "FALSO POSITIVO — avisó y no pasó nada",
        }
        lineas += [
            "## ⚖️ El Juez — auditoría independiente",
            "",
            "> El Juez es un auditor que **nunca predice**: solo registra "
            "cada aviso de los bots y, cuando se cierra la ventana de 72 "
            "horas, lo compara contra el catálogo sísmico real (USGS) y "
            "dicta sentencia. Dejar pasar un evento castiga 10 veces más "
            "que una falsa alarma — preferimos un sistema nervioso a uno "
            "dormido.",
            "",
        ]
        for r in juez:
            lineas.append(f"- {traduccion.get(r[0], r[0])}: {r[1]:,}")
        lineas.append(
            f"- PENDIENTES (avisos cuya ventana de 72h sigue abierta): "
            f"{pendientes:,}"
        )
        lineas.append("")

    total_ciclos = conn.execute("SELECT COUNT(*) FROM TBL_CICLOS").fetchone()[0]
    lineas += [
        "---",
        "*Todos los datos provienen de fuentes públicas oficiales (NOAA, "
        "USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección "
        "civil: es investigación de precursores en curso.*",
        "",
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
