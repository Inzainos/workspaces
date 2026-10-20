#!/usr/bin/env python3
"""
Vigilante de rebuild de Sentinel Omega.
Monitorea deploy/rebuild_completo.py y, al terminar, reinicia servicios.
"""
import subprocess, sqlite3, sys, time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SENTINEL_DB = WORKSPACE / "sentinel_omega" / "data" / "SENTINEL_OMEGA_PRO.db"
REBUILD_SCRIPT = "deploy/rebuild_completo.py"

def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [REBUILD-WATCH] {msg}", flush=True)

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()

def restart_services():
    log("Reiniciando servicios de Sentinel Omega...")
    for svc in ["sentinel-omega.service", "sentinel-omega-watchdog.service",
                "sentinel-omega-dashboard-api.service", "sentinel-omega-dashboard.web.service"]:
        rc, out = run_cmd(f"systemctl --user restart {svc}")
        if rc != 0:
            log(f"  ERROR reiniciando {svc}: {out[:80]}")
        else:
            log(f"  OK: {sentiname if False else svc}")
    # Re-anclar timers
    for t in ["sentinel-omega-rutinas.timer","sentinel-omega-mantenimiento.timer",
              "sentinel-omega-onnx-retrain.timer","sentinel-omega-autofix.timer"]:
        rc, out = run_cmd(f"systemctl --user enable --now {t}")
        if rc != 0:
            log(f"  ERROR timer {t}: {out[:60]}")

def verify_live():
    try:
        conn = sqlite3.connect(str(SENTINEL_DB), timeout=10)
        c = conn.execute("SELECT datetime(timestamp) FROM TBL_CICLOS ORDER BY timestamp DESC LIMIT 1").fetchone()
        conn.close()
        if c:
            return True, f"Último ciclo: {c[0]}"
    except Exception as e:
        return False, str(e)
    return False, "No hay ciclos en TBL_CICLOS"

def main():
    log("=== VIGILANTE DE REBUILD INICIADO ===")
    
    # Verificar si ya hay un rebuild corriendo
    r = subprocess.run("pgrep -f 'deploy/rebuild_completo.py'", shell=True,
                       capture_output=True, text=True)
    pids = [p for p in r.stdout.strip().split("\n") if p.strip()]
    if pids:
        log(f"Ya hay un rebuild corriendo (PID {pids[0]}). Esperando a que termine...")
        pid = pids[0]
    else:
        log("No hay rebuild corriendo. Lanzando uno nuevo...")
        subprocess.Popen(["python", "deploy/rebuild_completo.py"],
                         cwd=str(WORKSPACE),
                         stdout=open("estado/rebuild.log", "a"),
                         stderr=subprocess.STDOUT)
        time.sleep(5)
        r = subprocess.run("pgrep -f 'deploy/rebuild_completo.py'", shell=True,
                           capture_output=True, text=True)
        pids = [p for p in r.stdout.strip().split("\n") if p.strip()]
        if not pids:
            log("ERROR: No se pudo iniciar el rebuild")
            return 1
        pid = int(pids[0])
        log(f"PID del rebuild: {pid}")

    # Esperar a que termine
    while True:
        time.sleep(30)
        r = subprocess.run(f"ps -p {pid} --no-headers", shell=True,
                           capture_output=True, text=True)
        if not r.stdout.strip():
            log("El rebuild ha terminado.")
            break
        # Mostrar progreso cada 5 min
        elapsed = int(time.time() - time.time())  # placeholder
        if int(time.time()) % 300 == 0:
            log("  ...siguiendo en ejecución...")

    # Verificar resultado
    log_file = WORKSPACE / "estado" / "rebuild.log"
    exito = False
    if log_file.exists():
        with open(log_file) as f:
            txt = f.read()
        if "código de salida 0" in txt or "código 0" in txt or "código de salida: 0" in txt:
            exito = True

    if exito:
        log("=== REBUILD COMPLETADO EXITOSAMENTE ===")
        restart_servicios()
        ok, msg = verify_live()
        if ok:
            log(f"✓ {msg}")
        else:
            log(f"⚠ {msg}")
        return 0
    else:
        log("❌ El rebuild NO se completó correctamente")
        return 1

if __name__ == "__main__":
    sys.exit(main())
