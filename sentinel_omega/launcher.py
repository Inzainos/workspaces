#!/usr/bin/env python3
"""
Sentinel Omega — Launcher
Starts the orchestrator in continuous cycle mode with graceful signal handling.

Usage:
    python -m sentinel_omega.launcher
    python sentinel_omega/launcher.py
    python sentinel_omega/launcher.py --once          # Single cycle, then exit
    python sentinel_omega/launcher.py --dashboard     # Launch dashboard alongside
    python sentinel_omega/launcher.py --dry-run       # No Telegram + no writes in batch tasks
    python sentinel_omega/launcher.py --entrenar --reporte  # Train then report
    python sentinel_omega/launcher.py --reporte       # Report only (no training)
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime as _dt, timezone as _tz
from pathlib import Path

# Ensure the workspace root is importable when run as a script
# (python sentinel_omega/launcher.py), not just as a module.
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

PIDFILE = Path(__file__).parent / "data" / "sentinel_omega.pid"
LOGFILE = Path(__file__).parent / "data" / "sentinel_omega.log"
# data/ está en .gitignore: en un checkout limpio (GitHub Actions) no existe
LOGFILE.parent.mkdir(parents=True, exist_ok=True)

_LOG_MAX_BYTES = int(os.environ.get("SENTINEL_LOG_MAX_BYTES", str(50 * 1024 * 1024)))
_LOG_BACKUP_COUNT = int(os.environ.get("SENTINEL_LOG_BACKUP_COUNT", "5"))

# El handler de archivo se construye AL IMPORTAR, así que si el log no es
# escribible el `import launcher` reventaba con PermissionError --- y con él
# cualquier prueba, herramienta o invocación manual que importe este módulo.
#
# Medido el 2026-09-27: el servicio corre como root (`User=` vacío en una unidad
# de sistema), y cuando el log ROTÓ, root creó el archivo nuevo. Desde ese
# instante el usuario del repo no podía escribirlo, y tres pruebas que habían
# pasado una hora antes empezaron a fallar sin que el código cambiara. Se repite
# en cada rotación mientras el servicio sea root.
#
# Abrir un archivo por el mero hecho de importar un módulo es el defecto de
# fondo, y se arregla donde está: si el archivo no se puede abrir se sigue con
# stdout --- que es lo que systemd captura en el journal (`StandardOutput=journal`)
# --- y se avisa. Es la misma disciplina fail-soft del resto del pipeline: un
# log que no se puede escribir no es motivo para que el sistema no arranque.
_handlers = [logging.StreamHandler(sys.stdout)]
_aviso_log = None
try:
    _handlers.append(
        RotatingFileHandler(
            LOGFILE,
            mode="a",
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    )
except OSError as _e:      # permisos, disco lleno, ruta inaccesible
    _aviso_log = (
        f"No se pudo abrir {LOGFILE} ({_e}); se registra solo en stdout. "
        "Si el servicio corre como root y tú no, es el dueño del archivo."
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LAUNCHER] %(levelname)s %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)
if _aviso_log:
    logger.warning(_aviso_log)
logger.info(
    "Log rotation enabled (maxBytes=%s, backupCount=%s)",
    _LOG_MAX_BYTES,
    _LOG_BACKUP_COUNT,
)

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
    try:
        if PIDFILE.exists():
            PIDFILE.unlink()
    except OSError:
        pass


def _check_already_running() -> bool:
    if not PIDFILE.exists():
        return False
    try:
        pid = int(PIDFILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Proceso existe pero pertenece a otro usuario (root) -> sí está corriendo
        return True
    except (ProcessLookupError, ValueError, OSError):
        try:
            _clear_pid()
        except OSError:
            pass
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


def _run_reportes(db_path: str) -> None:
    """
    Genera el reporte general y el reporte del Padre en stdout.
    Guarda también ambos reportes en data/reporte_<timestamp>.txt
    para revisión posterior.

    Se invoca automáticamente después de --entrenar si se pasa --reporte,
    o de forma independiente con solo --reporte.
    """
    from sentinel_omega.infrastructure.pipeline.reporte_sentinel import (
        reporte_general,
        reporte_padre,
    )

    ts = _dt.now(_tz.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(db_path).parent
    general_path = out_dir / f"reporte_general_{ts}.txt"
    padre_path = out_dir / f"reporte_padre_{ts}.txt"

    # ── Reporte General ──────────────────────────────────────────────────────
    logger.info("Generando reporte general...")
    try:
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reporte_general(db_path)
        texto_general = buf.getvalue()
        print(texto_general)
        general_path.write_text(texto_general, encoding="utf-8")
        logger.info(f"Reporte general guardado en: {general_path}")
    except Exception as e:
        logger.error(f"reporte_general() falló: {e}", exc_info=True)

    # ── Reporte del Padre ────────────────────────────────────────────────────
    logger.info("Generando reporte del Padre...")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reporte_padre(db_path)
        texto_padre = buf.getvalue()
        print(texto_padre)
        padre_path.write_text(texto_padre, encoding="utf-8")
        logger.info(f"Reporte del Padre guardado en: {padre_path}")
    except Exception as e:
        logger.error(f"reporte_padre() falló: {e}", exc_info=True)


def run(args):
    global _shutdown_requested

    # ── Modo TAREA: corre su trabajo y sale. No compite con el ciclo vivo ────
    #
    # Medido el 2026-09-28: `sentinel-omega-mantenimiento.service` llevaba
    # fallando SIEMPRE con «Sentinel Omega is already running» (exit 1), porque
    # el guardián de instancia única se aplicaba también a los flags de tarea ---
    # y el launcher está arriba por diseño, así que el barrido y la disciplina
    # diarios no corrían NUNCA. Se había atribuido a un timer duplicado; la
    # causa era ésta.
    #
    # El guardián existe para que no haya DOS ciclos de vigilancia, no para
    # impedir un lote. Y el lote tampoco debe tocar el pid: `_write_pid()` lo
    # pisaba con el suyo y `_clear_pid()` lo borraba al salir, dejando al
    # launcher vivo sin archivo de pid --- ciegos `shutdown.py` y el watchdog.
    # Por eso el modo tarea no escribe, no borra y no consulta el pid.
    tarea_batch = bool(
        (args.backcast or args.entrenar or args.disciplina
         or args.barrido or args.reporte) and not args.once
    )

    if not tarea_batch and _check_already_running():
        logger.error("Sentinel Omega is already running. Use shutdown.py first.")
        sys.exit(1)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # load_config() LEE sentinel.yaml; SentinelOmegaConfig() se queda con los
    # valores por defecto del código. Medido el 2026-09-25: el lanzador usaba el
    # segundo, así que el fichero de configuración era decorativo --- se encendió
    # juez.peso_por_merito en el yaml, se reinició, y el arranque siguió diciendo
    # «paseo multiplicativo». El yaml solo mezcla database, telegram y juez; los
    # demás bloques siguen sin leerse y habrá que ir conectándolos.
    from sentinel_omega.config.sentinel_config import SentinelOmegaConfig, load_config
    from sentinel_omega.orchestrator import SentinelOrchestrator
    from sentinel_omega.infrastructure.database.schema import init_database, get_connection
    from sentinel_omega.infrastructure.database.repository import SentinelRepository
    from sentinel_omega.infrastructure.database.seed_nodos import seed_topology

    config = load_config()

    if args.dry_run:
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        config = load_config()

    _print_banner(config)
    if not tarea_batch:
        _write_pid()
    else:
        logger.info("Modo tarea: no se toca el pid del ciclo vivo.")

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
        from sentinel_omega.infrastructure.pipeline.backcast import (
            run_backcast,
            run_backfill_secundario,
        )
        logger.info("Running historical backcast (one-time)...")
        run_backcast(str(db_path))
        logger.info("Running secondary backfill (volcanic SO2 + BTC)...")
        run_backfill_secundario(str(db_path))
        logger.info("Backcast complete.")

    if args.entrenar:
        from sentinel_omega.infrastructure.pipeline.entrenamiento import entrenar
        logger.info("Running signature training (Fase 1 + Fase 2)...")
        resultado = entrenar(str(db_path))
        logger.info(f"Training complete: {resultado}")

    if args.disciplina:
        from sentinel_omega.infrastructure.pipeline.entrenamiento import (
            disciplina_trasfondo,
        )
        logger.info("Running background discipline (castigo desde abajo)...")
        resultado = disciplina_trasfondo(str(db_path), dry_run=args.dry_run)
        logger.info(f"Background discipline complete: {resultado}")

    if args.barrido:
        from sentinel_omega.infrastructure.pipeline.mantenimiento import (
            barrido_diario,
        )
        logger.info("Running daily maintenance sweep (barrido diario)...")
        resultado = barrido_diario(str(db_path), dry_run=args.dry_run)
        logger.info(f"Daily sweep complete: {resultado}")

    # ── Reportes (después de cualquier operación batch) ──────────────────────
    if args.reporte:
        _run_reportes(str(db_path))

    # ── Modo tarea: ejecutar y salir ─────────────────────────────────────────
    # Los flags batch (--backcast/--entrenar/--disciplina/--barrido/--reporte)
    # sin --once NO deben caer al loop continuo de vigilancia: el vigilante los
    # invoca como pasos one-shot y el loop dejaba el job colgado indefinidamente
    # (la disciplina corría 3s y luego ciclaba 2h+ hasta cancelarse a mano).
    # Con --once se conserva el comportamiento de bootstrap: tareas + UN ciclo.
    if tarea_batch:
        logger.info("Batch task(s) complete — exiting (no --once/continuous).")
        return

    # Los modos batch de mantenimiento/disciplina no entran al ciclo de
    # vigilancia continuo: ejecutan su trabajo y salen limpiamente. Sin esto,
    # `--disciplina` / `--barrido` caían en el loop de "Next cycle in Ns...".
    if args.disciplina or args.barrido:
        _clear_pid()
        logger.info("Batch operation complete — exiting without watch loop.")
        return

    dashboard_proc = None
    if args.dashboard:
        dashboard_proc = _launch_dashboard()

    logger.info("Creating orchestrator with live pipelines...")
    orch = SentinelOrchestrator.create_with_live_pipelines(config)

    # Fuera del try de los pesos: si aquel falla, el umbral del WAL tiene que
    # existir igual --- el ciclo lo usa más abajo y un NameError ahí tumbaría
    # la revisión del registro justo cuando algo va mal.
    _UMBRAL_WAL_MB = float(getattr(getattr(config, "wal", None), "umbral_mb", 800.0))

    try:
        from sentinel_omega.core.juez.pesos import cargar_pesos
        por_merito = bool(getattr(getattr(config, "juez", None), "peso_por_merito", False))
        minimo = int(getattr(getattr(config, "juez", None), "minimo_ventanas", 50))
        pesos = cargar_pesos(repo._conn, por_merito=por_merito, minimo_ventanas=minimo)
        aplicados = int(pesos.pop("_meritos_aplicados", 0))
        competentes = int(pesos.pop("_competencias_aplicadas", 0))
        if pesos and orch._runner is not None:
            orch._runner.padre.set_pesos(pesos)
            if not por_merito:
                origen = "paseo multiplicativo"
            elif aplicados:
                origen = (f"MERITO contra el silencio ({aplicados} bots) "
                          f"+ competencia por clase ({competentes})")
            elif competentes:
                origen = (f"COMPETENCIA por clase de evento ({competentes} bots); "
                          "el merito de la fase viva aun no tiene evidencia")
            else:
                origen = ("merito PEDIDO pero SIN EVIDENCIA todavia: se usan "
                          "los pesos almacenados")
            logger.info("Pesos disciplinarios cargados (%s): %s", origen, pesos)
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

            # El disparador del WAL. Mirar el tamaño de un archivo cuesta
            # microsegundos, así que puede correr en cada ciclo; el volcado solo
            # se dispara por encima del umbral. Va FUERA del try del ciclo a
            # propósito: si el ciclo falla, el registro sigue creciendo igual y
            # es justo cuando más falta hace vaciarlo.
            try:
                from sentinel_omega.infrastructure.database.wal import volcar_si_crece
                volcar_si_crece(str(db_path), umbral_mb=_UMBRAL_WAL_MB)
            except Exception as e:  # noqa: BLE001 — nunca tumbar el ciclo por esto
                logger.warning("Revisión del WAL falló (non-blocking): %s", e)

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
            _b1 = getattr(runner.pipeline, "_cache", {}).get("beta1") or {} if runner else {}
            _a1 = getattr(runner.pipeline, "_cache", {}).get("alfa1") or {} if runner else {}
            _sch_hz = _b1.get("schumann_frequency")
            try:
                from sentinel_omega.infrastructure.api.geophysical import compute_lunar_phase
                _lunar = compute_lunar_phase()
                import numpy as _np
                _lp = _b1.get("lunar_phase", 0.5)
                if isinstance(_lp, _np.ndarray):
                    _lp = float(_lp[-1]) if _lp.size > 0 else 0.5
                _fase = _lunar.get("phase_fraction", _lp or 0.5)
            except Exception:
                import numpy as _np
                _lp = _b1.get("lunar_phase", 0.0)
                if isinstance(_lp, _np.ndarray):
                    _lp = float(_lp[-1]) if _lp.size > 0 else 0.0
                _fase = _lp or _b1.get("fase_lunar", 0.0) or 0.5
            try:
                _prot = _a1.get("proton_flux") or _a1.get("proton_speed") or _b1.get("proton_speed") or 0.0
                # Handle numpy arrays and other iterables
                import numpy as _np
                if isinstance(_prot, _np.ndarray):
                    _prot = float(_prot[-1]) if _prot.size > 0 else 0.0
                elif isinstance(_prot, (list, tuple)):
                    _prot = float(_prot[-1]) if _prot else 0.0
                else:
                    _prot = float(_prot) if _prot else 0.0
            except Exception:
                _prot = 0.0
            # Defensive scalar conversion for numpy arrays
            import numpy as _np
            def _scalar(v, default=0.0):
                if isinstance(v, _np.ndarray):
                    return float(v[-1]) if v.size > 0 else default
                if isinstance(v, (list, tuple)):
                    return float(v[-1]) if v else default
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return default

            # Schumann sin lectura viva = NULL, no el 7.83 / 0 inventado de antes.
            _sch_wpc = _scalar(risk.components.get("schumann_wpc"), None)
            if _sch_wpc is not None and _sch_wpc != _sch_wpc:
                _sch_wpc = None
            _sch_hz_v = _scalar(_sch_hz, None)
            if _sch_hz_v is not None and _sch_hz_v != _sch_hz_v:
                _sch_hz_v = None
            repo.insert_precursor_cosmico(
                bz=_scalar(risk.components.get("bz_nT"), None),  # sin dato = NULL, no 0
                viento=_scalar(risk.components.get("wind_kms"), None),  # sin dato = NULL, no 0
                protones=_prot,
                kp=_scalar(risk.components.get("kp", 0)),
                lod_ms=_scalar(risk.components.get("lod_ms"), None),  # sin dato = NULL, no 0
                schumann_hz=_sch_hz_v,  # sin dato = NULL, no 7.83
                schumann_activity=_sch_wpc * 100 if _sch_wpc is not None else None,  # sin dato = NULL, no 0
                presion_hpa=_scalar(risk.components.get("pressure_hpa", 1013)),
                fantasma=_scalar(risk.fantasma),
                nivel_riesgo=risk.risk_level,
                fase_lunar=_fase,
            )
        except Exception as e:
            import traceback
            logger.warning(f"Failed to persist cycle data: {e}")
            logger.warning(f"Traceback: {traceback.format_exc()}")

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

    # ── Persistir alfa2 (cobertura satelital) ──────────────────────
    if runner is not None:
        try:
            from sentinel_omega.core.alfa2_zonas import (
                puntaje_zona as _puntaje_zona,
            )
            alfa2_data = getattr(runner, "_last_alfa2_data", None)
            if alfa2_data and alfa2_data.get("zone_coverages"):
                ts_blk = _dt.now(_tz.utc).strftime("%Y-%m-%d %H:00:00")
                for zona, cov in alfa2_data["zone_coverages"].items():
                    cloud_covers = cov.get("s2_cloud_covers", [])
                    clear_passes = sum(1 for cc in cloud_covers if cc < 20.0)
                    total = cov.get("total_passes", 0)
                    # s2_count/s1_count se leían aquí y no se usaban:
                    # `insert_cobertura_satelital` no los acepta. Eran
                    # asignaciones muertas; el desglose por satélite vive en
                    # `tbl_alfa2_cobertura_zona`.
                    revisit = cov.get("mean_revisit_days", 0.0)
                    repo.insert_cobertura_satelital(
                        timestamp_blk=ts_blk,
                        zona=zona,
                        # La fórmula es `alfa2_zonas.puntaje_zona`, no una
                        # cuarta copia: estaba escrita a mano aquí, otra vez en
                        # `_build_live_features` y una tercera en el agregado.
                        # Tres copias de la misma aritmética se separan solas.
                        coverage_score=round(_puntaje_zona(
                            total, clear_passes, len(cloud_covers), revisit), 4),
                        # None, no 0: la columna acepta NULL y así el
                        # histórico distingue «no se midió» de «no hubo».
                        thermal_anomalies=alfa2_data.get("thermal_anomaly_count"),
                        clear_passes=clear_passes,
                        total_passes=total,
                        revisit_days=revisit,
                    )
        except Exception as exc:
            logger.warning(f"Failed to persist alfa2 coverage (non-blocking): {exc}")
        # Detecciones FRP completas (Sentinel-3 SLSTR). Tabla nueva, sólo
        # INSERT OR IGNORE: el LOCF puede repetir el mismo lote sin duplicar.
        try:
            alfa2_data = getattr(runner, "_last_alfa2_data", None) or {}
            frp = alfa2_data.get("frp_detections")
            if frp:
                nuevas = repo.insert_frp_detecciones(frp)
                logger.info(f"FRP: {nuevas} detecciones nuevas de {len(frp)}")
        except Exception as exc:
            logger.warning(f"Failed to persist FRP detections (non-blocking): {exc}")

    # ── Persistir correlación cruzada delta_enriched ──────────────
    if runner is not None:
        try:
            delta_cache = getattr(runner.pipeline, "_cache", {}).get("delta") or {}
            if delta_cache.get("cross_coupling") is not None:
                ts_blk = _dt.now(_tz.utc).strftime("%Y-%m-%d %H:00:00")
                repo.insert_delta_cross(
                    timestamp_blk=ts_blk,
                    cross_coupling=delta_cache.get("cross_coupling", 0.0),
                    geomagnetic_coupling=delta_cache.get("geo_coupling", 0.0),
                    schumann_coupling=delta_cache.get("schumann_coupling", 0.0),
                    composite_score=delta_cache.get("delta_composite_score", 0.0),
                    regime_label=delta_cache.get("delta_regime_label", ""),
                    confidence=delta_cache.get("delta_confidence", 0.0),
                    data_completeness=delta_cache.get("delta_data_completeness", 0.0),
                    geo_kp_max_3d=delta_cache.get("geo_kp_max_3d"),
                    geo_storm_active=delta_cache.get("geo_storm_active", 0),
                    geo_schumann_deviation=delta_cache.get("geo_schumann_deviation"),
                )
        except Exception as exc:
            logger.warning(f"Failed to persist delta cross (non-blocking): {exc}")


# Schumann: arrastre sin límite de edad, con bandera en_vivo (ver
# sentinel_omega/core/schumann_vivo.py). Decisión del Capitán, 2026-09-26.


# Tolerancia para considerar que una racha CONTINÚA. El ciclo corre cada ~5 min
# (300 s por defecto); con 20 min se aguanta un ciclo lento o dos perdidos sin
# partir la racha en dos, y un reinicio largo sí la parte, que es lo correcto.
RACHA_TOLERANCIA_MIN = 20


def _registrar_racha_viva(conn, matches) -> None:
    """Cuándo empezó la racha de emparejamiento ACTUAL de cada firma.

    Es el ancla que le faltaba a la cuenta regresiva. Medido el 2026-09-27:
    `format_lag_line` sabe restar el tiempo transcurrido al lag aprendido, pero
    se anclaba en `tbl_cimatica_patrones.primera_vez`, y **el rebuild pone esa
    columna al 100 % en la fecha del rebuild** (279.453 de 279.453 filas). Así
    que la cuenta regresiva se reiniciaba entera cada vez que se reconstruía la
    memoria, mostrando un número plausible que no medía nada.

    `TBL_FIRMAS.primera_vista` tampoco sirve: guarda fechas reales (1994–2026)
    pero es la primera vez HISTÓRICA, y restarle el transcurrido da «restan 0 h».

    Lo que hace falta es un tercer dato que no existía: el instante en que la
    firma empezó a emparejar EN ESTA racha. Con eso, «restan ~N h» cuenta de
    verdad hacia abajo mientras el patrón se mantiene, y se reinicia solo cuando
    el patrón desaparece y vuelve --- que es lo que el operador describió.

    Es dato VIVO: no se puede reconstruir del histórico y no lo toca el rebuild.
    """
    if not matches:
        return
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS tbl_firma_racha_viva ("
            "firma_id TEXT PRIMARY KEY, inicio_ts TEXT NOT NULL, "
            "ultimo_ts TEXT NOT NULL, ciclos INTEGER NOT NULL DEFAULT 1)"
        )
        for m in matches:
            fid = m.get("firma_id")
            if not fid:
                continue
            # Si la última vez que se vio es reciente, la racha sigue; si no,
            # empieza una nueva. `excluded` es la fila que se intentó insertar.
            conn.execute(
                "INSERT INTO tbl_firma_racha_viva "
                "  (firma_id, inicio_ts, ultimo_ts, ciclos) "
                "VALUES (?, datetime('now'), datetime('now'), 1) "
                "ON CONFLICT(firma_id) DO UPDATE SET "
                "  inicio_ts = CASE WHEN ultimo_ts >= datetime('now', ?) "
                "                   THEN inicio_ts ELSE datetime('now') END, "
                "  ciclos    = CASE WHEN ultimo_ts >= datetime('now', ?) "
                "                   THEN ciclos + 1 ELSE 1 END, "
                "  ultimo_ts = datetime('now')",
                (str(fid), f"-{RACHA_TOLERANCIA_MIN} minutes",
                 f"-{RACHA_TOLERANCIA_MIN} minutes"),
            )
        conn.commit()
    except Exception as e:  # noqa: BLE001 — el ciclo no se cae por la racha
        logger.warning("Racha viva de firmas no registrada (%s)", e)


def _build_live_features(runner, conn=None) -> dict:
    """Build the firma feature vector from the live pipeline cache.

    Extrae features para los 5 bots entrenados:
      alfa1  — clima espacial (Bz, viento solar)
      beta1  — Kp, Schumann, sismicidad, fase lunar
      beta2  — desgasificación volcánica (proxy OWM → escala kt aproximada)
      delta  — volatilidad financiera BTC
      alfa2  — cobertura satelital ESA Sentinel (acumulación desde ciclos vivos)

    El proxy de beta2 usa el global_node_scan de OpenWeatherMap:
    - erupciones_win  ≈ # nodos volcánicos/tectónicos con SO2 > umbral
    - so2_kt_win      ≈ suma de exceso SO2 en nodos (μg/m³) × factor escala
    El factor de escala es muy conservador (1e-4) porque 1 kilotón de SO2
    dispersado a nivel global corresponde a ~10 μg/m³ en 1 nodo de referencia.
    Los valores se mueven en la misma escala relativa que el histórico entrenado
    (0 en calma, positivo en actividad), lo que es suficiente para que la
    función de similitud distinga estados activos de estados quietos.
    """
    import numpy as np

    features = {}
    if runner is None or not hasattr(runner, "pipeline"):
        return features
    cache = getattr(runner.pipeline, "_cache", {})

    # ── alfa1: clima espacial ──────────────────────────────────────
    # Los agregados los calcula la MISMA función que arma el vector de
    # inferencia (core/features_onnx.agregados_omni). Antes aquí se calculaban
    # a mano solo cuatro --- bz_mean, bz_min, viento_avg, viento_max --- y
    # faltaban proton_max, bz_deriv_std y bz_mean_72h, que sí están en el orden
    # del modelo. Consecuencia (medida el 2026-09-25, revisando la tubería
    # entera): el Juez guardaba esas tres posiciones vacías, así que el
    # reentrenamiento aprendería «aquí siempre hay un 0» mientras la inferencia
    # manda valores de verdad. Un desajuste nuevo, más fino que el que se acaba
    # de arreglar, pero de la misma familia.
    alfa1 = cache.get("alfa1") or {}
    omni = alfa1.get("omni_dataframe")
    if omni is not None:
        from sentinel_omega.core.features_onnx import agregados_omni
        columnas = [c for c in omni.columns]
        try:
            features.update(agregados_omni(columnas, omni[columnas].values))
        except Exception as e:  # noqa: BLE001 — el ciclo sigue sin estos rasgos
            logger.warning("agregados de OMNI fallaron (non-blocking): %s", e)
    # `proton_max` no sale de `agregados_omni`: el flujo de protones se busca
    # aparte (`data_pipeline`) y NO viaja como columna del `omni_dataframe`, así
    # que la posición del vector llegaba siempre vacía --- y con ella ausente el
    # modelo canónico de alfa1 se abstenía (medido el 2026-09-27, NO_SIGNAL
    # 0,31, mientras el agente con su propio vector decía WATCH 0,72).
    _prot_max = alfa1.get("proton_flux_max")
    if _prot_max is not None:
        features["proton_max"] = float(_prot_max)

    # ── beta1: Kp / Schumann / sismicidad / lunar ─────────────────
    # Medido el 2026-09-26: de los 10 rasgos que pide el modelo de beta1, el
    # ciclo solo producía 5. Los otros cinco --- es_sicigia, kp_max_72h,
    # schumann_std, sismo_count_72h y schumann_mean cuando la fuente falla ---
    # llegaban como 0.0 al vector, que para el modelo significa «ese día no
    # hubo sicigia» o «cero sismos», no «no lo sé». Se calculan aquí, de los
    # mismos datos que ya trae el ciclo.
    beta1 = cache.get("beta1") or {}
    # El Kp se agrega de la MISMA tabla y con las MISMAS ventanas que la firma,
    # o no significa lo mismo. Medido el 2026-09-27 (hallazgo de Agente-C):
    #
    #   entrenamiento (signature_engine:148/280)  tbl_clima_espacial_raw, bloques
    #                                             de 1 h, ventanas de 336 h y 72 h
    #   inferencia    (esto, antes)               `kp_series` de NOAA, que es
    #                                             `planetary_k_index_1m.json`
    #
    # Ese feed es de **1 minuto** y trae unas 6 h en total (medido en vivo: 358
    # filas, 5,95 h). Así que `kp[-24:]` son **24 minutos**, no 72 h --- 72 h
    # serían 4.320 muestras y el feed no las tiene ni puede tenerlas. El
    # comentario que decía «viene en tramos de 3 h» era falso. Mismo nombre,
    # cantidades que difieren 180×.
    #
    # Y no era solo `kp_max_72h`: los tres rasgos de Kp salían de una ventana de
    # 6 h donde el entrenamiento usa 336 h. Comparado esta noche:
    #
    #   MAX(kp_max) 72 h real = 4,0        contra  max(kp[-24:]) = 0,000
    #   AVG(kp_prom) 336 h    = 1,96       contra  mean(feed 6 h) ≈ 0,30
    #
    # La distribución con la que se entrenó tiene p5 = 0,896 y mediana 1,742, así
    # que el ciclo vivo entregaba el Kp **por debajo del percentil 5** de forma
    # permanente. Arreglar solo `kp_max_72h` y dejar los otros dos habría bajado
    # el número sin cerrar el desajuste.
    #
    # Sin tabla no se inventa: los rasgos se omiten y `vector_para` pone 0,0.
    # Las últimas 72 h tienen 71 de 72 bloques con 66 de Kp, así que la fuente
    # está viva --- la escribe este mismo launcher cada hora.
    if conn is not None:
        try:
            fila = conn.execute(
                "SELECT AVG(kp_promedio), MAX(kp_max) "
                "FROM tbl_clima_espacial_raw "
                "WHERE timestamp_blk >= datetime('now','-336 hours')"
            ).fetchone()
            if fila and fila[0] is not None:
                features["kp_mean"] = float(fila[0])
            if fila and fila[1] is not None:
                features["kp_max"] = float(fila[1])
            fila = conn.execute(
                "SELECT MAX(kp_max) FROM tbl_clima_espacial_raw "
                "WHERE timestamp_blk >= datetime('now','-72 hours')"
            ).fetchone()
            if fila and fila[0] is not None:
                features["kp_max_72h"] = float(fila[0])
            # Densidad de protones, MISMA ventana que la firma (336 h) y misma
            # tabla. El valor instantáneo de `fetch_solar_wind()` NO sirve aquí
            # por la regla de este archivo: la firma calcula media y máximo
            # sobre la ventana, así que preguntarle al modelo con un instante
            # es la misma trampa que costó el desajuste del Kp.
            fila = conn.execute(
                "SELECT AVG(densidad_protones), MAX(densidad_protones) "
                "FROM tbl_clima_espacial_raw "
                "WHERE timestamp_blk >= datetime('now','-336 hours')"
            ).fetchone()
            if fila and fila[0] is not None:
                features["densidad_prot_mean"] = float(fila[0])
            if fila and fila[1] is not None:
                features["densidad_prot_max"] = float(fila[1])
        except Exception as e:  # noqa: BLE001 — el ciclo sigue sin los rasgos
            logger.warning("Kp/densidad por ventana no disponible (%s): "
                           "quedan sin dato", e)
    if "schumann_frequency" in beta1:
        features["schumann_mean"] = float(beta1["schumann_frequency"])
    # La dispersión de Schumann: el modelo la pide y nadie la calculaba.
    for clave in ("schumann_std", "schumann_sigma", "schumann_desviacion"):
        if clave in beta1 and beta1[clave] is not None:
            features["schumann_std"] = float(beta1[clave])
            break
    else:
        serie_sch = beta1.get("schumann_series")
        if serie_sch is not None and len(serie_sch) > 1:
            v = np.asarray(serie_sch, dtype=float)
            v = v[np.isfinite(v)]
            if v.size > 1:
                features["schumann_std"] = float(np.std(v))
    # Los conteos sísmicos se calculan como los calcula la FIRMA, o no
    # significan lo mismo. Medido el 2026-09-27 (ciclo 14419):
    #
    #   entrenamiento (signature_engine.py:180/281)  del NODO, 336 h y 72 h,
    #                                                 SUM sobre el histórico
    #   inferencia    (esto, antes)                   global, 30 d, len() del
    #                                                 catálogo de USGS
    #
    # Y el catálogo viene topado (`api/usgs.py: MAX_RESULTS = 500`), así que
    # `len(...)` valía 500 en TODOS los ciclos. Contra la distribución con la
    # que se entrenó --- mediana 7, p75 14, p99 244, solo 34 de 15.282 firmas
    # llegan a 500 --- eso ponía al modelo, cada cinco minutos, por encima del
    # percentil 99,8: «enjambre extremo en este nodo», permanente y falso.
    #
    # El ciclo es global y la firma es por nodo, así que se manda el MÁXIMO
    # sobre los nodos: conserva la escala aprendida (14-sep: máx 99) y
    # responde a la pregunta que el rasgo hace, «¿hay algún nodo enjambrado?».
    # Sin conexión no se inventa nada: el rasgo se omite y `vector_para` pone
    # 0,0, que es «no lo sé».
    if conn is not None:
        for nombre, horas in (("sismo_count_win", 336), ("sismo_count_72h", 72)):
            try:
                fila = conn.execute(
                    "SELECT COALESCE(MAX(n),0) FROM ("
                    "  SELECT SUM(sismo_count) AS n"
                    "  FROM tbl_historico_sismico_raw"
                    f" WHERE timestamp_blk >= datetime('now','-{horas} hours')"
                    "  GROUP BY id_nodo)"
                ).fetchone()
            except Exception as e:  # noqa: BLE001 — el ciclo sigue sin el rasgo
                logger.warning("%s no se pudo contar (%s): queda sin dato",
                               nombre, e)
                continue
            if fila and fila[0] is not None:
                features[nombre] = float(fila[0])

    mags = beta1.get("seismic_magnitudes")
    if mags is not None and len(mags) > 0:
        # La magnitud máxima NO se topa: el catálogo llega recortado a 500, pero
        # el máximo de esos 500 sigue siendo un máximo medido.
        features["sismo_max_mag_win"] = float(np.nanmax(mags))
    lunar = beta1.get("lunar_phase")
    if lunar is not None and len(lunar) > 0:
        fase = float(lunar[-1])
        features["fase_lunar"] = fase
        # Sicigia = luna nueva o llena: la fase (0-1) cerca de 0, 0,5 o 1.
        # Es lo que el modelo espera en esa posición, y llegaba siempre 0.
        distancia = min(abs(fase - x) for x in (0.0, 0.5, 1.0))
        features["es_sicigia"] = 1.0 if distancia <= 0.05 else 0.0

    # ── beta2: desgasificación volcánica (proxy OWM) ──────────────
    _SO2_SCALE = 1e-4
    beta2 = cache.get("beta2") or {}
    node_scan = beta2.get("global_node_scan", [])
    if node_scan:
        degassing_nodes = [
            n for n in node_scan
            if n.get("tipo", "") in ("VOLCAN", "TECTONICO")
        ]
        aq_baseline = beta2.get("degassing_baseline") or {}
        base_so2 = aq_baseline.get("so2", 0.0)
        erupciones_proxy = 0
        so2_sum = 0.0
        for node in degassing_nodes:
            excess = max(0.0, node.get("so2", 0.0) - base_so2)
            if excess > 50.0:  # NODE_SO2_EXCESS_ALERT
                erupciones_proxy += 1
                so2_sum += excess
        features["erupciones_win"] = float(erupciones_proxy)
        features["so2_kt_win"] = round(so2_sum * _SO2_SCALE, 6)
        features["erupciones_90d"] = float(erupciones_proxy)
        features["so2_kt_90d"] = round(so2_sum * _SO2_SCALE, 6)

    # ── delta: volatilidad financiera BTC ─────────────────────────
    delta = cache.get("delta") or {}
    for key in ("btc_volatilidad", "btc_vol_max", "btc_ret_win", "btc_vol_72h",
                "vix"):
        if key in delta and delta[key] is not None:
            features[key] = float(delta[key])

    # ── loki y jupiter: rayos X y tendencias ──────────────────────
    # Sus modelos se entrenan con xray_mean/xray_max/trends_mean --- están en
    # las firmas, con variación real --- y el ciclo no los producía, así que al
    # inferir llegaban como 0.0: para el modelo, «el Sol no emite rayos X».
    # Las dos tablas se llenan cada hora y estaban ahí sin usarse.
    if conn is not None:
        try:
            fila = conn.execute(
                "SELECT flux_avg, flux_max FROM tbl_xray_vivo "
                "ORDER BY timestamp_blk DESC LIMIT 1"
            ).fetchone()
            if fila and fila[0] is not None:
                features["xray_mean"] = float(fila[0])
                features["xray_max"] = float(fila[1] or fila[0])
            fila = conn.execute(
                "SELECT solar_interest FROM tbl_trends_vivo "
                "ORDER BY fecha DESC LIMIT 1"
            ).fetchone()
            if fila and fila[0] is not None:
                features["trends_mean"] = float(fila[0])
        except Exception as e:  # noqa: BLE001 — el ciclo sigue sin estos
            logger.warning("rayos X / tendencias no disponibles: %s", e)

    # ── alfa2: cobertura satelital ────────────────────────────────
    alfa2_data = getattr(runner, "_last_alfa2_data", None)
    # El agregado sale de TODAS las zonas medidas, no solo de las tres que le
    # tocaron a este ciclo (2026-10-02). Antes el rasgo describía tres cajas
    # mexicanas mientras el Juez calificaba a alfa2 contra el catálogo mundial;
    # ahora describe el barrido global que la rotación mantiene al día.
    # `agregado_global` devuelve None si todavía no hay ninguna lectura ---
    # faltante es faltante ---, y entonces se cae al cálculo del propio ciclo.
    from sentinel_omega.core.alfa2_zonas import agregado_global, puntaje_zona
    glob = agregado_global(conn) if conn is not None else None
    if glob:
        # Solo para el registro: cuántas zonas lleva medidas la rotación. NO se
        # usa como rasgo --- ver el bloque de abajo.
        logger.info("Alfa-2 rotación: %d zonas con lectura, puntaje medio "
                    "%.4f", glob["zonas"], glob["satellite_coverage_score"])

    # Los CUATRO rasgos de alfa2 salen de la MISMA ventana, la MISMA tabla y
    # con la MISMA agregación que la firma (`signature_engine`: media para
    # `coverage_score` y `revisita_dias`, SUMA para `thermal_anomalies` y
    # `clear_passes`, sobre 336 h de `tbl_cobertura_satelital` unida a su
    # histórico).
    #
    # Antes dos de ellos salían del agregado de la rotación --- la suma sobre
    # las ZONAS de la última lectura --- y eso es otra magnitud con el mismo
    # nombre. Medido el 2026-10-02, justo antes de hacer votante a alfa2:
    #
    #   coverage_score     firma 0,7894 media   vivo 0,8019    compatible
    #   thermal_anomalies  firma   447  SUMA    vivo 0-1        ~160x
    #   clear_passes       firma  5437  SUMA    vivo   34       ~160x
    #   revisita_dias      firma 0,6916 media   vivo 0,6916     identico
    #
    # Es el desajuste del Kp otra vez, y habría entrado en producción con el
    # voto de alfa2 si no se hubieran mirado sus firmas antes de declararlo.
    if conn is not None:
        try:
            filas = conn.execute(
                "SELECT coverage_score, thermal_anomalies, clear_passes, "
                "       revisit_days FROM ("
                "  SELECT coverage_score, thermal_anomalies, clear_passes,"
                "         revisit_days FROM tbl_cobertura_satelital"
                "   WHERE timestamp_blk >= datetime('now','-336 hours')"
                "  UNION ALL"
                "  SELECT coverage_score, thermal_anomalies, clear_passes,"
                "         revisit_days FROM tbl_cobertura_satelital_historico"
                "   WHERE timestamp_blk >= datetime('now','-336 hours'))"
            ).fetchall()
            cov = [f[0] for f in filas if f[0] is not None]
            ther = [f[1] for f in filas if f[1] is not None]
            clar = [f[2] for f in filas if f[2] is not None]
            revi = [f[3] for f in filas if f[3] is not None]
            if cov:
                features["satellite_coverage_score"] = round(float(np.mean(cov)), 4)
            if ther:
                features["satellite_thermal_anomalies"] = float(sum(ther))
            if clar:
                features["satellite_clear_passes"] = float(sum(clar))
            if revi:
                features["satellite_revisita_dias"] = float(np.mean(revi))
            if filas:
                logger.info("Alfa-2 (ventana 336 h, %d lecturas): puntaje "
                            "%.4f · %d limpias · %d anomalías · revisita "
                            "%.3f d", len(filas),
                            features.get("satellite_coverage_score", float("nan")),
                            int(features.get("satellite_clear_passes", 0)),
                            int(features.get("satellite_thermal_anomalies", 0)),
                            features.get("satellite_revisita_dias", float("nan")))
        except Exception as e:  # noqa: BLE001 — los rasgos se OMITEN, no se fingen
            logger.warning("Rasgos satelitales por ventana no disponibles "
                           "(%s): quedan sin dato", e)
    # NO hay respaldo por ciclo, y es deliberado.
    #
    # Lo hubo hasta el 2026-10-02: si la ventana estaba vacía, se escribían el
    # puntaje y las pasadas limpias sumadas sobre las ZONAS de este ciclo. Pero
    # eso no es un respaldo, es el desajuste con un `if` delante --- 34 contra
    # 5.437 para el mismo nombre de rasgo. Si la ventana no tiene lecturas, los
    # rasgos se OMITEN y `vector_para` pone 0,0, que significa «no lo sé».
    #
    # La anomalía térmica tampoco se escribe desde aquí: el conteo del FRP se
    # persiste en `tbl_cobertura_satelital` unas líneas más abajo
    # (`thermal_anomalies=alfa2_data.get("thermal_anomaly_count")`), así que
    # llega al rasgo por la ventana y a la escala en que se entrenó. Pasar por
    # la tabla es más lento de ver, pero es la única forma de que lo entrenado
    # y lo preguntado sean la misma magnitud.

    # ── beta2: marea terrestre ────────────────────────────────────
    # El tirón de la Luna y el Sol, por efemérides. Es la única fuente del
    # sistema que no puede fallar ni tener huecos: no llama a ninguna API. Se
    # añadió el 2026-09-26 porque beta2 llevaba desde el 2026-07-31 sin una
    # sola fuente viva --- sus cuatro rasgos volcánicos llegaban ausentes.
    try:
        from sentinel_omega.core.mareas import marea_para_ciclo
        features.update(marea_para_ciclo())
    except Exception as e:  # noqa: BLE001 — el ciclo sigue sin marea
        logger.warning("marea no disponible (non-blocking): %s", e)

    # ── delta_enriched: acoplamiento cruzado geofísico-financiero ──
    # Solo si la pasada delta_enriched corrió: un fetch fallido deja las
    # claves ausentes y la feature debe quedar NaN (excluida por similitud),
    # nunca un 0.0 falso.
    if delta.get("cross_coupling") is not None:
        features["delta_cross_coupling"] = float(delta["cross_coupling"])
    if delta.get("geo_coupling") is not None:
        features["delta_geo_coupling"] = float(delta["geo_coupling"])
    if delta.get("schumann_coupling") is not None:
        features["delta_schumann_coupling"] = float(delta["schumann_coupling"])

    return features


def _auditar_ciclo(geo, repo, runner) -> None:
    """Firma matching + Juez registration/resolution for this cycle."""
    try:
        from sentinel_omega.core.firmas.signature_engine import FirmaMemoria
        from sentinel_omega.core.juez.juez import Juez

        conn = repo._conn
        memoria = FirmaMemoria(conn)
        juez = Juez(conn)

        # Serie viva de Schumann: la lectura en tiempo real de esta corrida
        # (WPC de Tomsk) se acumula con su bloque horario. Con el tiempo esta
        # serie alimenta el dominio SCHUMANN de los cruces (no hay backcast).
        try:
            from sentinel_omega.core import schumann_vivo
            beta1_cache = getattr(runner.pipeline, "_cache", {}).get("beta1") or {}
            sch = schumann_vivo.registrar(
                conn,
                beta1_cache.get("schumann_frequency"),
                beta1_cache.get("schumann_activity"),
            )
            if sch["estado"] == "arrastrado":
                logger.info(
                    "Schumann API caída: arrastro el último valor real (%s, "
                    "%.1f h) -> %s / %s, en_vivo=0",
                    sch["ultimo_vivo_ts"], sch["atraso_horas"],
                    sch["schumann_hz"], sch["schumann_activity"],
                )
            elif sch["estado"] == "desconocido":
                logger.warning(
                    "Schumann DESCONOCIDO: la API falla y no hay ninguna "
                    "lectura real guardada. No se inventa un valor."
                )
        except Exception as e:
            logger.warning(f"Persistencia Schumann viva falló (non-blocking): {e}")

        matches = []
        features = _build_live_features(runner, conn)
        if features:
            matches = memoria.match_estado_actual(features)
            _registrar_racha_viva(conn, matches)
            for m in matches[:5]:
                try:
                    nodo = conn.execute(
                        "SELECT nombre, lat, lon, region FROM "
                        "TBL_NODOS_TOPOLOGIA WHERE node_id = ?",
                        (m["id_nodo"],),
                    ).fetchone()
                    if nodo:
                        m["nodo_nombre"] = nodo[0]
                        m["nodo_lat"] = round(nodo[1], 1)
                        m["nodo_lon"] = round(nodo[2], 1)
                        m["nodo_region"] = nodo[3]
                except Exception:
                    pass
            for m in matches[:3]:
                ventana = ""
                try:
                    lag_firma = conn.execute(
                        "SELECT lag_promedio_h, lag_n FROM TBL_FIRMAS "
                        "WHERE firma_id = ? AND lag_promedio_h IS NOT NULL",
                        (m["firma_id"],),
                    ).fetchone()
                    if lag_firma:
                        # En HORAS, que es la resolución que el entrenamiento
                        # mide desde el 2026-09-27 (antes la rejilla era de 48 a
                        # 96 h, así que dividir por 24 no perdía nada; ahora sí:
                        # 202,7 h impresas como «8 días» tiran la precisión que
                        # se acaba de ganar). `ventana_tipica_dias` se conserva
                        # porque lo leen muro_lags, generar_reporte y el
                        # ejecutivo --- campo añadido, ninguno quitado.
                        m["ventana_tipica_h"] = round(lag_firma[0], 1)
                        m["ventana_tipica_dias"] = round(lag_firma[0] / 24, 1)
                        m["lag_n"] = lag_firma[1]
                        ventana = (
                            f" — ESTA firma suele presentarse "
                            f"~{lag_firma[0]:.0f} h antes "
                            f"({lag_firma[0]/24:.1f} d, n={lag_firma[1]})"
                        )
                    else:
                        # ¿Se MIDIÓ esta firma y salió sin anticipación? Desde
                        # el 2026-10-08 eso se puede saber (`lag_medido_at`), y
                        # entonces caer al promedio de la clase sería afirmar
                        # una ventana que nuestra propia medición niega: el
                        # patrón no se ve antes de SU evento. Se dice.
                        medida_sin_lag = False
                        try:
                            medida_sin_lag = bool(conn.execute(
                                "SELECT 1 FROM TBL_FIRMAS WHERE firma_id = ? "
                                "AND lag_medido_at IS NOT NULL "
                                "AND lag_promedio_h IS NULL",
                                (m["firma_id"],)).fetchone())
                        except Exception:
                            pass          # sin la columna, el camino de antes
                        if medida_sin_lag:
                            m["lag_n"] = 0
                            ventana = (
                                " — medida y SIN anticipación: este patrón no "
                                "se reconoce antes de su evento, así que no "
                                "da tiempo de aviso"
                            )
                            m["ventana_tipica_h"] = None
                            m["ventana_tipica_dias"] = None
                            lag = None
                        else:
                            lag = conn.execute(
                                "SELECT lag_promedio_h, lag_max_h FROM "
                                "tbl_lag_anticipacion WHERE event_class = ?",
                                (m["event_class"],),
                            ).fetchone()
                        if lag:
                            # Promedio de la CLASE: la firma no tiene el suyo.
                            m["ventana_tipica_h"] = round(lag[0], 1)
                            m["ventana_tipica_dias"] = round(lag[0] / 24, 1)
                            ventana = (
                                f" — ventana típica de su clase ~{lag[0]:.0f} h "
                                f"({lag[0]/24:.1f} d, hasta {lag[1]:.0f} h)"
                            )
                except Exception:
                    pass
                lugar = m.get("nodo_nombre") or f"nodo {m['id_nodo']}"
                logger.warning(
                    f"FIRMA MATCH: estado actual se parece {m['similitud']:.0%} "
                    f"a la firma que precedió {m['event_class']} "
                    f"({lugar}, nodo {m['id_nodo']}, "
                    f"vista {m['recurrencia']} veces){ventana}"
                )

        muro_lags = {}
        try:
            from sentinel_omega.core.precursor.muro_lags import (
                evaluar_muro_lags,
                format_muro_lags,
                cargar_estado_muro_lags,
                guardar_estado_muro_lags,
            )
            # Memoria: si la MISMA convergencia persiste, conserva el ancla y
            # descuenta días (no re-proyecta desde ahora cada ciclo).
            estado_previo = cargar_estado_muro_lags(conn)
            muro_lags = evaluar_muro_lags(matches, estado_previo=estado_previo)
            guardar_estado_muro_lags(conn, muro_lags)
            if muro_lags.get("activo"):
                logger.warning(format_muro_lags(muro_lags))
        except Exception as e:
            logger.warning(f"Muro de lags failed (non-blocking): {e}")

        # Nodos DE la predicción: un aviso solo vale si acierta DÓNDE avisó.
        # El Juez valida esta fila solo contra estos nodos (no toda la malla)
        # — sin esto, el modelo nulo de Molchan gana siempre.
        nodos_pred = [
            {"id": m["id_nodo"], "lat": m.get("nodo_lat"),
             "lon": m.get("nodo_lon")}
            for m in matches[:5]
            if m.get("nodo_lat") is not None
        ]
        from sentinel_omega.infrastructure.pipeline.juez_cycle_register import (
            register_cycle_predictions,
        )
        # `features=` NO es opcional: sin él, cada fila de la auditoría guarda
        # "features_generales": {} y el reentrenamiento no tiene con qué
        # aprender. La clave se añadió el 2026-08-20 justo para esto, pero esta
        # llamada nunca la pasó, así que las 19.422 filas vivas quedaron sin
        # rasgos (medido el 2026-09-25). `features` ya está calculado arriba,
        # en el mismo ciclo: pasarlo no cuesta nada.
        register_cycle_predictions(
            juez, geo, matches=matches, conn=conn,
            muro_lags=muro_lags, nodos_pred=nodos_pred,
            features=features,
        )

        # ── Cimática: snapshot del sistema → patrón nuevo o frecuencia+1 ──
        # Todo alta/incremento dispara la revisión del Padre; si el patrón
        # es nuevo con el Padre activo, o se volvió consistente y está
        # asociado a un tipo de evento, se envía alerta por Telegram.
        try:
            from sentinel_omega.core.firmas.cimatica import (
                FRECUENCIA_CONSISTENTE, registrar_snapshot,
            )
            from sentinel_omega.infrastructure.messaging.alert_service import AlertService, AlertTemplates
            from sentinel_omega.infrastructure.pipeline.entrenamiento import dispara_alerta

            if features:
                ec_top = matches[0]["event_class"] if matches else None
                snapshots = [(None, ec_top)] + [
                    (m["id_nodo"], m["event_class"]) for m in matches[:3]
                ]
                padre_activo = geo.final_signal.value in ("alert", "watch")
                for id_nodo, ec in snapshots:
                    pid_c, es_nuevo, frec = registrar_snapshot(
                        conn, features, id_nodo=id_nodo, event_class=ec,
                    )
                    if not pid_c:
                        continue
                    # Trigger: el Padre revisa cada alta/incremento
                    logger.info(
                        f"PADRE REVISA cimática: patrón {pid_c} "
                        f"({'nuevo' if es_nuevo else f'frecuencia {frec}'}"
                        f"{f', nodo {id_nodo}' if id_nodo else ', general'})"
                    )
                    if es_nuevo and padre_activo and dispara_alerta(ec_top):
                        svc = AlertService()
                        msg = AlertTemplates.cimatica_nuevo(
                            patron_id=pid_c,
                            clave=str(features),
                            ambito="general" if id_nodo is None else "nodo",
                            id_nodo=id_nodo,
                            event_class=ec_top,
                        )
                        svc.dispatch(msg, channels=["telegram", "log"], conn=conn,
                                     extra={"es_nuevo": True, "frecuencia": frec})
                    elif frec == FRECUENCIA_CONSISTENTE and ec and dispara_alerta(ec):
                        svc = AlertService()
                        msg = AlertTemplates.cimatica_consistente(
                            patron_id=pid_c,
                            clave=str(features),
                            frecuencia=frec,
                            event_class=ec,
                            ambito="general" if id_nodo is None else "nodo",
                            id_nodo=id_nodo,
                        )
                        svc.dispatch(msg, channels=["telegram", "log"], conn=conn,
                                     extra={"frecuencia": frec})
        except Exception as e:
            logger.warning(f"Cimática falló (non-blocking): {e}")

        # AssertivityTracker: los avisos se anclan a SUS nodos al momento
        # de emitirse (la validación + Molchan corre en la pasada del Juez).
        tracker = getattr(runner, "assertivity", None)
        if tracker is not None and geo.final_signal.value in ("alert", "watch"):
            for m in matches[:3]:
                if m.get("nodo_lat") is not None:
                    tracker.record_prediction(
                        m["nodo_lat"], m["nodo_lon"],
                        risk_level=geo.final_signal.value.upper(),
                        fantasma=float(geo.confidence),
                        source=f"nodo{m['id_nodo']}",
                    )

        # El Juez pasa a verificar real vs predicción CADA 4 HORAS (ritmo
        # auto-impuesto en verificacion.py): el ciclo del Padre solo
        # registra; la confrontación con USGS es tarea del Juez.
        from sentinel_omega.infrastructure.pipeline.verificacion import (
            verificar_juez,
        )
        resultado_juez = verificar_juez(conn, tracker=tracker)
        if resultado_juez.get("resueltas"):
            logger.info(
                f"Juez resolvió {resultado_juez['resueltas']} predicciones "
                f"pendientes"
            )
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
        help=(
            "Dry run: silencia Telegram y bloquea las escrituras de las "
            "tareas batch (--disciplina/--barrido)"
        ),
    )
    parser.add_argument(
        "--backcast", action="store_true",
        help="Run historical backcast (1994-2025) before starting cycles",
    )
    parser.add_argument(
        "--entrenar", action="store_true",
        help="Run signature training over the backcast (Fase 1 + Fase 2)",
    )
    parser.add_argument(
        "--disciplina", action="store_true",
        help="Run background discipline on minor quakes (castigo desde abajo)",
    )
    parser.add_argument(
        "--barrido", action="store_true",
        help="Run daily maintenance sweep (compact history, keep significant)",
    )
    parser.add_argument(
        "--reporte", action="store_true",
        help=(
            "Generate post-training reports (reporte_general + reporte_padre). "
            "Can be combined with --entrenar (runs after training) or standalone."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
