"""
Pesos de credibilidad por bot — the substrate of hierarchical punishment.

The Padre weighs each bot's vote in consensus by its peso. Training Fase 2
adjusts them: a bot that fails to recognize enforceable knowledge is
punished (hijo x1); the Padre pays double (x2) when its own meta-signature
fails — base_geo protocol. Recognition earns mild reinforcement.

Bounds keep any bot from being silenced or deified: [0.3, 1.5].
"""

import logging
import re
import sqlite3
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PESO_DEFAULT = 1.0
PESO_BASELINE = 1.0        # normal reinforcement only RECOVERS up to here
PESO_MIN = 0.3
PESO_MAX = 1.5             # only attention redistribution can push above 1.0

CASTIGO_HIJO = 0.95        # x1 — multiplicative decay per failure
CASTIGO_PADRE = 0.90       # x2 — the Padre pays double
REFUERZO = 1.02            # mild reinforcement per recognition


def cargar_pesos(
    conn: sqlite3.Connection,
    por_merito: bool = False,
    minimo_ventanas: int = 50,
) -> Dict[str, float]:
    """Los pesos con los que vota cada bot (los que faltan valen 1.0 al leerse).

    `por_merito=True` devuelve el mérito medido contra quedarse callado en vez
    del paseo multiplicativo (ver `merito_relativo` al final del módulo). Un bot
    sin ventanas suficientes para juzgarlo CONSERVA su peso almacenado: no se le
    inventa un mérito que no se ha podido medir.
    """
    try:
        rows = conn.execute("SELECT bot_name, peso FROM TBL_PESOS_BOTS").fetchall()
        pesos = {bot: peso for bot, peso in rows}
    except sqlite3.OperationalError:
        pesos = {}
    if not por_merito:
        return pesos
    # Orden de prioridad, de menos a más fundado:
    #   1. el paseo almacenado (lo que ya había)
    #   2. la COMPETENCIA por clase de evento --- 4.696 veredictos que
    #      discriminan, y respeta al especialista: beta2 es malo en M3 y M4
    #      pero el MEJOR en M5, así que conserva voz
    #   3. el MÉRITO de la fase viva, si hay episodios de evento suficientes
    #      (hoy no los hay: 3 en 17 días, así que se abstiene)
    competencia = pesos_por_competencia(conn)
    for bot, peso in competencia.items():
        pesos[bot] = peso
    aplicados = pesos_por_merito(conn, minimo_ventanas=minimo_ventanas)
    for bot, m in aplicados.items():
        pesos[bot] = m["peso"]
    # Cuántos méritos se pudieron calcular de verdad. Sin esto, el arranque
    # decía «MERITO contra el silencio» aunque no se hubiera aplicado ninguno
    # por falta de evidencia, y el registro engañaba al que lo leyera.
    pesos["_meritos_aplicados"] = float(len(aplicados))
    pesos["_competencias_aplicadas"] = float(len(competencia))
    return pesos


def _ajustar(
    conn: sqlite3.Connection,
    bot: str,
    factor: float,
    es_fallo: bool,
    techo: float = PESO_MAX,
) -> float:
    row = conn.execute(
        "SELECT peso FROM TBL_PESOS_BOTS WHERE bot_name = ?", (bot,)
    ).fetchone()
    peso_actual = row[0] if row else PESO_DEFAULT
    nuevo = max(PESO_MIN, min(PESO_MAX, peso_actual * factor))
    if not es_fallo:
        # Reinforcement respects its ceiling and never LOWERS a weight that
        # is already above it (e.g. earned via attention redistribution).
        nuevo = min(nuevo, max(techo, peso_actual))

    conn.execute(
        "INSERT INTO TBL_PESOS_BOTS (bot_name, peso, aciertos, fallos) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(bot_name) DO UPDATE SET "
        "peso = ?, "
        "aciertos = aciertos + ?, "
        "fallos = fallos + ?, "
        "updated_at = datetime('now')",
        (bot, nuevo, 0 if es_fallo else 1, 1 if es_fallo else 0,
         nuevo, 0 if es_fallo else 1, 1 if es_fallo else 0),
    )
    conn.commit()
    return nuevo


