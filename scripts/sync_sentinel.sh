#!/bin/bash
# sync_sentinel.sh - Sincroniza los worktrees de Sentinel Omega con origin/main

set -e

# repo, ruta, rama
declare -A ENTORNOS=(
  ["PROD"]="/home/deamon/workspaces:main"
  ["DEV"]="/home/deamon/workspaces-dev:dev"
  ["TEST"]="/home/deamon/workspaces-test:test"
)

for NOMBRE in "${!ENTORNOS[@]}"; do
  DIR="${ENTORNOS[$NOMBRE]%%:*}"
  RAMA="${ENTORNOS[$NOMBRE]##*:}"

  echo "=============================="
  echo "[$NOMBRE] $DIR (rama: $RAMA)"
  echo "=============================="

  if [ ! -e "$DIR/.git" ]; then
    echo "⚠️  $DIR no existe o no es un worktree válido. Saltando."
    continue
  fi

  cd "$DIR"
  find . -name "*:Zone.Identifier" -delete 2>/dev/null || true

  if [ -n "$(git status --porcelain)" ]; then
    echo "Guardando cambios locales en stash..."
    git stash push -m "auto-stash $NOMBRE $(date +%F_%T)"
  fi

  git fetch origin

  if [ "$RAMA" == "main" ]; then
    # PROD: pull directo sobre main
    git checkout main
    git pull origin main
  else
    # DEV/TEST: mantener su rama propia, traer cambios de main por merge
    git checkout "$RAMA"
    git merge origin/main -m "sync: merge origin/main into $RAMA ($(date +%F))"
  fi

  if [ -d ".venv" ]; then
    echo "Actualizando dependencias..."
    .venv/bin/pip install -r sentinel_omega/requirements.txt --quiet
  fi

  echo "✅ $NOMBRE sincronizado."
done

echo ""
echo "Sync completo."
echo "⚠️  Si PROD tuvo cambios, reinicia el servicio manualmente:"
echo "   sudo systemctl restart sentinel-omega.service"