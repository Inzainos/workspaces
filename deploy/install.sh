#!/usr/bin/env bash
# Sentinel Omega — instalador para servidor Linux (systemd)
# Uso:  bash deploy/install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
echo ">> Instalando Sentinel Omega en $REPO_DIR"

# 1. Entorno virtual + dependencias
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r sentinel_omega/requirements.txt -q
echo ">> Dependencias instaladas."

# 2. Variables de entorno
if [ ! -f deploy/.env ]; then
    cp deploy/.env.example deploy/.env
    echo ""
    echo "⚠️  EDITA deploy/.env CON TUS KEYS antes de continuar:"
    echo "    nano deploy/.env"
    echo ""
fi

# 3. Servicio systemd (auto-arranque + auto-restart)
sudo cp deploy/sentinel-omega.service /etc/systemd/system/sentinel-omega.service
sudo sed -i "s|__REPO_DIR__|$REPO_DIR|g" /etc/systemd/system/sentinel-omega.service
sudo systemctl daemon-reload
echo ">> Servicio systemd instalado."

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  SIGUIENTE (una sola vez — carga 30 años y entrena):"
echo "    .venv/bin/python sentinel_omega/launcher.py --backcast --entrenar --once --dry-run"
echo ""
echo "  DESPUÉS (arrancar 24/7):"
echo "    sudo systemctl enable --now sentinel-omega"
echo ""
echo "  Ver estado / logs en vivo:"
echo "    systemctl status sentinel-omega"
echo "    journalctl -u sentinel-omega -f"
echo ""
echo "  Actualizar a nueva versión:"
echo "    git pull && sudo systemctl restart sentinel-omega"
echo "═══════════════════════════════════════════════════════════"