def castigar(
    conn: sqlite3.Connection,
    bot: str,
    es_padre: bool = False,
    gravedad: float = 1.0,
) -> float:
    """Punish a bot for missing enforceable knowledge.

    base_geo protocol: the punishment scales with the gravity of the error —
    missing an M7 hurts far more than missing an M5 (gravedad M5=1, M6=2,
    M7=3; decay factor raised to gravedad). The Padre pays double.
    """
    base = CASTIGO_PADRE if es_padre else CASTIGO_HIJO
    factor = base ** max(1.0, gravedad)
    nuevo = _ajustar(conn, bot, factor, es_fallo=True)
    logger.warning(
        f"CASTIGO {'x2 (PADRE)' if es_padre else 'x1'} a {bot} "
        f"(gravedad={gravedad:.1f}): peso -> {nuevo:.3f}"
    )
    return nuevo


def reforzar(
    conn: sqlite3.Connection,
    bot: str,
    hasta: float = PESO_BASELINE,
) -> float:
    """Mild reinforcement when the bot recognizes a known signature.

    Normal recognition only RECOVERS credibility up to the baseline (1.0) —
    doing your job doesn't earn extra weight, it just repairs punishment.
    Attention redistribution (the bot saw what the Padre missed) may pass
    hasta=PESO_MAX to reward above baseline.
    """
    return _ajustar(conn, bot, REFUERZO, es_fallo=False, techo=hasta)


# ─── Peso por MÉRITO: relativo a quedarse callado ────────────────────────────
#
# Medido el 2026-09-25 sobre los 19.422 veredictos reales de la fase viva, y es
# la razón de que esto exista: el paseo multiplicativo de arriba NO PUEDE
# expresar mérito relativo. Se replicó la secuencia real con tres reglas:
#
#   regla                         pesos finales            dispersión
#   actual (todo ACIERTO refuerza) 8 de 9 en 1.000          0.072
#   solo refuerzan las alarmas     los 9 en el suelo 0.300  0.017
#   silencio refuerza lento x1.002 0.306 a 0.515            0.056
#
# O todos al techo, porque la calma refuerza y borra el castigo (mediana: 5,9 h
# para volver a 1.0), o todos al suelo, porque hay 1.105 falsas alarmas y 313
# omisiones contra 20 detecciones. En ningún caso el peso informa, y un consenso
# ponderado donde todos pesan igual es un consenso sin ponderar.
#
# El mérito se mide como todo lo demás en este sistema: contra la estrategia
# tonta. Cada bot paga el coste de sus errores en la moneda del Juez (omitir 10,
# falsa alarma 1) y se compara con lo que habría pagado callándose siempre. Si
# ahorra, pesa más que 1; si sale más caro que el silencio, pesa menos. Con los
# datos reales da dispersión 0.298 y deja ver lo que el paseo escondía: beta2 es
# el único bot que le gana al silencio (11 de 37 eventos con 1 falsa alarma),
# mientras delta, alfa2 y loki no abren la boca jamás.

