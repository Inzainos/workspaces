#!/bin/bash
# Vigila el rebuild: cuando termina, verifica el log y sube los servicios.
# Se corre como oneshot desde un timer cada 15 min; si no hay rebuild, sale.
set -u
R=/home/deamon/workspaces

# ¿hay un rebuild corriendo?
if ! systemctl --user list-units --all --no-pager --no-legend 2>/dev/null | grep -q "rebuild.*activ"; then
    echo "$(date -u +%FT%TZ) sin rebuild en curso — nada que vigilar"
    exit 0
fi

# esperar a que termine (con tope de 4 h)
for i in $(seq 1 960); do
    if ! systemctl --user is-active --quiet "sentinel-omega-rebuild-*.service" 2>/dev/null \
       && ! systemctl --user list-units --all --no-pager --no-legend 2>/dev/null | grep -q "rebuild.*activ"; then
        echo "$(date -u +%FT%TZ) rebuild terminó — verificando y subiendo servicios"
        break
    fi
    sleep 15
done

# verificar el último log de rebuild
LOG=$(ls -t $R/estado/rebuild_post_fixes_*.log $R/estado/rebuild_recuperacion_*.log 2>/dev/null | head -1)
if [ -z "$LOG" ]; then
    echo "no se encontró log de rebuild"
    exit 1
fi

echo "verificando $LOG…"
if grep -q "✔ Generar reportes" "$LOG" 2>/dev/null; then
    echo "rebuild COMPLETO según el log"
    # subir servicios en el orden documentado
    systemctl --user start sentinel-omega.service \
        sentinel-omega-dashboard-api.service sentinel-omega-dashboard-web.service \
        sentinel-omega-dashboard.service sentinel-omega-watchdog.service \
        sentinel-omega-rutinas.timer sentinel-omega-mantenimiento.timer \
        sentinel-omega-onnx-retrain.timer
    sleep 5
    # verificar el timer de rutinas (la trampa conocida)
    NEXT=$(systemctl --user show sentinel-omega-rutinas.timer -p NextElapseUSecMonotonic --value)
    if echo "$NEXT" | grep -q "infinity"; then
        echo "timer de rutinas con infinity — reanclando"
        systemctl --user start sentinel-omega-rutinas.service
    fi
    echo "servicios arriba, timer verificado"
    # correr la verificación post-rebuild
    $R/.venv/bin/python $R/deploy/verificar_post_rebuild.py >> $R/sentinel_omega/logs/post_rebuild_verify.log 2>&1
    echo "verificación post-rebuild: ver log"
    exit 0
elif grep -q "FALLO\|Error\|Traceback" "$LOG" | tail -5; then
    echo "rebuild con FALLOS — revisar $LOG"
    exit 2
else
    echo "rebuild aún corriendo o estado desconocido — $LOG"
    exit 0
fi
