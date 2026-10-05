"""
Muro de los Cinco Eventos — Cross-Correlation Precursor Framework

Five walls of correlated signals that, when aligned, indicate elevated
natural event probability. Each wall draws from different data domains:

  Wall 1 — GEOFÍSICO: Earthquakes, volcanic, seismic clusters
  Wall 2 — ATMOSFÉRICO: Blue Jets, Sprites Rojos, Niebla Tule, pressure anomalies
  Wall 3 — OCEÁNICO: Tsunamis, maremotos, hurricane proximity
  Wall 4 — SOLAR/GEOMAGNÉTICO: Tormenta solar, perturbación, Schumann, Silent Trigger
  Wall 5 — FINANCIERO/SOCIAL: Crypto fear, VIX spikes, bolsa bearish, trends

The "muro" fires when >= 3 walls are simultaneously active with correlated
precursors. The correlation score weights each wall by the confidence of
its strongest active precursor.

CALIBRACIÓN MEDIDA el 2026-10-02 sobre los 6.915 ciclos de `TBL_MURO_EVENTOS`.
Sustituye el aviso del 26-sep, que daba 66 % de breach --- hoy es 32 %, tras
mover FANTASMA fuera del muro geofísico.

Reparto de muros activos:

    5/5      0 ciclos   ( 0,0 %)   <- NUNCA ha ocurrido
    4/5     20          ( 0,3 %)
    3/5  2.200          (31,8 %)   -> el breach (>=3) dispara el 32,1 %
    2/5  1.692          (24,5 %)
    1/5  2.543          (36,8 %)
    0/5    460          ( 6,7 %)

Cuánto se enciende cada muro, que es donde está el defecto:

    geofisico    82,4 %      <- SEISMIC_CLUSTER dispara el 81,8 % de los ciclos
    solar        66,7 %      <- SILENT_TRIGGER el 55,4 %: dispara PORQUE hay calma
    oceanico     27,9 %      <- TSUNAMI el 27,9 %; no puede estar midiendo tsunamis
    atmosferico   5,2 %
    financiero    0,0 %      <- MUERTO: no se ha encendido ni una vez

Con dos muros encendidos tres cuartas partes del tiempo, la premisa de arriba
---«dominios físicos distintos alterados a la vez casi nunca es coincidencia»---
queda vacía. Y con el muro financiero muerto, exigir 5/5 no es un umbral
estricto: es un instrumento **permanentemente mudo**. 4/5 son 20 ciclos, n
insuficiente para calibrar nada.

LO QUE SÍ DISCRIMINA, y por qué parecía que no. Medido contra «¿hay un sismo
M>=4.5 en el planeta en las próximas 72 h?», la ganancia de Molchan sale 1,00x
en TODOS los umbrales --- pero no porque el muro no sepa nada, sino porque ese
blanco es cierto el **99,6 %** del tiempo. La vara estaba rota antes que el
umbral. Con un blanco alcanzable:

    BLANCO M>=6.0 en 24 h   (tasa base 0,238, 31 sismos)
      >=1   dispara 93,3 %   ganancia 0,92x   peor que el azar
      >=2   dispara 56,6 %   ganancia 1,29x
      >=3   dispara 32,1 %   ganancia **1,93x**   <- el optimo medido
      >=4   dispara  0,3 %   ganancia 1,47x   (n=20, no fiable)

    BLANCO M>=6.0 en 48 h: >=3 da 1,54x · BLANCO M>=5.5 en 24 h: >=3 da 1,37x

Así que **el umbral de 3 es el óptimo medido** y no se toca; lo que hay que
arreglar son los detectores y la vara con la que se reporta.

LOS PESOS SON DECORATIVOS. `correlation_score` se reduce algebraicamente a
`weighted_sum / total_walls` --- el `walls_active` se cancela --- y las
confianzas son constantes fijas por tipo (0,95 / 0,9 / 0,7): banderas, no
medidas. Medido: su mejor cuartil da 1,89x contra el 1,93x del simple conteo de
muros. No aporta información; sugiere una precisión que no existe.

PENDIENTE, en orden de daño: (1) el muro FINANCIERO muerto, (2) SEISMIC_CLUSTER
y SILENT_TRIGGER siempre encendidos, (3) TSUNAMI al 27,9 %, (4) decidir si los
pesos se hacen reales o se retiran.

Legacy: TITAN V32 only had walls 1+4. V53 added atmospheric. Sentinel Omega
completes the picture with oceanic and financial correlation.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sentinel_omega.core.precursor.precursor_types import PrecursorType

logger = logging.getLogger(__name__)


WALL_GEOFISICO = "GEOFÍSICO"
WALL_ATMOSFERICO = "ATMOSFÉRICO"
WALL_OCEANICO = "OCEÁNICO"
WALL_SOLAR = "SOLAR/GEOMAGNÉTICO"
WALL_FINANCIERO = "FINANCIERO/SOCIAL"

# FANTASMA estuvo en el muro GEOFÍSICO hasta el 2026-09-26, y no pertenece ahí:
# el índice se calcula con Bz, viento solar y Schumann --- clima espacial puro.
# Medido antes de moverlo: de 114 ciclos con el muro geofísico activo, **46
# (40 %) lo tenían activo SOLO por FANTASMA**. O sea que dos de cada cinco veces
# que el sistema informaba «dominio geofísico alterado», lo que estaba alterado
# era el Sol.
#
# Eso vacía la premisa del Muro, que es su razón de existir: «si 3 o más se
# activan a la vez, distintos dominios físicos están alterados al mismo tiempo
# --- eso casi nunca es coincidencia». Con una señal solar contando como
# geofísica, una sola causa podía encender dos frentes.
#
# El recuento de muros apenas cambia (medido: 0 ciclos tenían FANTASMA y otra
# señal solar a la vez, así que el muro SOLAR se activa donde antes se activaba
# el geofísico). Lo que cambia es que el dominio que se nombra es el correcto.
WALL_MEMBERS = {
    WALL_GEOFISICO: {
        PrecursorType.SEISMIC_CLUSTER,
        PrecursorType.VOLCANICO,
    },
    WALL_ATMOSFERICO: {
        PrecursorType.BLUE_JET,
        PrecursorType.SPRITE_ROJO,
        PrecursorType.NIEBLA_TULE,
    },
    WALL_OCEANICO: {
        PrecursorType.TSUNAMI,
        PrecursorType.HURACAN,
    },
    WALL_SOLAR: {
        PrecursorType.TORMENTA_SOLAR,
        PrecursorType.PERTURBACION_GEOMAGNETICA,
        PrecursorType.SCHUMANN,
        PrecursorType.SILENT_TRIGGER,
        PrecursorType.GRB,
        PrecursorType.FANTASMA,   # movido del geofísico: es clima espacial
    },
    WALL_FINANCIERO: {
        PrecursorType.CORRELACION_FINANCIERA,
    },
}


@dataclass
class WallStatus:
    name: str
    active: bool
    precursor_count: int
    max_confidence: float
    active_types: List[str] = field(default_factory=list)


@dataclass
class MuroResult:
    timestamp: float
    walls_active: int
    total_walls: int
    correlation_score: float
    muro_breach: bool
    wall_statuses: List[WallStatus] = field(default_factory=list)
    active_precursor_types: List[str] = field(default_factory=list)

    @property
    def risk_label(self) -> str:
        if self.walls_active >= 4:
            return "CRÍTICO"
        if self.walls_active >= 3:
            return "ALTO"
        if self.walls_active >= 2:
            return "MODERADO"
        if self.walls_active >= 1:
            return "BAJO"
        return "NORMAL"


class MuroCincoEventos:

    def __init__(
        self,
        min_walls_for_breach: int = 3,
        db_path: Optional[str] = None,
        clase_vivo: str = "SISMO_M6",
    ):
        # Fallback fijo si la tabla no da numero. El vivo lo relee
        # en cada evaluate; no se congela al arrancar.
        self.min_walls_for_breach = min_walls_for_breach
        self.db_path = db_path
        self.clase_vivo = clase_vivo
        self.senales_breach: Optional[tuple] = None
        self.last_umbral_fuente: str = "fallback"
        self.last_result: Optional[MuroResult] = None

    def evaluate(self, detections: list) -> MuroResult:
        """Evaluate all five walls against current precursor detections."""
        umbral = self.min_walls_for_breach
        senales = None
        if self.db_path:
            _uv = cargar_umbral_vivo(
                self.db_path,
                clase=self.clase_vivo,
                fallback=self.min_walls_for_breach,
            )
            umbral = int(_uv["umbral"])
            senales = _uv.get("senales")
            self.last_umbral_fuente = str(_uv.get("fuente") or "fallback")
            self.senales_breach = senales
        detection_types: Dict[PrecursorType, float] = {}
        for d in detections:
            tipo = d.tipo
            conf = d.confidence
            if tipo not in detection_types or conf > detection_types[tipo]:
                detection_types[tipo] = conf

        wall_statuses = []
        walls_active = 0
        weighted_sum = 0.0

        for wall_name, members in WALL_MEMBERS.items():
            active_in_wall = {
                t: detection_types[t]
                for t in members
                if t in detection_types
            }

            is_active = len(active_in_wall) > 0
            max_conf = max(active_in_wall.values()) if active_in_wall else 0.0

            if is_active:
                walls_active += 1
                weighted_sum += max_conf

            wall_statuses.append(WallStatus(
                name=wall_name,
                active=is_active,
                precursor_count=len(active_in_wall),
                max_confidence=max_conf,
                active_types=[t.value for t in active_in_wall.keys()],
            ))

        total_walls = len(WALL_MEMBERS)
        correlation_score = 0.0
        if walls_active > 0:
            correlation_score = (walls_active / total_walls) * (weighted_sum / walls_active)

        if senales:
            activas = {ws.name for ws in wall_statuses if ws.active}
            conteo = sum(1 for s in senales if s in activas)
            muro_breach = conteo >= umbral
        else:
            muro_breach = walls_active >= umbral

        result = MuroResult(
            timestamp=time.time(),
            walls_active=walls_active,
            total_walls=total_walls,
            correlation_score=correlation_score,
            muro_breach=muro_breach,
            wall_statuses=wall_statuses,
            active_precursor_types=[t.value for t in detection_types.keys()],
        )
        self.last_result = result

        if muro_breach:
            logger.warning(
                f"MURO BREACH: {walls_active}/{total_walls} walls active "
                f"(score={correlation_score:.2f}, risk={result.risk_label})"
            )
        else:
            logger.info(
                f"Muro: {walls_active}/{total_walls} walls "
                f"(score={correlation_score:.2f})"
            )

        return result


def format_muro_report(result: MuroResult) -> str:
    """Format Muro result as HTML for Telegram dispatch."""
    status_icon = "🔴" if result.muro_breach else "🟢"

    lines = [
        f"<b>SENTINEL OMEGA — MURO DE LOS 5 EVENTOS</b>",
        f"",
        f"<b>Estado:</b> {status_icon} {result.risk_label}",
        f"<b>Muros activos:</b> {result.walls_active}/{result.total_walls}",
        f"<b>Correlación:</b> <code>{result.correlation_score:.2f}</code>",
        f"",
    ]

    for ws in result.wall_statuses:
        mark = "✅" if ws.active else "⬜"
        conf_str = f" ({ws.max_confidence:.0%})" if ws.active else ""
        lines.append(f"{mark} <b>{ws.name}</b>{conf_str}")
        if ws.active_types:
            types_str = ", ".join(ws.active_types)
            lines.append(f"    → {types_str}")

    if result.muro_breach:
        lines.append(f"")
        lines.append(f"<b>⚠️ ALERTA: Correlación multi-dominio detectada</b>")

    return "\n".join(lines)


# Entrenamiento aparte por magnitud (2026-10-04).
# El 2.5 es gatillo, no blanco. El blanco empieza en la prediccion, 4.5.
# Lo que precede a un 4.5 no entra como acierto del muro de un 6.
# Cada senal se juzga sola. Entra al muro de una magnitud solo si esta
# encendida mas a menudo antes de esa magnitud que antes de las otras.
# Si esta encendida para todas, no cuenta para esa clase. No se borra:
# la misma senal se vuelve a juzgar para cada magnitud.
# Geofisico y solar pasan por el mismo corte. No hay excepcion por nombre.
# Si una clase no tiene con que aprender, el umbral queda None: no se copia el 3.

CLASES_BLANCO_MURO = ("SISMO_M4", "SISMO_M5", "SISMO_M6", "SISMO_M7")
SENALES_MURO = tuple(WALL_MEMBERS)


def cargar_umbral_vivo(
    db_path: str,
    clase: str = "SISMO_M6",
    fallback: int = 3,
) -> Dict[str, Any]:
    """Lee el umbral guardado para el vivo.

    Blanco del vivo: SISMO_M6 (alerta). Si la fila no existe, umbral es
    NULL, o senales vacias, se queda el fallback (hoy 3) sin senales.
    No inventa numeros. Abre en solo lectura: si la ruta falla, no crea
    un .db vacio.
    """
    import json
    import sqlite3

    out: Dict[str, Any] = {
        "clase": clase,
        "umbral": fallback,
        "senales": None,
        "fuente": "fallback",
    }
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT umbral, senales FROM tbl_muro_umbral_magnitud WHERE clase = ?",
                (clase,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return out
    if not row:
        return out
    umbral, senales_json = row
    if umbral is None:
        return out
    try:
        senales = tuple(json.loads(senales_json or "[]"))
    except Exception:
        return out
    if not senales:
        return out
    out["umbral"] = int(umbral)
    out["senales"] = senales
    out["fuente"] = "tabla"
    return out


def clase_blanco_muro(mag: float) -> Optional[str]:
    """Clase que el muro puede aprender. Por debajo de 4.5 no hay blanco."""
    if mag is None or mag < 4.5:
        return None
    if mag >= 7.0:
        return "SISMO_M7"
    if mag >= 6.0:
        return "SISMO_M6"
    if mag >= 5.0:
        return "SISMO_M5"
    return "SISMO_M4"


def entrenar_umbral_por_magnitud(
    filas: List[tuple],
    min_positivos: int = 30,
) -> Dict[str, Dict[str, Any]]:
    """Senales y umbral de cada magnitud.

    Cada fila es (senales_activas, magnitud). senales_activas son nombres
    de muro. magnitud None es un ciclo sin sismo de blanco. Un sismo solo
    es acierto de SU clase.

    Una senal entra a la clase si su tasa delante de esa clase es mayor
    que su tasa delante de las otras clases con blanco. Empate, o
    encendida para todas, no entra. El umbral es el conteo de esas
    senales, de 1 hasta las que entraron, cuya ganancia supera al azar.
    Si dos conteos empatan, se queda el mas alto. Si ninguno supera, o
    no hay suficientes sismos, el umbral es None.
    """
    activas: List[Set[str]] = []
    etiquetas: List[Optional[str]] = []
    for senales, mag in filas:
        activas.append(set(senales))
        etiquetas.append(None if mag is None else clase_blanco_muro(float(mag)))
    n = len(etiquetas)
    out: Dict[str, Dict[str, Any]] = {}
    for clase in CLASES_BLANCO_MURO:
        idx = [i for i, et in enumerate(etiquetas) if et == clase]
        vacio = {"senales": (), "umbral": None}
        if n == 0 or len(idx) < min_positivos:
            out[clase] = vacio
            continue
        otras = [i for i, et in enumerate(etiquetas) if et is not None and et != clase]
        if not otras:
            out[clase] = vacio
            continue
        entran = []
        for senal in SENALES_MURO:
            tasa_clase = sum(senal in activas[i] for i in idx) / len(idx)
            tasa_otras = sum(senal in activas[i] for i in otras) / len(otras)
            if tasa_clase > tasa_otras:
                entran.append(senal)
        if not entran:
            out[clase] = vacio
            continue
        mejor_k: Optional[int] = None
        mejor_g = 1.0
        n_pos = len(idx)
        for k in range(1, len(entran) + 1):
            alarmas = 0
            aciertos = 0
            for i, encienden in enumerate(activas):
                if sum(s in encienden for s in entran) >= k:
                    alarmas += 1
                    if i in idx:
                        aciertos += 1
            if not alarmas:
                continue
            ganancia = (aciertos / n_pos) / (alarmas / n)
            if ganancia > mejor_g or (
                mejor_k is not None and ganancia == mejor_g and k > mejor_k
            ):
                mejor_g = ganancia
                mejor_k = k
        out[clase] = {"senales": tuple(entran), "umbral": mejor_k}
    return out


def filas_muros_antes_del_sismo(
    ciclos: List[tuple],
    sismos: List[tuple],
) -> List[tuple]:
    """Una fila por ciclo: los muros de ese ciclo y la magnitud posterior.

    El ciclo que cuenta es el ultimo con marca estrictamente anterior al
    sismo. El del mismo instante, o uno posterior, no entra. Si varios
    sismos caen sobre el mismo ciclo, se queda la magnitud mayor. Un ciclo
    sin sismo despues lleva magnitud None.
    """
    ordenados = sorted(ciclos, key=lambda fila: fila[0])
    eventos = sorted(sismos, key=lambda fila: fila[0])
    mejor: Dict[int, float] = {}
    j = 0
    n = len(ordenados)
    for ts, mag in eventos:
        while j + 1 < n and ordenados[j + 1][0] < ts:
            j += 1
        if n == 0 or ordenados[j][0] >= ts:
            continue
        previa = mejor.get(j)
        if previa is None or mag > previa:
            mejor[j] = float(mag)
    return [(senales, mejor.get(i)) for i, (_, senales) in enumerate(ordenados)]