def merito_relativo(
    conn: sqlite3.Connection,
    bot: str,
    minimo_ventanas: int = 50,
    sev_fallo: float = 10.0,
    sev_falso_positivo: float = 1.0,
    minimo_eventos: int = 20,
) -> Optional[Dict[str, Any]]:
    """Mérito de un bot frente a callarse siempre, en la fase viva.

    Devuelve None cuando NO HAY EVIDENCIA para juzgarlo, y quien llame debe
    dejar su peso como estaba.

    `minimo_eventos` cuenta episodios de evento DISTINTOS, no ventanas. Se
    añadió el 2026-09-25 al descubrir que la cuenta por ciclos multiplica la
    misma evidencia: el ciclo corre cada 5 min y la ventana dura 2 h, así que un
    solo sismo «confirma» hasta 24 predicciones seguidas y una alarma sostenida
    cuenta como decenas de falsas alarmas. Medido ese día sobre 17 días de fase
    viva: 37 ventanas-ciclo con evento eran **3 episodios reales**, las «544
    falsas alarmas» de alfa1 eran **8 episodios** (precisión 12,5 %, la mejor de
    los nueve) y las «11 detecciones» de beta2 eran **una**. Con esa cuenta el
    mérito castigaba al bot más preciso y premiaba al de una sola observación.
    """
    from sentinel_omega.core.precursor.baseline import (
        evaluar_episodios,
        evaluar_veredictos,
    )

    try:
        filas_ts = conn.execute(
            "SELECT timestamp, verdad, resultado FROM TBL_JUEZ_AUDITORIA "
            "WHERE fase = 'viva' AND LOWER(bot_name) = ? "
            "AND resultado != 'PENDIENTE' AND verdad != ''",
            (bot.lower(),),
        ).fetchall()
    except sqlite3.OperationalError:
        return None
    filas = [(v, r) for _, v, r in filas_ts]
    if len(filas) < minimo_ventanas:
        return None
    episodios = evaluar_episodios(filas_ts, minimo_eventos=minimo_eventos)
    if episodios is None or not episodios["evidencia_suficiente"]:
        logger.info(
            "Mérito de %s sin evidencia: %s episodios de evento distintos "
            "(hacen falta %s). El peso se queda como estaba.",
            bot, (episodios or {}).get("eventos_distintos"), minimo_eventos,
        )
        return None
    m = evaluar_veredictos(filas, sev_fallo, sev_falso_positivo)
    if m is None or m.coste_mudo <= 0:
        return None
    ahorro = (m.coste_mudo - m.coste_sistema) / m.coste_mudo
    # `umbral_rentable` sale de la asimetría del Juez: con omitir=10 y falsa
    # alarma=1, alarmar sale a cuenta cuando la probabilidad de evento en la
    # ventana supera 1/(10+1) = 9,1 %. `precision` es esa probabilidad medida:
    # de las veces que el bot se mojó, cuántas tenían evento. Medido el
    # 2026-09-25, solo beta2 pasa el listón --- y por mucho: alarma 12 veces y
    # acierta 11 (91,7 %), mientras el resto no llega al 2 %.
    precision = (m.detectados / m.alarmas) if m.alarmas else None
    return {
        "bot": bot.lower(),
        "ventanas": m.ventanas,
        "eventos": m.con_evento,
        "detectados": m.detectados,
        "fallos": m.fallos,
        "falsos_positivos": m.falsos_positivos,
        "coste": m.coste_sistema,
        "coste_mudo": m.coste_mudo,
        "ahorro": ahorro,
        "alarmas": m.alarmas,
        "episodios": episodios["episodios"],
        "episodios_con_evento": episodios["episodios_con_evento"],
        "eventos_distintos": episodios["eventos_distintos"],
        "precision_episodios": episodios["precision"],
        "precision": precision,
        "umbral_rentable": m.umbral_rentable,
        "alarma_rentable": (precision is not None
                            and precision >= m.umbral_rentable),
        "peso": max(PESO_MIN, min(PESO_MAX, 1.0 + ahorro)),
    }


def pesos_por_merito(
    conn: sqlite3.Connection,
    minimo_ventanas: int = 50,
    sev_fallo: float = 10.0,
    sev_falso_positivo: float = 1.0,
    minimo_eventos: int = 20,
) -> Dict[str, Dict[str, Any]]:
    """El mérito de todos los bots que tienen veredictos vivos suficientes."""
    try:
        bots = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT LOWER(bot_name) FROM TBL_JUEZ_AUDITORIA "
                "WHERE fase = 'viva'"
            ).fetchall()
        ]
    except sqlite3.OperationalError:
        return {}
    fuera = {}
    for bot in bots:
        m = merito_relativo(conn, bot, minimo_ventanas, sev_fallo,
                            sev_falso_positivo, minimo_eventos)
        if m is not None:
            fuera[bot] = m
    return fuera


