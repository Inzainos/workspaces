"""
Reportes periódicos de Sentinel Omega — comparativo diario, semanal y mensual.

Uso (lo agenda Roy Vigilante):
  python deploy/reporte_periodico.py --comparativo   # 12pm/12am MX: hoy vs ayer
  python deploy/reporte_periodico.py --semanal       # domingo 12:15 MX
  python deploy/reporte_periodico.py --mensual       # fin de mes 12:30 MX

Cada reporte:
  - Se escribe en estado/ (versionado por el vigilante).
  - Genera gráficas PNG (matplotlib, fail-soft si no está) en estado/graficas/.
  - Se envía por Telegram (vía Consenso Vigilante) con las gráficas adjuntas.
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from deploy.aciertos_reporte import obtener_estadisticas_aciertos
from sentinel_omega.core.precursor.baseline import (
    BLANCO_REPORTE_MAGNITUD,
    BLANCO_REPORTE_VENTANA_H,
    evaluar_veredictos,
)

DB_DEFAULT = str(RAIZ / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db")
DIR_ESTADO = RAIZ / "estado"
DIR_GRAFICAS = DIR_ESTADO / "graficas"

MX_UTC_OFFSET = -6  # CDMX, sin horario de verano desde 2022

# Paleta sobria (una sola familia de azules para magnitud, gris para contexto,
# rojo reservado a lo crítico — nunca arcoíris).
COLOR_SERIE = "#2563a8"
COLOR_CONTEXTO = "#9aa5b1"
COLOR_CRITICO = "#b3261e"


def _ahora_mx() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=MX_UTC_OFFSET)


def _dias_resumen(conn, n_dias: int):
    """Series diarias combinando tbl_resumen_diario (compactado) y TBL_CICLOS
    (días aún no barridos) — lo compactado no se pierde, se resume."""
    desde = (_ahora_mx() - timedelta(days=n_dias)).strftime("%Y-%m-%d")
    filas = {
        d: {"dia": d, "n_ciclos": n, "fantasma_media": fm, "fantasma_max": fx,
            "breaches": b, "alertas": a, "senal": s}
        for d, n, fx, fm, b, a, s in conn.execute(
            "SELECT dia, n_ciclos, fantasma_max, fantasma_media, breaches, "
            "alertas, senal_dominante FROM tbl_resumen_diario "
            "WHERE dia >= ? ORDER BY dia", (desde,))
    }
    for d, n, fm, fx, b, a in conn.execute(
        "SELECT date(timestamp, 'unixepoch'), COUNT(*), AVG(fantasma), "
        "MAX(fantasma), SUM(muro_breach), SUM(alerts_dispatched) "
        "FROM TBL_CICLOS WHERE date(timestamp,'unixepoch') >= ? "
        "GROUP BY 1 ORDER BY 1", (desde,)
    ):
        if d not in filas:
            filas[d] = {"dia": d, "n_ciclos": n, "fantasma_media": fm,
                        "fantasma_max": fx, "breaches": b or 0,
                        "alertas": a or 0, "senal": ""}
    return [filas[d] for d in sorted(filas)]


def _viva_en_rango(conn, desde_ts: float, hasta_ts: float):
    """Asertividad viva del rango, Y SU GANANCIA. Nunca una sin la otra.

    Dos cosas que faltaban (2026-10-08):

    1. **El filtro `en_vivo`.** `CLAUDE.md` lo dice como trampa de dato: la
       vista `viva_real` es solo `fase='viva'`, no filtra `en_vivo`, y arrastra
       los 603 veredictos duplicados del 27-sep. Hoy no cambia el numero ---
       medido: 324 filas, todas con `en_vivo=1` --- pero es el seguro para
       cuando vuelvan, y la regla pide el filtro en TODA metrica de
       asertividad.
    2. **La ganancia.** `CLAUDE.md`: «La asertividad nunca se muestra sola:
       cuenta como acierto cada silencio en calma y excluye los falsos
       positivos del denominador. Va siempre junto a `ganancia_real`
       (Molchan)». Este reporte la ponia SOLA en la «Lectura rapida», que es
       la primera linea que alguien lee.
    """
    filas = conn.execute(
        "SELECT verdad, resultado FROM viva_real "
        "WHERE resultado != 'PENDIENTE' AND COALESCE(en_vivo, 1) = 1 "
        "AND timestamp >= ? AND timestamp < ?", (desde_ts, hasta_ts)).fetchall()
    tot = len(filas)
    if not tot:
        return None, 0, None
    aciertos = sum(1 for _, r in filas if r == "ACIERTO")
    ganancia = muda = None
    con_evento = None
    try:
        m = evaluar_veredictos([(v or "", r or "") for v, r in filas])
        if m is not None:
            ganancia = m.ganancia
            muda = m.asertividad_muda
            con_evento = m.con_evento
    except Exception:  # noqa: BLE001 — el reporte sale igual, sin ganancia
        pass
    return aciertos / tot, tot, {"ganancia": ganancia, "muda": muda,
                                 "con_evento": con_evento}


def _grafica_serie(dias, campo, titulo, ylabel, nombre, resalta_max=False):
    """Gráfica de línea sobria: una serie, un color, grid tenue."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    if len(dias) < 2:
        return None
    xs = [d["dia"][5:] for d in dias]          # MM-DD
    ys = [d.get(campo) or 0 for d in dias]

    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=120)
    ax.plot(xs, ys, color=COLOR_SERIE, linewidth=2, marker="o",
            markersize=4, zorder=3)
    if resalta_max and ys:
        i = ys.index(max(ys))
        ax.plot(xs[i], ys[i], "o", color=COLOR_CRITICO, markersize=7,
                zorder=4)
        ax.annotate(f"{ys[i]:.1f}", (xs[i], ys[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8,
                    color=COLOR_CRITICO)
    ax.set_title(titulo, fontsize=11, loc="left")
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(axis="y", color=COLOR_CONTEXTO, alpha=0.25, linewidth=0.7)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(labelsize=8)
    if len(xs) > 14:
        ax.set_xticks(xs[:: max(1, len(xs) // 10)])
    fig.tight_layout()
    DIR_GRAFICAS.mkdir(parents=True, exist_ok=True)
    ruta = DIR_GRAFICAS / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def _delta_txt(hoy, ayer, fmt="{:+.1f}"):
    if hoy is None or ayer is None:
        return "—"
    d = hoy - ayer
    flecha = "▲" if d > 0 else ("▼" if d < 0 else "＝")
    return f"{flecha} {fmt.format(d)}"


def _barra(pct: float, ancho: int = 10) -> str:
    """Barra visual ▓▓▓░░ para porcentajes."""
    if pct is None:
        return ""
    llenos = round(max(0.0, min(1.0, pct)) * ancho)
    return "▓" * llenos + "░" * (ancho - llenos)


def _nivel_fantasma(v) -> str:
    """Etiqueta de riesgo del índice Fantasma (TITAN V32)."""
    if v is None:
        return "—"
    if v < 5:
        return "LOW · calma"
    if v < 15:
        return "MODERATE · atención"
    if v < 30:
        return "HIGH · avisar"
    return "CRITICAL · protocolo"


# Glosario común: hace el reporte legible para cualquiera, no solo para el operador.
GLOSARIO = f"""## ℹ️ Cómo leer este reporte

- **Fantasma** — índice de *riesgo cósmico* (TITAN V32). **No es un sismo**: mide la
  tensión del sistema combinando campo magnético (Bz), viento solar, resonancia
  Schumann, presión y más. Escala: **LOW <5** (calma) · **MODERATE 5–15** (atención)
  · **HIGH 15–30** (avisar) · **CRITICAL ≥30** (protocolo).
- **Muro de los 5 Eventos** — cinco "paredes" de correlación (geofísica, atmosférica,
  oceánica, solar/geomagnética y financiera). Hay *breach* cuando **3 o más** se
  activan a la vez.
- **Asertividad viva** — de las predicciones ya verificadas contra la realidad (USGS),
  qué porcentaje resultó **ACIERTO**. El conteo impreso conserva la `ventana_h`
  almacenada en cada fila; no es todavía un filtro de **M>={BLANCO_REPORTE_MAGNITUD:.1f}
  dentro de {BLANCO_REPORTE_VENTANA_H} h** ni una relabelización del histórico.
  Ese es el blanco objetivo para reportes nuevos. El umbral del muro no cambia.
  El Juez audita aparte (nunca predice).
- **Cimática** — patrones de telemetría que el sistema ve repetirse; si un patrón
  antecede a un evento real se etiqueta con su clase (SISMO_M4…M7, ERUPCION_VEI…).
  La frecuencia es cuántas veces se ha visto ese patrón.
- **Anticipación** — días de adelanto promedio entre la señal y el evento.
"""


def _gan_txt(m) -> str:
    """La ganancia, o el comparador que la sustituye cuando no hay eventos."""
    if not isinstance(m, dict):
        return "—" if m is None else f"{m:.2f}×"
    g, muda, con_ev = m.get("ganancia"), m.get("muda"), m.get("con_evento")
    if g is not None:
        return f"{g:.2f}×"
    if con_ev == 0:
        return ("sin eventos" if muda is None
                else f"sin eventos (callarse: {muda:.0%})")
    return "—"


def _lectura_rapida(fant_media, breaches, viva, ganancia=None) -> str:
    """Una línea en lenguaje llano que resume el estado del periodo.

    La asertividad va SIEMPRE con su ganancia. Sola es engañosa: cuenta como
    acierto cada silencio en calma, que es casi todo el tiempo. Una ganancia
    <= 1x significa que alarmar a ciegas lo habría hecho igual de bien.
    """
    tranquilo = (fant_media or 0) < 15 and not breaches
    partes = [f"el sistema estuvo **{'en calma' if tranquilo else 'inquieto'}**"]
    if fant_media is not None:
        partes.append(f"Fantasma medio **{fant_media:.1f}** ({_nivel_fantasma(fant_media)})")
    partes.append("Muro **sin roturas**" if not breaches else f"Muro con **{breaches} breach(es)**")
    m = ganancia if isinstance(ganancia, dict) else {"ganancia": ganancia}
    g, muda, con_ev = m.get("ganancia"), m.get("muda"), m.get("con_evento")
    if viva is not None:
        if g is not None:
            juicio = "no supera al azar" if g <= 1.0 else "aporta"
            partes.append(f"asertividad viva **{viva:.0%}** con ganancia "
                          f"**{g:.2f}×** ({juicio})")
        elif con_ev == 0:
            # La ganancia es indefinida con todo derecho: sin un solo evento en
            # la ventana no hay nada que detectar, asi que «mejor que el azar»
            # no significa nada. Pero el comparador honesto SI existe, y es
            # devastador: `asertividad_muda` es lo que habria sacado un bot que
            # se calla. Medido el 2026-10-08: el sistema 56 %, callarse 100 %.
            extra = "" if muda is None else f"; **callarse habría dado {muda:.0%}**"
            partes.append(f"asertividad viva **{viva:.0%}** — pero **no hubo "
                          f"ningún evento que detectar** en el periodo, así que "
                          f"la ganancia es indefinida{extra}")
        else:
            partes.append(f"asertividad viva **{viva:.0%}** (sin ganancia "
                          "medida: no se puede leer sola)")
    return "> **Lectura rápida:** " + " · ".join(partes) + "."


def _grafica_aciertos_pastel(stats: dict, nombre: str) -> str:
    """Gráfica de pastel: Aciertos vs Fallos vs Falsos Positivos."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""

    aciertos = stats["aciertos_totales"] or 0
    fallos = stats["fallos_totales"] or 0
    falsos = stats["falsos_positivos_totales"] or 0

    if aciertos + fallos + falsos == 0:
        return ""

    fig, ax = plt.subplots(figsize=(7, 5), dpi=120)
    sizes = [aciertos, fallos, falsos]
    labels = [f"Aciertos\n{aciertos}", f"Fallos\n{fallos}", f"Falsos positivos\n{falsos}"]
    colors = ["#059669", "#dc2626", "#f59e0b"]  # verde, rojo, ámbar

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"fontsize": 9, "weight": "bold"}
    )
    for autotext in autotexts:
        autotext.set_color("white")
        autotext.set_fontsize(8)

    ax.set_title("Distribución de Veredictos", fontsize=11, weight="bold", pad=20)
    fig.tight_layout()
    DIR_GRAFICAS.mkdir(parents=True, exist_ok=True)
    ruta = DIR_GRAFICAS / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return str(ruta)


def _grafica_aciertos_barras(stats: dict, nombre: str) -> str:
    """Gráfica de barras: Tasa de acierto por bot."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""

    if not stats.get("por_bot"):
        return ""

    bots = list(stats["por_bot"].keys())
    tasas = [stats["por_bot"][bot]["tasa_acierto"] * 100 for bot in bots]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
    bars = ax.barh(bots, tasas, color=COLOR_SERIE, height=0.6)

    # Anotar porcentajes
    for i, (bar, tasa) in enumerate(zip(bars, tasas)):
        ax.text(tasa + 1, bar.get_y() + bar.get_height() / 2,
                f"{tasa:.0f}%", va="center", fontsize=9, weight="bold")

    ax.set_xlabel("Tasa de acierto (%)", fontsize=9)
    ax.set_title("Desempeño por Bot", fontsize=11, weight="bold")
    ax.set_xlim(0, 110)
    ax.grid(axis="x", color=COLOR_CONTEXTO, alpha=0.3, linewidth=0.7)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)

    fig.tight_layout()
    DIR_GRAFICAS.mkdir(parents=True, exist_ok=True)
    ruta = DIR_GRAFICAS / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return str(ruta)


def _seccion_aciertos(db_path: str, dias: int, titulo: str) -> tuple:
    """Genera sección de aciertos con gráficas para reportes periódicos.

    Retorna: (markdown_text, list_of_image_paths)
    """
    try:
        stats = obtener_estadisticas_aciertos(db_path, dias)
    except Exception:
        return "", []

    if stats["total_predicciones"] == 0:
        return f"## ✅ {titulo}\n\n**No hay predicciones auditadas en este período.**\n", []

    imagenes = []
    lineas = [
        f"## ✅ {titulo}",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| **Aciertos** | {stats['aciertos_totales']} |",
        f"| **Fallos** | {stats['fallos_totales']} |",
        f"| **Falsos positivos** | {stats['falsos_positivos_totales']} |",
        f"| **Tasa de acierto** | {stats['tasa_acierto_global']:.1%} `{_barra(stats['tasa_acierto_global'], 12)}` |",
        f"| **Total predicciones** | {stats['total_predicciones']} |",
        "",
    ]

    # Gráfica de pastel
    sufijo = f"aciertos_{dias}d_pastel.png"
    grafica_pastel = _grafica_aciertos_pastel(stats, sufijo)
    if grafica_pastel:
        imagenes.append(grafica_pastel)
        lineas.append(f"![Distribución de veredictos](graficas/{sufijo})")
        lineas.append("")

    if stats["por_bot"]:
        lineas += [
            "### 🤖 Desempeño por Bot",
            "",
            "| Bot | Aciertos | Tasa | Confianza | Anticipación |",
            "|-----|----------|------|-----------|---------------|",
        ]
        for bot, datos in stats["por_bot"].items():
            tasa_bot = datos["tasa_acierto"]
            conf = datos["confianza_promedio"] or 0
            dias_ant = datos["dias_anticipacion_promedio"] or 0
            lineas.append(
                f"| {bot} | {datos['aciertos']}/{datos['total']} | "
                f"{tasa_bot:.0%} `{_barra(tasa_bot, 8)}` | "
                f"{conf:.2f} | {dias_ant:.1f}d |"
            )
        lineas.append("")

        # Gráfica de barras
        sufijo_barras = f"aciertos_{dias}d_barras.png"
        grafica_barras = _grafica_aciertos_barras(stats, sufijo_barras)
        if grafica_barras:
            imagenes.append(grafica_barras)
            lineas.append(f"![Desempeño por bot](graficas/{sufijo_barras})")
            lineas.append("")

    return "\n".join(lineas), imagenes


def comparativo(conn) -> tuple:
    """Hoy vs ayer (corre 12pm y 12am hora MX)."""
    ahora = _ahora_mx()
    dias = _dias_resumen(conn, 3)
    hoy_str = ahora.strftime("%Y-%m-%d")
    ayer_str = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    hoy = next((d for d in dias if d["dia"] == hoy_str), None)
    ayer = next((d for d in dias if d["dia"] == ayer_str), None)

    ts_hoy0 = datetime(ahora.year, ahora.month, ahora.day,
                       tzinfo=timezone.utc).timestamp() - MX_UTC_OFFSET * 3600
    viva_hoy, n_hoy, gan_hoy = _viva_en_rango(conn, ts_hoy0, ts_hoy0 + 86400)
    viva_ayer, n_ayer, gan_ayer = _viva_en_rango(conn, ts_hoy0 - 86400, ts_hoy0)

    cim = conn.execute(
        "SELECT COUNT(*), SUM(primera_vez >= datetime('now','-1 day')) "
        "FROM tbl_cimatica_patrones").fetchone()

    def _v(d, k):
        return d.get(k) if d else None

    lineas = [
        f"# 🔄 Comparativo diario — {hoy_str} vs {ayer_str}",
        f"*Corte {ahora.strftime('%H:%M')} hora MX*", "",
        "| Métrica | Hoy | Ayer | Cambio |",
        "|---|---:|---:|---:|",
        f"| Fantasma medio | {(_v(hoy,'fantasma_media') or 0):.1f} | "
        f"{(_v(ayer,'fantasma_media') or 0):.1f} | "
        f"{_delta_txt(_v(hoy,'fantasma_media'), _v(ayer,'fantasma_media'))} |",
        f"| Fantasma máx | {(_v(hoy,'fantasma_max') or 0):.1f} | "
        f"{(_v(ayer,'fantasma_max') or 0):.1f} | "
        f"{_delta_txt(_v(hoy,'fantasma_max'), _v(ayer,'fantasma_max'))} |",
        f"| Ciclos corridos | {_v(hoy,'n_ciclos') or 0} | "
        f"{_v(ayer,'n_ciclos') or 0} | "
        f"{_delta_txt(_v(hoy,'n_ciclos'), _v(ayer,'n_ciclos'), '{:+.0f}')} |",
        f"| Breaches del Muro | {_v(hoy,'breaches') or 0} | "
        f"{_v(ayer,'breaches') or 0} | "
        f"{_delta_txt(_v(hoy,'breaches'), _v(ayer,'breaches'), '{:+.0f}')} |",
        f"| Asertividad viva (resuelta en el día) | "
        f"{f'{viva_hoy:.0%} (n={n_hoy})' if viva_hoy is not None else '—'} | "
        f"{f'{viva_ayer:.0%} (n={n_ayer})' if viva_ayer is not None else '—'} | "
        f"{_delta_txt(viva_hoy, viva_ayer, '{:+.0%}') if None not in (viva_hoy, viva_ayer) else '—'} |",
        # La ganancia va PEGADA a la asertividad, nunca en otra parte del
        # reporte: leer el 97 % sin el 1,04x es lo que sostuvo la idea de que
        # el sistema acertaba.
        f"| …y su ganancia (Molchan) | {_gan_txt(gan_hoy)} | "
        f"{_gan_txt(gan_ayer)} | "
        f"{_delta_txt(gan_hoy.get('ganancia'), gan_ayer.get('ganancia'), '{:+.2f}') if None not in (gan_hoy.get('ganancia'), gan_ayer.get('ganancia')) else '—'} |",
        f"| Patrones cimáticos (total / nuevos 24h) | "
        f"{cim[0]} | — | +{cim[1] or 0} |",
        "",
        _lectura_rapida(_v(hoy, "fantasma_media"), _v(hoy, "breaches"), viva_hoy,
                        gan_hoy), "",
    ]

    aciertos_sec, aciertos_imgs = _seccion_aciertos(DB_DEFAULT, 1, "Aciertos — Últimas 24 horas")
    if aciertos_sec:
        lineas.append(aciertos_sec)

    grafica = _grafica_serie(
        _dias_resumen(conn, 7), "fantasma_media",
        "Fantasma medio — últimos 7 días", "índice fantasma",
        "comparativo_fantasma.png", resalta_max=True)
    if grafica:
        lineas.append("![Fantasma 7 días](graficas/comparativo_fantasma.png)")
    lineas += ["", GLOSARIO]
    ruta = DIR_ESTADO / "REPORTE_COMPARATIVO.md"
    ruta.write_text("\n".join(lineas), encoding="utf-8")

    adjuntos = [str(grafica)] if grafica else []
    adjuntos.extend(aciertos_imgs)
    return ruta, lineas, adjuntos


def _resumen_rango(conn, n_dias, titulo, archivo, prefijo_grafica):
    ahora = _ahora_mx()
    dias = _dias_resumen(conn, n_dias)
    ahora_ts = datetime.now(timezone.utc).timestamp()
    viva, n_viva, gan_viva = _viva_en_rango(conn, ahora_ts - n_dias * 86400, ahora_ts)

    cim = conn.execute(
        "SELECT ambito, COUNT(*), MAX(frecuencia) FROM tbl_cimatica_patrones "
        "GROUP BY ambito").fetchall()
    consistentes = conn.execute(
        "SELECT patron_id, ambito, id_nodo, event_class, frecuencia "
        "FROM tbl_cimatica_patrones WHERE frecuencia >= 3 "
        "ORDER BY frecuencia DESC LIMIT 10").fetchall()

    tot_ciclos = sum(d["n_ciclos"] or 0 for d in dias)
    tot_breach = sum(d["breaches"] or 0 for d in dias)
    fant = [d["fantasma_media"] for d in dias if d["fantasma_media"]]
    fant_media_val = (sum(fant) / len(fant)) if fant else None

    lineas = [
        f"# {titulo}",
        f"*Generado {ahora.strftime('%Y-%m-%d %H:%M')} hora MX — "
        f"ventana {n_dias} días*", "",
        _lectura_rapida(fant_media_val, tot_breach, viva, gan_viva), "",
        "## Resumen",
        f"- Ciclos corridos: **{tot_ciclos}**",
        f"- Fantasma medio del periodo: "
        f"**{(sum(fant)/len(fant)):.1f}**" if fant else
        "- Fantasma medio del periodo: —",
        f"- Fantasma máximo: "
        f"**{max((d['fantasma_max'] or 0) for d in dias):.1f}**"
        if dias else "- Fantasma máximo: —",
        f"- Breaches del Muro: **{tot_breach}**",
        f"- Asertividad viva del periodo: "
        f"**{f'{viva:.0%}' if viva is not None else '—'}** "
        f"(n={n_viva} resueltas)",
        "",
        "## Cimática",
    ]
    for ambito, n, fmax in cim:
        lineas.append(f"- Patrones `{ambito}`: {n} (frecuencia máx {fmax})")
    if consistentes:
        lineas += ["", "| Patrón | Ámbito | Evento asociado | Frecuencia |",
                   "|---|---|---|---:|"]
        for pid, amb, nodo, ec, frec in consistentes:
            lugar = f"nodo {nodo}" if nodo else "general"
            lineas.append(f"| {pid} | {lugar} | {ec or '—'} | {frec} |")
    lineas.append("")

    aciertos_titulo = f"Aciertos — Últimos {n_dias} días"
    aciertos_sec, aciertos_imgs = _seccion_aciertos(DB_DEFAULT, n_dias, aciertos_titulo)
    if aciertos_sec:
        lineas.append(aciertos_sec)

    adjuntos = list(aciertos_imgs)
    for campo, tit, ylab, nombre, resalta in (
        ("fantasma_media", "Fantasma medio diario", "índice",
         f"{prefijo_grafica}_fantasma.png", True),
        ("alertas", "Alertas por día", "alertas",
         f"{prefijo_grafica}_alertas.png", False),
        ("breaches", "Breaches del Muro por día", "breaches",
         f"{prefijo_grafica}_breaches.png", False),
    ):
        g = _grafica_serie(dias, campo, tit, ylab, nombre, resalta_max=resalta)
        if g:
            adjuntos.append(str(g))
            lineas.append(f"![{tit}](graficas/{nombre})")
    lineas += ["", GLOSARIO]
    ruta = DIR_ESTADO / archivo
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta, lineas, adjuntos


def _texto_telegram(lineas: list) -> str:
    """Resumen plano para Telegram: sin tablas, imágenes ni glosario largo."""
    out = []
    for ln in lineas:
        if ln.startswith("![") or ln.startswith("|"):
            continue
        if ln.startswith("## ℹ️"):        # corta antes del glosario
            break
        out.append(ln)
    txt = "\n".join(out).replace("**", "").replace("`", "").replace("> ", "")
    while "\n\n\n" in txt:
        txt = txt.replace("\n\n\n", "\n\n")
    return txt.strip()[:3900]


def _enviar_telegram(lineas: list, adjuntos: list, ruta_md: Path) -> bool:
    """Envía el reporte a Telegram: resumen + gráficas + el .md como documento.

    Fail-soft: sin TELEGRAM_BOT_TOKEN/CHAT_ID no envía (las funciones retornan
    False). Respeta SENTINEL_DRY_RUN para las fotos.
    """
    try:
        from sentinel_omega.infrastructure.api.telegram import (
            send_alert, send_photo, send_document,
        )
    except Exception as e:
        print(f"Telegram no disponible: {e}")
        return False
    ok = send_alert(_texto_telegram(lineas))
    for img in adjuntos:
        try:
            send_photo(str(img), caption=Path(img).stem)
        except Exception:
            pass
    try:
        send_document(str(ruta_md), caption=ruta_md.stem)
    except Exception:
        pass
    print(f"Telegram: resumen={'ok' if ok else 'no enviado (sin credenciales?)'}, "
          f"{len(adjuntos)} gráfica(s) + documento")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparativo", action="store_true")
    ap.add_argument("--semanal", action="store_true")
    ap.add_argument("--mensual", action="store_true")
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--no-telegram", action="store_true",
                    help="No enviar a Telegram (solo archivo)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    ahora = _ahora_mx().strftime("%Y-%m-%d %H:%M")

    if args.comparativo:
        ruta, lineas, adj = comparativo(conn)
    elif args.semanal:
        ruta, lineas, adj = _resumen_rango(
            conn, 7, "📅 Reporte semanal — Sentinel Omega",
            "REPORTE_SEMANAL.md", "semanal")
    elif args.mensual:
        ruta, lineas, adj = _resumen_rango(
            conn, 31, "🗓️ Reporte mensual — Sentinel Omega",
            "REPORTE_MENSUAL.md", "mensual")
    else:
        ap.error("indica --comparativo, --semanal o --mensual")
    print(f"Reporte generado: {ruta}")

    if not args.no_telegram:
        _enviar_telegram(lineas, adj, ruta)
    else:
        print("Telegram: deshabilitado (--no-telegram)")


if __name__ == "__main__":
    main()
