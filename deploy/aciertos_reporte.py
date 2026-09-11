#!/usr/bin/env python3
"""
Extrae los aciertos (resultado='ACIERTO' en TBL_JUEZ_AUDITORIA) y los formatea
para reportes.

Muestra:
- Eventos predichos correctamente
- Momento de la predicción y momento en que el Juez la resolvió
- Ventana declarada de la predicción (lo que el bot se jugó)
- Confianza del bot
- Tasa de aciertos sobre lo REALMENTE auditado

Nota de honestidad (regla "cero datos sintéticos"):
`TBL_JUEZ_AUDITORIA` NO guarda el instante del evento real, ni su clase, ni
su magnitud o ubicación como columnas. Lo que guarda es:

    timestamp · bot_name · prediccion · confianza · ventana_h ·
    verdad · resultado · severidad · reincidencia · detalles_json ·
    resuelto_at · fase

Por eso aquí NO se calcula una "anticipación en días" (sería inventada): se
reporta la **ventana declarada** (`ventana_h`), que es el compromiso real que
el bot asumió. La magnitud y el ámbito se extraen del texto de `verdad`
—que el Juez escribe como "N eventos en ventana de Xh (máx M4.9, ámbito)"—
y quedan en `None` cuando esa cadena no los trae.
"""

import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional

DB_DEFAULT = str(
    Path(__file__).parent.parent / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
)

# Estados terminales: una predicción "auditada" es una que el Juez ya resolvió.
# PENDIENTE queda fuera de las tasas — si no, la tasa baja sola con solo
# abrir predicciones nuevas.
RESUELTOS = ("ACIERTO", "FALLO", "FALSO_POSITIVO")

# El Juez escribe `verdad` en dos formas (core/juez/juez.py):
#   con eventos : "3 eventos en ventana de 2h (máx M5.2, nodos de la predicción)"
#   sin eventos : "sin eventos en ventana de 2h (global)"
# El ámbito es siempre el último paréntesis; la magnitud solo aparece en la
# primera forma.
_RE_MAGNITUD = re.compile(r"m[áa]x\s*M\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_RE_PARENTESIS_FINAL = re.compile(r"\(([^)]*)\)\s*$")


def _barra(pct: float, ancho: int = 10) -> str:
    """Barra visual ▓▓▓░░ para porcentajes en Markdown."""
    if pct is None:
        return ""
    llenos = round(max(0.0, min(1.0, pct)) * ancho)
    return "▓" * llenos + "░" * (ancho - llenos)


def _magnitud_de_verdad(verdad: Optional[str]) -> Optional[float]:
    """Magnitud máxima embebida en el texto de `verdad`; None si no la trae."""
    if not verdad:
        return None
    m = _RE_MAGNITUD.search(verdad)
    return float(m.group(1)) if m else None


def _ambito_de_verdad(verdad: Optional[str]) -> Optional[str]:
    """Ámbito geográfico embebido en `verdad` (nodos propios / zonas / global)."""
    if not verdad:
        return None
    m = _RE_PARENTESIS_FINAL.search(verdad.strip())
    if not m:
        return None
    # "máx M5.2, nodos de la predicción" → el ámbito es lo que sigue a la coma;
    # "global" → no hay coma y el contenido entero es el ámbito.
    contenido = m.group(1).split(",")[-1].strip()
    return contenido or None