# ─── Competencia por CLASE de evento ─────────────────────────────────────────
#
# Un solo número por bot no basta, y lo dijo el operador: «tal vez en esto estás
# mal, pero para tal evento siempre le has atinado». Eso es medible.
#
# La fase de RECONOCIMIENTO no sirve para esto: sus 984.413 veredictos son
# TODOS acierto --- en el preentrenamiento, registrar una firma cuenta como
# acierto, así que ahí todos los bots son perfectos en todo. La que discrimina
# es la fase de TRASFONDO (castigo desde abajo, 4.696 veredictos) y la viva.
#
# Medido el 2026-09-26 sobre el trasfondo, y esto es exactamente lo que un
# número único escondía:
#
#     bot         M3            M4
#     padre    65/133 (49 %)  331/535 (62 %)   <- el mejor en M3
#     beta1    45/133 (34 %)  413/535 (77 %)   <- el mejor en M4
#     omega    52/133 (39 %)  383/535 (72 %)
#     alfa1    42/133 (32 %)  373/535 (70 %)
#     jupiter   0/133 ( 0 %)   60/535 (11 %)
#     loki      1/133 ( 1 %)   51/535 (10 %)
#
# No son el mismo experto: el Padre ve los pequeños y beta1 los medianos.

FASES_QUE_DISCRIMINAN = ("trasfondo", "viva")
MINIMO_POR_CLASE = 20


def _clase_de(verdad: str) -> Optional[str]:
    """La clase del evento desde la verdad del Juez: «…|M5.1» o «máx M5.0…»."""
    m = re.search(r"M(\d+)(?:\.\d+)?", str(verdad or ""))
    return f"M{m.group(1)}" if m else None


