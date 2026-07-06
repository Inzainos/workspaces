"""
Scheduler de Reportes — Sentinel Omega
=======================================
Ejecuta los tres reportes en bucle con sus cadencias:

  reporte_general  →  cada  2 horas  (visión global de todos los bots)
  reporte_padre    →  cada  6 horas  (análisis profundo del Padre)
  reporte_omega    →  cada  6 horas  (análisis profundo de Omega, independiente)

Se inicia desde el vigilante o directamente:
    python sentinel_omega/launcher.py --reportes

Dentro del bucle principal del vigilante:
    scheduler = ReporteScheduler(db_path)
    scheduler.tick()   # llamar en cada ciclo (~2h)
"""

import logging
import time as _time
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Cadencias en segundos
CADENCIA_GENERAL = 2 * 3600   # 2 horas
CADENCIA_PADRE   = 6 * 3600   # 6 horas
CADENCIA_OMEGA   = 6 * 3600   # 6 horas


class ReporteScheduler:
    """
    Scheduler de tres reportes con cadencias independientes.

    Uso dentro del vigilante:

        scheduler = ReporteScheduler(db_path)
        while True:
            ciclo_principal()
            scheduler.tick()  # ← llama los reportes que toquen

    Uso standalone (bucle propio, bloquea):

        ReporteScheduler(db_path).run_forever()
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._last: Dict[str, float] = {
            "general": 0.0,
            "padre":   0.0,
            "omega":   0.0,
        }
        self._cadencias: Dict[str, float] = {
            "general": CADENCIA_GENERAL,
            "padre":   CADENCIA_PADRE,
            "omega":   CADENCIA_OMEGA,
        }

    # ── helpers ──────────────────────────────────────────────────────────────

    def _due(self, nombre: str) -> bool:
        """Devuelve True si ya pasó la cadencia desde la última ejecución."""
        return (_time.monotonic() - self._last[nombre]) >= self._cadencias[nombre]

    def _run(self, nombre: str, fn: Callable) -> Optional[Dict]:
        """Ejecuta el reporte capturando errores para que nunca interrumpa el bucle."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        logger.info(f"[scheduler] {nombre.upper()} iniciando — {ts}")
        try:
            result = fn(self.db_path)
            self._last[nombre] = _time.monotonic()
            logger.info(f"[scheduler] {nombre.upper()} completado.")
            return result
        except Exception as exc:
            logger.exception(f"[scheduler] {nombre.upper()} falló: {exc}")
            # Actualiza el timer igual para no reintentar en el siguiente ciclo
            self._last[nombre] = _time.monotonic()
            return None

    # ── API pública ──────────────────────────────────────────────────────────

    def tick(self) -> Dict[str, bool]:
        """
        Llama los reportes que correspondan según la cadencia.
        Diseñado para ser invocado en cada ciclo del vigilante (~2h).
        Devuelve qué reportes se ejecutaron.
        """
        from sentinel_omega.infrastructure.pipeline.reporte_sentinel import (
            reporte_general, reporte_padre, reporte_omega,
        )
        ejecutados = {"general": False, "padre": False, "omega": False}

        if self._due("general"):
            self._run("general", reporte_general)
            ejecutados["general"] = True

        if self._due("padre"):
            self._run("padre", reporte_padre)
            ejecutados["padre"] = True

        if self._due("omega"):
            self._run("omega", reporte_omega)
            ejecutados["omega"] = True

        return ejecutados

    def force_all(self) -> None:
        """Fuerza la ejecución inmediata de los tres reportes."""
        from sentinel_omega.infrastructure.pipeline.reporte_sentinel import (
            reporte_general, reporte_padre, reporte_omega,
        )
        logger.info("[scheduler] Ejecución forzada de todos los reportes.")
        self._run("general", reporte_general)
        self._run("padre", reporte_padre)
        self._run("omega", reporte_omega)

    def run_forever(self, sleep_s: int = 60) -> None:
        """
        Bucle autónomo (standalone). Revisa cada `sleep_s` segundos si toca
        ejecutar algún reporte. Útil para correr el scheduler como proceso
        separado sin el vigilante.

        Lanzar desde launcher.py con:
            python sentinel_omega/launcher.py --reportes
        """
        logger.info(
            f"[scheduler] Iniciando bucle autónomo. "
            f"General: {CADENCIA_GENERAL//3600}h  "
            f"Padre: {CADENCIA_PADRE//3600}h  "
            f"Omega: {CADENCIA_OMEGA//3600}h"
        )
        # Primer reporte inmediato al arrancar
        self.force_all()
        while True:
            _time.sleep(sleep_s)
            self.tick()


# ──────────────────────────────────────────────────────────────────────────────
# Punto de entrada standalone
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from sentinel_omega.core.config import DB_PATH  # type: ignore

    parser = argparse.ArgumentParser(description="Scheduler de reportes Sentinel Omega")
    parser.add_argument("--db", default=DB_PATH, help="Ruta a la base de datos SQLite")
    parser.add_argument("--force", action="store_true", help="Ejecutar los tres reportes una vez y salir")
    parser.add_argument("--sleep", type=int, default=60, help="Segundos entre tick() (modo bucle)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
    sched = ReporteScheduler(args.db)

    if args.force:
        sched.force_all()
    else:
        sched.run_forever(sleep_s=args.sleep)