def _dt_utc(epoch: Optional[float]) -> Optional[datetime]:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def obtener_aciertos_recientes(db_path: str = DB_DEFAULT, dias: int = 30) -> List[Dict]:
    """
    Obtiene los aciertos (resultado='ACIERTO') de los últimos N días.

    Retorna lista de dicts:
    {
        "timestamp_prediccion": <datetime>,
        "resuelto_at": <str|None>,   # cuándo el Juez cerró la fila
        "ventana_h": <int>,          # ventana declarada por la predicción
        "bot": <str>,
        "prediccion": <str>,
        "verdad": <str>,             # texto del Juez con el conteo de eventos
        "magnitude": <float|None>,   # extraída de `verdad`, None si no viene
        "ambito": <str|None>,        # extraído de `verdad`, None si no viene
        "confianza": <float>,        # 0-1
        "fase": <str>,
    }
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    hace_n_dias = datetime.now(timezone.utc) - timedelta(days=dias)
    timestamp_cutoff = hace_n_dias.timestamp()

    query = """
    SELECT
        j.timestamp AS timestamp_prediccion,
        j.resuelto_at,
        j.ventana_h,
        j.bot_name,
        j.prediccion,
        j.verdad,
        j.confianza,
        j.fase
    FROM TBL_JUEZ_AUDITORIA j
    WHERE j.resultado = 'ACIERTO'
      AND j.timestamp >= ?
    ORDER BY j.timestamp DESC
    """

    rows = conn.execute(query, (timestamp_cutoff,)).fetchall()
    conn.close()

    aciertos = []
    for row in rows:
        verdad = row["verdad"]
        aciertos.append({
            "timestamp_prediccion": _dt_utc(row["timestamp_prediccion"]),
            "resuelto_at": row["resuelto_at"],
            "ventana_h": row["ventana_h"],
            "bot": row["bot_name"],
            "prediccion": row["prediccion"],
            "verdad": verdad,
            "magnitude": _magnitud_de_verdad(verdad),
            "ambito": _ambito_de_verdad(verdad),
            "confianza": row["confianza"],
            "fase": row["fase"],
        })

    return aciertos


def obtener_estadisticas_aciertos(db_path: str = DB_DEFAULT, dias: int = 90) -> Dict:
    """
    Calcula estadísticas de aciertos:
    - Aciertos vs fallos vs falsos positivos (y pendientes, aparte)
    - Tasa de aciertos sobre lo RESUELTO (las pendientes no cuentan)
    - Tasa de aciertos por bot
    - Ventana declarada promedio y confianza promedio por bot
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    hace_n_dias = datetime.now(timezone.utc) - timedelta(days=dias)
    timestamp_cutoff = hace_n_dias.timestamp()

    total_query = """
    SELECT
        SUM(CASE WHEN resultado = 'ACIERTO' THEN 1 ELSE 0 END) as aciertos,
        SUM(CASE WHEN resultado = 'FALLO' THEN 1 ELSE 0 END) as fallos,
        SUM(CASE WHEN resultado = 'FALSO_POSITIVO' THEN 1 ELSE 0 END) as falsos_positivos,
        SUM(CASE WHEN resultado = 'PENDIENTE' THEN 1 ELSE 0 END) as pendientes,
        COUNT(*) as total_filas
    FROM TBL_JUEZ_AUDITORIA
    WHERE timestamp >= ?
    """

    total_row = conn.execute(total_query, (timestamp_cutoff,)).fetchone()

    por_bot_query = """
    SELECT
        bot_name,
        SUM(CASE WHEN resultado = 'ACIERTO' THEN 1 ELSE 0 END) as aciertos,
        COUNT(*) as total,
        ROUND(AVG(confianza), 3) as confianza_promedio,
        ROUND(AVG(CAST(ventana_h AS FLOAT)), 1) as ventana_h_promedio
    FROM TBL_JUEZ_AUDITORIA
    WHERE timestamp >= ? AND resultado IN ({_in_resueltos})
    GROUP BY bot_name
    ORDER BY aciertos DESC
    """.format(_in_resueltos=", ".join(f"'{r}'" for r in RESUELTOS))

    por_bot = conn.execute(por_bot_query, (timestamp_cutoff,)).fetchall()

    conn.close()

    por_bot_dict = {}
    for row in por_bot:
        total_bot = row["total"] or 0
        aciertos_bot = row["aciertos"] or 0
        por_bot_dict[row["bot_name"]] = {
            "aciertos": aciertos_bot,
            "total": total_bot,
            "tasa_acierto": aciertos_bot / total_bot if total_bot > 0 else 0,
            "confianza_promedio": row["confianza_promedio"],
            "ventana_h_promedio": row["ventana_h_promedio"],
        }

    aciertos_n = total_row["aciertos"] or 0
    fallos_n = total_row["fallos"] or 0
    falsos_n = total_row["falsos_positivos"] or 0
    pendientes_n = total_row["pendientes"] or 0
    resueltas = aciertos_n + fallos_n + falsos_n

    return {
        "periodo_dias": dias,
        "aciertos_totales": aciertos_n,
        "fallos_totales": fallos_n,
        "falsos_positivos_totales": falsos_n,
        "pendientes_totales": pendientes_n,
        # "auditadas" = resueltas por el Juez. Las PENDIENTE no entran en la
        # tasa: aún no se sabe si acertaron.
        "total_predicciones": resueltas,
        "total_filas": total_row["total_filas"] or 0,
        "tasa_acierto_global": (aciertos_n / resueltas) if resueltas else 0.0,
        "por_bot": por_bot_dict,
    }