def competencia_por_clase(
    conn: sqlite3.Connection,
    minimo: int = MINIMO_POR_CLASE,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Qué tan bien ve cada bot CADA clase de evento.

    Devuelve {bot: {clase: {vistos, total, tasa}}}. Solo clases con al menos
    `minimo` eventos: con menos, la tasa es ruido y prometería una competencia
    que no se ha medido.
    """
    try:
        filas = conn.execute(
            "SELECT LOWER(bot_name), verdad, resultado FROM TBL_JUEZ_AUDITORIA "
            f"WHERE fase IN ({','.join('?' * len(FASES_QUE_DISCRIMINAN))}) "
            "AND resultado IN ('ACIERTO', 'FALLO') AND verdad != '' "
            "AND verdad NOT LIKE 'sin eventos%'",
            FASES_QUE_DISCRIMINAN,
        ).fetchall()
    except sqlite3.OperationalError:
        return {}

    crudo: Dict[str, Dict[str, list]] = {}
    for bot, verdad, resultado in filas:
        clase = _clase_de(verdad)
        if clase is None:
            continue
        casilla = crudo.setdefault(bot, {}).setdefault(clase, [0, 0])
        casilla[1] += 1
        if resultado == "ACIERTO":
            casilla[0] += 1

    fuera: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for bot, clases in crudo.items():
        for clase, (vistos, total) in clases.items():
            if total < minimo:
                continue
            fuera.setdefault(bot, {})[clase] = {
                "vistos": vistos, "total": total, "tasa": vistos / total,
            }
    return fuera


def pesos_por_competencia(
    conn: sqlite3.Connection,
    minimo: int = MINIMO_POR_CLASE,
) -> Dict[str, float]:
    """El peso de cada bot RELATIVO al mejor en cada clase.

    Para cada clase se mira quién es el mejor y se puntúa a los demás contra
    él; el peso del bot es su mejor puntuación. Así, un bot flojo en general
    pero el mejor en una clase conserva voz --- que es justo lo que un número
    único aplastaba. Recortado a [PESO_MIN, PESO_MAX].
    """
    perfil = competencia_por_clase(conn, minimo)
    if not perfil:
        return {}
    mejor_por_clase: Dict[str, float] = {}
    for clases in perfil.values():
        for clase, d in clases.items():
            if d["tasa"] > mejor_por_clase.get(clase, 0.0):
                mejor_por_clase[clase] = d["tasa"]
    pesos: Dict[str, float] = {}
    for bot, clases in perfil.items():
        relativas = [
            d["tasa"] / mejor_por_clase[clase]
            for clase, d in clases.items()
            if mejor_por_clase.get(clase, 0.0) > 0
        ]
        if not relativas:
            continue
        # Su MEJOR clase manda: el bot que solo sirve para una cosa, sirve.
        pesos[bot] = max(PESO_MIN, min(PESO_MAX, max(relativas)))
    return pesos


# ─── La memoria del perfil: cómo cambia cada experto con el tiempo ───────────
#
# El perfil por clase dice quién es bueno en qué HOY. Guardarlo en cada barrido
# convierte esa foto en una película, que es lo que permite decir «beta2 lleva
# tres cortes mejorando en M5» o «jupiter se apagó». Sin historia, el Padre solo
# puede reaccionar al último número, y un bot que empeora despacio no se nota.
#
# Tabla nueva, hacia delante: no reescribe nada de lo que ya hay.

SQL_TABLA_COMPETENCIA = """
CREATE TABLE IF NOT EXISTS tbl_competencia_historico (
    ts          REAL    NOT NULL,
    bot_name    TEXT    NOT NULL,
    clase       TEXT    NOT NULL,
    vistos      INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    tasa        REAL    NOT NULL,
    PRIMARY KEY (ts, bot_name, clase)
)
"""


def guardar_competencia(
    conn: sqlite3.Connection,
    minimo: int = MINIMO_POR_CLASE,
    ts: Optional[float] = None,
) -> int:
    """Guarda la foto de hoy. Devuelve cuántas filas escribió."""
    perfil = competencia_por_clase(conn, minimo)
    if not perfil:
        return 0
    momento = float(ts if ts is not None else time.time())
    conn.execute(SQL_TABLA_COMPETENCIA)
    filas = [
        (momento, bot, clase, d["vistos"], d["total"], d["tasa"])
        for bot, clases in perfil.items()
        for clase, d in clases.items()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO tbl_competencia_historico "
        "(ts, bot_name, clase, vistos, total, tasa) VALUES (?,?,?,?,?,?)",
        filas,
    )
    conn.commit()
    return len(filas)


def tendencia_competencia(
    conn: sqlite3.Connection,
    minimo_cortes: int = 2,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Cómo se mueve cada bot en cada clase: {bot: {clase: {...}}}.

    `cambio` es tasa de ahora menos la del corte más viejo que se conserva.
    Positivo = está aprendiendo; negativo = se está apagando. None cuando no
    hay al menos `minimo_cortes` fotos: con una sola no hay película.
    """
    try:
        filas = conn.execute(
            "SELECT bot_name, clase, ts, tasa FROM tbl_competencia_historico "
            "ORDER BY bot_name, clase, ts"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    series: Dict[str, Dict[str, list]] = {}
    for bot, clase, ts, tasa in filas:
        series.setdefault(bot, {}).setdefault(clase, []).append((ts, tasa))
    fuera: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for bot, clases in series.items():
        for clase, serie in clases.items():
            if len(serie) < minimo_cortes:
                continue
            primera, ultima = serie[0][1], serie[-1][1]
            fuera.setdefault(bot, {})[clase] = {
                "cortes": len(serie),
                "tasa_actual": ultima,
                "tasa_inicial": primera,
                "cambio": ultima - primera,
                "desde": serie[0][0],
            }
    return fuera
