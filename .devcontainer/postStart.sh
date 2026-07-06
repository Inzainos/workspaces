#!/usr/bin/env bash
set -e

echo "============================================"
echo "  SENTINEL OMEGA — Codespace Auto-Launch"
echo "============================================"

# ── Instalar dependencias ───────────────────────────────────────
echo "[1/4] Instalando dependencias..."
pip install --quiet -r sentinel_omega/requirements.txt 2>/dev/null || \
  pip install --quiet requests ephem numpy pandas scikit-learn 2>/dev/null

# ── Backcast (solo si la DB no existe o está vacía) ─────────────
DB_PATH="sentinel_omega/data/sentinel.db"
if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
  echo "[2/4] DB no encontrada — corriendo backcast histórico..."
  python sentinel_omega/launcher.py --backcast --entrenar --disciplina --reporte --once \
    >> sentinel_omega/data/codespace_init.log 2>&1 &
  echo "  Backcast + entrenamiento corriendo en background (PID $!)"
else
  echo "[2/4] DB existente — saltando backcast."
  python sentinel_omega/launcher.py --entrenar --reporte --once \
    >> sentinel_omega/data/codespace_init.log 2>&1 &
  echo "  Entrenamiento + reporte corriendo en background (PID $!)"
fi

# ── Esperar a que termine el batch antes de ciclos live ─────────
echo "[3/4] Esperando batch inicial..."
wait

# ── Arrancar ciclos continuos en background ─────────────────────
echo "[4/4] Arrancando ciclos live continuos..."
nohup python sentinel_omega/launcher.py \
  >> sentinel_omega/data/sentinel_omega.log 2>&1 &
echo "  Sentinel Omega ONLINE (PID $!) — ciclos corriendo."
echo "  Logs: sentinel_omega/data/sentinel_omega.log"
echo "  Reporte: sentinel_omega/data/reporte_general_*.txt"
echo "============================================"