def seccion_aciertos_markdown(db_path: str = DB_DEFAULT, dias: int = 30) -> str:
    """
    Genera la sección Markdown de aciertos para insertar en reportes.
    """
    aciertos = obtener_aciertos_recientes(db_path, dias)
    stats = obtener_estadisticas_aciertos(db_path, dias)

    lineas = [
        "## ✅ Aciertos y Predicciones Correctas",
        "",
        "> El sistema también tiene victorias que celebrar. Esta sección documenta "
        "cuándo nuestras predicciones fueron correctas: qué anticipamos, con qué "
        "ventana nos jugamos el aviso y qué encontró el Juez al verificarlo.",
        "",
    ]

    # ── Estadísticas generales ──
    total = stats["total_predicciones"]
    aciertos_n = stats["aciertos_totales"]
    tasa = stats["tasa_acierto_global"]

    lineas += [
        "### 📊 Resumen — Últimos {} días".format(dias),
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| **Aciertos** | {aciertos_n} |",
        f"| **Fallos** | {stats['fallos_totales']} |",
        f"| **Falsos positivos** | {stats['falsos_positivos_totales']} |",
        f"| **Tasa de acierto** | {tasa:.1%} `{_barra(tasa, 12)}` |",
        f"| **Predicciones auditadas** | {total} |",
        f"| **Pendientes (ventana abierta)** | {stats['pendientes_totales']} |",
        "",
        "_La tasa se calcula solo sobre lo que el Juez ya resolvió; las "
        "pendientes aún no se sabe si aciertan._",
        "",
    ]

    # ── Por bot ──
    if stats["por_bot"]:
        lineas += [
            "### 🤖 Desempeño por Bot",
            "",
            "| Bot | Aciertos | Tasa | Confianza | Ventana declarada (h) |",
            "|-----|----------|------|-----------|------------------------|",
        ]
        for bot, datos in stats["por_bot"].items():
            tasa_bot = datos["tasa_acierto"]
            conf = datos["confianza_promedio"] or 0
            ventana = datos["ventana_h_promedio"] or 0
            lineas.append(
                f"| {bot} | {datos['aciertos']}/{datos['total']} | "
                f"{tasa_bot:.0%} `{_barra(tasa_bot, 8)}` | "
                f"{conf:.2f} | {ventana:.1f} |"
            )
        lineas.append("")

    # ── Eventos recientes correctamente predichos ──
    if aciertos:
        lineas += [
            "### 🎯 Eventos Predichos Correctamente (más recientes primero)",
            "",
        ]

        for acierto in aciertos[:10]:  # Mostrar top 10
            ts_pred = acierto["timestamp_prediccion"].strftime("%Y-%m-%d %H:%M")
            ts_resuelto = acierto["resuelto_at"] or "—"
            ventana = acierto["ventana_h"]
            ventana_txt = f"{ventana}h" if ventana is not None else "—"
            magnitude = f"M{acierto['magnitude']:.1f}" if acierto["magnitude"] is not None else "—"
            confianza = acierto["confianza"] or 0
            bot = acierto["bot"]
            ambito = acierto["ambito"] or "—"

            lineas += [
                f"#### {bot.upper()} — {acierto['prediccion']} {magnitude} ({ambito})",
                "",
                f"- **Predicción:** {ts_pred} UTC",
                f"- **Ventana declarada:** {ventana_txt}",
                f"- **Resuelta por el Juez:** {ts_resuelto}",
                f"- **Verdad registrada:** {acierto['verdad'] or '—'}",
                f"- **Confianza:** {confianza:.1%} `{_barra(confianza, 10)}`",
                f"- **Fase:** {acierto['fase']}",
                "",
            ]

        if len(aciertos) > 10:
            lineas.append(f"_... y {len(aciertos) - 10} aciertos más en los últimos {dias} días_")
            lineas.append("")
    else:
        lineas += [
            "**Aún no hay aciertos registrados en este período.**",
            "El sistema comenzó hace poco o estamos en fase de aprendizaje.",
            "",
        ]

    return "\n".join(lineas)


if __name__ == "__main__":
    # Para debug: mostrar tabla de aciertos
    print(seccion_aciertos_markdown())
