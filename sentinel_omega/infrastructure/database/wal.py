"""Volcado del WAL: que el registro no se coma la base.

El 2026-09-25 el `-wal` de SENTINEL_OMEGA_PRO.db llegó a **999,8 MB**, más que
la base misma (888 MB). Dos consecuencias, y la segunda es la grave:

  1. Cada lector tiene que recorrer ese registro, y una recuperación tras un
     corte se vuelve lenta.
  2. **Una copia hecha con `cp` del .db NO incluye el WAL**: las dos que se
     hicieron esa tarde salieron sin la vista `viva_real` y sin los datos
     recientes. Eran respaldos que no servían para restaurar.

SQLite ya vuelca solo cuando un escritor encuentra el WAL por encima de ~1.000
páginas (unos 4 MB). Que llegara a 1 GB significa que ese volcado automático
**venía fallando**, y la causa casi siempre es la misma: un lector de larga vida
—el tablero, el bot— mantiene abierta una instantánea, y el volcado no puede
reclamar las páginas que ese lector todavía podría necesitar.

No hay disparador por tamaño en SQLite: esto es una comprobación que corre con
el ciclo (barata: mirar el tamaño de un archivo) y fuerza el volcado cuando hace
falta. El modo TRUNCATE es literalmente «parar la entrada/salida»: bloquea a los
escritores y espera a que los lectores suelten. Si alguno no suelta, el volcado
devuelve «bloqueado» y NO se queda esperando para siempre --- se informa y se
reintenta en el siguiente ciclo, porque colgar el ciclo por limpiar el registro
sería peor que el problema.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Por debajo de esto no se toca nada: el WAL es sano y útil, evita reescribir
# la base en cada transacción.
UMBRAL_MB = 800.0
ESPERA_S = 30.0


def tamano_wal_mb(db_path: str) -> float:
    """Tamaño del `-wal` en MB. 0.0 si no existe (base sin WAL o ya volcado)."""
    try:
        return os.path.getsize(f"{db_path}-wal") / (1024 * 1024)
    except OSError:
        return 0.0


def procesos_con_la_base(db_path: str) -> List[str]:
    """Quién tiene la base abierta, para saber QUIÉN bloquea el volcado.

    Best-effort sobre /proc: sin esto, un volcado bloqueado no dice nada y hay
    que salir a buscar a ciegas.
    """
    fuera: List[str] = []
    objetivo = os.path.basename(db_path)
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return fuera
    for pid in pids:
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                destino = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if objetivo in destino:
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
                except OSError:
                    cmd = "?"
                fuera.append(f"{pid}: {cmd.strip()[:90]}")
                break
    return fuera


def volcar_wal(
    db_path: str,
    modo: str = "TRUNCATE",
    espera_s: float = ESPERA_S,
) -> Dict[str, Any]:
    """Vuelca el WAL a la base. Devuelve qué pasó, sin lanzar excepciones.

    `modo`: PASSIVE no molesta a nadie pero puede no reclamar nada; TRUNCATE
    bloquea escritores y espera lectores, y deja el archivo en cero.
    """
    antes = tamano_wal_mb(db_path)
    salida: Dict[str, Any] = {
        "antes_mb": round(antes, 1), "despues_mb": round(antes, 1),
        "modo": modo, "bloqueado": None, "ok": False,
    }
    if modo.upper() not in ("PASSIVE", "FULL", "RESTART", "TRUNCATE"):
        salida["error"] = f"modo inválido: {modo}"
        return salida
    try:
        conn = sqlite3.connect(db_path, timeout=espera_s)
        try:
            fila = conn.execute(f"PRAGMA wal_checkpoint({modo.upper()})").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as e:
        salida["error"] = f"{type(e).__name__}: {e}"
        logger.warning("Volcado del WAL falló: %s", salida["error"])
        return salida
    # (bloqueado, páginas_en_wal, páginas_volcadas): el primero es 1 cuando no
    # se pudo completar porque alguien tenía la base tomada.
    salida["bloqueado"] = bool(fila[0]) if fila else None
    salida["despues_mb"] = round(tamano_wal_mb(db_path), 1)
    salida["ok"] = not salida["bloqueado"]
    return salida


def volcar_si_crece(
    db_path: str,
    umbral_mb: float = UMBRAL_MB,
    espera_s: float = ESPERA_S,
) -> Optional[Dict[str, Any]]:
    """El disparador: vuelca solo si el WAL pasó del umbral. None si no tocaba.

    Mirar el tamaño de un archivo cuesta microsegundos, así que puede correr en
    cada ciclo. Primero PASSIVE, que no molesta a nadie; si eso no baja el WAL,
    TRUNCATE, que sí para la entrada/salida.
    """
    tam = tamano_wal_mb(db_path)
    if tam < umbral_mb:
        return None
    logger.warning(
        "WAL en %.0f MB (umbral %.0f): volcando a la base", tam, umbral_mb)
    salida = volcar_wal(db_path, modo="PASSIVE", espera_s=espera_s)
    if salida["despues_mb"] >= umbral_mb:
        logger.info("PASSIVE no reclamó lo suficiente (%.0f MB): se fuerza TRUNCATE",
                    salida["despues_mb"])
        salida = volcar_wal(db_path, modo="TRUNCATE", espera_s=espera_s)
    salida["umbral_mb"] = umbral_mb
    if salida.get("bloqueado"):
        # Quién lo impide: casi siempre un lector de larga vida con una
        # instantánea abierta. Decirlo ahorra la búsqueda a ciegas.
        salida["procesos"] = procesos_con_la_base(db_path)
        logger.warning(
            "Volcado BLOQUEADO: alguien mantiene la base tomada. Con ella "
            "abierta: %s", "; ".join(salida["procesos"]) or "(no se pudo mirar)")
    else:
        logger.info("WAL volcado: %.0f MB -> %.0f MB",
                    salida["antes_mb"], salida["despues_mb"])
    return salida
