#!/usr/bin/env python3
"""
Sentinel Omega — Launcher
Starts the orchestrator in continuous cycle mode with graceful signal handling.

Usage:
    python -m sentinel_omega.launcher
    python sentinel_omega/launcher.py
    python sentinel_omega/launcher.py --once          # Single cycle, then exit
    python sentinel_omega/launcher.py --dashboard     # Launch dashboard alongside
    python sentinel_omega/launcher.py --dry-run       # No Telegram alerts
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Ensure the workspace root is importable when run as a script
# (python sentinel_omega/launcher.py), not just as a module.
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

PIDFILE = Path(__file__).parent / "data" / "sentinel_omega.pid"
LOGFILE = Path(__file__).parent / "data" / "sentinel_omega.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LAUNCHER] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGFILE, mode="a"),
    ],
)
logger = logging.getLogger(__name__)

_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name} — initiating graceful shutdown...")
    _shutdown_requested = True


def _write_pid():
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))
    logger.info(f"PID {os.getpid()} written to {PIDFILE}")


def _clear_pid():
    if PIDFILE.exists():
        PIDFILE.unlink()


def _check_already_running() -> bool:
    if not PIDFILE.exists():
        return False
    try:
        pid = int(PIDFILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        _clear_pid()
        return False


def _launch_dashboard() -> subprocess.Popen:
    dashboard_path = Path(__file__).parent / "infrastructure" / "dashboard" / "app.py"
    logger.info(f"Launching dashboard: {dashboard_path}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_path),
         "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info(f"Dashboard PID: {proc.pid}")
    return proc


def _print_banner(config):
    print()
    print("=" * 60)
    print(f"  SENTINEL OMEGA v{config.version}")
    print(f"  Precursor Detection Platform")
    print(f"  Author: {config.author}")
    print("=" * 60)
    print(f"  PID:        {os.getpid()}")
    print(f"  Location:   {config.coordinates.get('location', '—')}")
    active = [k for k, v in config.layers.items() if v.enabled]
    print(f"  Layers:     {', '.join(active)}")
    print(f"  Telegram:   {'ON' if config.telegram.enabled else 'OFF (dry run)'}")
    print(f"  Log:        {LOGFILE}")
    print("=" * 60)
    print()


def run(args):
    global _shutdown_requested

    if _check_already_running():
        logger.error("Sentinel Omega is already running. Use shutdown.py first.")
        sys.exit(1)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    from sentinel_omega.config.sentinel_config import SentinelOmegaConfig
    from sentinel_omega.orchestrator import SentinelOrchestrator
    from sentinel_omega.infrastructure.database.schema import init_database, get_connection
    from sentinel_omega.infrastructure.database.repository import SentinelRepository
    from sentinel_omega.infrastructure.database.seed_nodos import seed_topology

    config = SentinelOmegaConfig()

    if args.dry_run:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        config = SentinelOmegaConfig()

    _print_banner(config)
    _write_pid()

    logger.info("Initializing database...")
    db_path = Path(__file__).parent / config.databases.geodynamic_db
    init_database(str(db_path))

    repo = SentinelRepository(str(db_path))
    existing_nodes = repo.get_nodos()
    if not existing_nodes:
        logger.info("Seeding 125 topology nodes...")
        seed_topology(repo)
        logger.info("Topology seeded.")

    if args.backcast:
        from sentinel_omega.infrastructure.pipeline.backcast import run_backcast
        logger.info("Running historical backcast (one-time)...")
        run_backcast(str(db_path))
        logger.info("Backcast complete.")

    if args.entrenar:
        from sentinel_omega.infrastructure.pipeline.entrenamiento import entrenar
        logger.info("Running signature training (Fase 1 + Fase 2)...")
        resultado = entrenar(str(db_path))
        logger.info(f"Training complete: {resultado}")

    dashboard_proc = None
    if args.dashboard:
        dashboard_proc = _launch_dashboard()

    logger.info("Creating orchestrator with live pipelines...")
    orch = SentinelOrchestrator.create_with_live_pipelines(config)

    try:
        from sentinel_omega.core.juez.pesos import cargar_pesos
        pesos = cargar_pesos(repo._conn)
        if pesos and orch._runner is not None:
            orch._runner.padre.set_pesos(pesos)
            logger.info(f"Pesos disciplinarios cargados: {pesos}")
    except Exception as e:
        logger.warning(f"Could not load bot weights: {e}")

    cycle_interval = config.layers.get("geodynamic", config.layers["geodynamic"]).refresh_interval_s
    logger.info(f"Cycle interval: {cycle_interval}s")
    logger.info("Sentinel Omega ONLINE.")

    try:
        while not _shutdown_requested:
            cycle_start = time.time()

            try:
                logger.info(f"--- Starting cycle #{orch.get_status().cycle_count + 1} ---")
                results = orch.run_cycle()
                status = orch.get_status()

                _log_cycle_summary(status, results, repo, config, runner=orch._runner)

            except Exception as e:
                logger.error(f"Cycle failed: {e}", exc_info=True)

            if args.once:
                logger.info("--once flag: exiting after single cycle.")
                break

            elapsed = time.time() - cycle_start
            sleep_time = max(0, cycle_interval - elapsed)
            if sleep_time > 0 and not _shutdown_requested:
                logger.info(f"Next cycle in {sleep_time:.0f}s...")
                _interruptible_sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")

    finally:
        logger.info("Shutting down...")
        if dashboard_proc:
            logger.info(f"Terminating dashboard (PID {dashboard_proc.pid})...")
            dashboard_proc.terminate()
            dashboard_proc.wait(timeout=10)
        _clear_pid()
        logger.info("Sentinel Omega OFFLINE.")


def _interruptible_sleep(seconds: float):
    end = time.time() + seconds
    while time.time() < end and not _shutdown_requested:
        time.sleep(min(1.0, end - time.time()))


def _log_cycle_summary(status, results, repo, config, runner=None):
    risk = status.last_precursor_risk
    if risk:
        logger.info(
            f"Fantasma: {risk.fantasma:.2f} ({risk.risk_level}) | "
            f"Precursors: {len(status.active_precursors)} | "
            f"Alerts dispatched: {status.alerts_dispatched} | "
            f"Uptime: {status.uptime_s:.0f}s"
        )

        try:
            repo.insert_precursor_cosmico(
                bz=risk.components.get("bz_nT", 0),
                viento=risk.components.get("wind_kms", 0),
                protones=0.0,
                kp=risk.components.get("kp", 0),
                lod_ms=risk.components.get("lod_ms", 0),
                schumann_hz=7.83,
                schumann_activity=risk.components.get("schumann_wpc", 0) * 100,
                presion_hpa=risk.components.get("pressure_hpa", 1013),
                fantasma=risk.fantasma,
                nivel_riesgo=risk.risk_level,
                fase_lunar=0.0,
            )
        except Exception as e:
            logger.warning(f"Failed to persist cycle data: {e}")

        muro = status.last_muro
        walls_active = muro.walls_active if muro else 0
        muro_breach = muro.muro_breach if muro else False

        geo = results.get("geodynamic")
        if geo:
            try:
                cycle_id = repo.insert_ciclo(
                    geo_signal=geo.final_signal.value,
                    geo_confidence=geo.confidence,
                    geo_consensus=geo.consensus_reached,
                    fantasma=risk.fantasma,
                    nivel_riesgo=risk.risk_level,
                    precursors_count=len(status.active_precursors),
                    precursor_types=status.active_precursors,
                    muro_walls_active=walls_active,
                    muro_breach=muro_breach,
                    alerts_dispatched=status.alerts_dispatched,
                )
            except Exception as e:
                logger.warning(f"Failed to persist cycle record: {e}")
                cycle_id = None

            if muro:
                try:
                    wall_states = {ws.name: ws.active for ws in muro.wall_statuses}
                    repo.insert_muro_evento(
                        walls_active=muro.walls_active,
                        correlation_score=muro.correlation_score,
                        muro_breach=muro.muro_breach,
                        risk_label=muro.risk_label,
                        wall_states=wall_states,
                        active_types=muro.active_precursor_types,
                        cycle_id=cycle_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist muro record: {e}")

            detections = getattr(geo, "precursor_detections", None) or []
            for det in detections:
                try:
                    repo.insert_deteccion(
                        tipo=det.tipo.value,
                        display_name=det.display_name,
                        confidence=det.confidence,
                        station=det.station,
                        lat=det.lat,
                        lon=det.lon,
                        values=det.values,
                        cycle_id=cycle_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist detection: {e}")

            _auditar_ciclo(geo, repo, runner)


def _build_live_features(runner) -> dict:
    """Approximate the firma feature vector from the live pipeline cache."""
    import numpy as np

    features = {}
    if runner is None or not hasattr(runner, "pipeline"):
        return features
    cache = getattr(runner.pipeline, "_cache", {})

    alfa1 = cache.get("alfa1") or {}
    omni = alfa1.get("omni_dataframe")
    if omni is not None:
        if "bz_gsm" in omni.columns:
            bz = omni["bz_gsm"].dropna()
            if len(bz) > 0:
                features["bz_mean"] = float(bz.mean())
                features["bz_min"] = float(bz.min())
        if "plasma_speed" in omni.columns:
            wind = omni["plasma_speed"].dropna()
            if len(wind) > 0:
                features["viento_avg"] = float(wind.mean())
                features["viento_max"] = float(wind.max())

    beta1 = cache.get("beta1") or {}
    kp = beta1.get("kp_series")
    if kp is not None and len(kp) > 0:
        features["kp_mean"] = float(np.nanmean(kp))
        features["kp_max"] = float(np.nanmax(kp))
    if "schumann_frequency" in beta1:
        features["schumann_mean"] = float(beta1["schumann_frequency"])
    mags = beta1.get("seismic_magnitudes")
    if mags is not None and len(mags) > 0:
        features["sismo_count_win"] = float(len(mags))
        features["sismo_max_mag_win"] = float(np.nanmax(mags))
    lunar = beta1.get("lunar_phase")
    if lunar is not None and len(lunar) > 0:
        features["fase_lunar"] = float(lunar[-1])

    delta = cache.get("delta") or {}
    for key in ("btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h"):
        if key in delta:
            features[key] = float(delta[key])

    return features


def _auditar_ciclo(geo, repo, runner) -> None:
    """Firma matching + Juez registration/resolution for this cycle."""
    try:
        from sentinel_omega.core.firmas.signature_engine import FirmaMemoria
        from sentinel_omega.core.juez.juez import Juez

        conn = repo._conn
        memoria = FirmaMemoria(conn)
        juez = Juez(conn)

        matches = []
        features = _build_live_features(runner)
        if features:
            matches = memoria.match_estado_actual(features)
            for m in matches[:3]:
                logger.warning(
                    f"FIRMA MATCH: estado actual se parece {m['similitud']:.0%} "
                    f"a la firma que precedió {m['event_class']} "
                    f"(nodo {m['id_nodo']}, vista {m['recurrencia']} veces)"
                )

        juez.registrar_prediccion(
            bot_name="padre",
            prediccion=geo.final_signal.value,
            confianza=geo.confidence,
            ventana_h=72,
            detalles={"firma_matches": matches[:5]},
        )

        # Resolve predictions whose 72h window closed, against USGS truth.
        from sentinel_omega.infrastructure.api.usgs import fetch_earthquakes
        eq = fetch_earthquakes(min_magnitude=5.0, days=4)
        evento_ocurrido = eq is not None and len(eq) > 0
        verdad = f"{len(eq)} eventos M5+ en 4 dias" if evento_ocurrido else "sin eventos M5+"
        resueltos = juez.evaluar_pendientes(
            evento_ocurrido=evento_ocurrido,
            verdad=verdad,
            firma_conocida=bool(matches),
        )
        if resueltos:
            logger.info(f"Juez resolvió {len(resueltos)} predicciones pendientes")
    except Exception as e:
        logger.warning(f"Audit step failed (non-blocking): {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sentinel Omega — Precursor Detection Platform Launcher",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single cycle and exit",
    )
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Also launch the Streamlit dashboard",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Disable Telegram alerts (dry run mode)",
    )
    parser.add_argument(
        "--backcast", action="store_true",
        help="Run historical backcast (1994-2025) before starting cycles",
    )
    parser.add_argument(
        "--entrenar", action="store_true",
        help="Run signature training over the backcast (Fase 1 + Fase 2)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
