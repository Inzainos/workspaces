#!/bin/bash
# Vigila el rebuild: cuando termina, verifica el log y sube los servicios.
# Se corre como oneshot desde un timer cada 15 min; si no hay rebuild, sale.
#
# 2026-10-18 — tres arreglos, todos medidos contra la corrida real:
#   1. AUTO-EMPAREJE: el grep 'rebuild.*activ' calzaba con la PROPIA línea
#      del vigía ('sentinel-omega-rebuild-watch.service loaded activating…')
#      y esperaba 4 h a que terminara ÉL MISMO en cada disparo del timer.
#      Ahora se listan solo las unidades transitorias de rebuild real
#      (la receta 10-09 las llama sentinel-omega-rebuild-<timestamp>) y se
#      excluye explícitamente al propio -watch.
#   2. GLOB RANCIO: solo conocía 'rebuild_post_fixes_*' y
#      'rebuild_recuperacion_*'; los logs reales se llaman rebuild.log,
#      rebuild_YYYYMMDD*.log… Ahora: estado/rebuild*.log menos el watchdog.
#   3. ELIF ROTO: 'grep -q … | tail -5' probaba el código de salida de TAIL
#      (siempre 0) — decía 'con FALLOS' siempre que llegaba a esa rama. Y
#      'FALLO' a secas calza con los cientos de líneas rutinarias
#      'JUEZ: FALLO de X' del entrenamiento; el marcador real de fallo de
#      rebuild_completo.py es '[X] <paso> FALLO:'.

set -u
R=/home/deamon/workspaces

rebuilds_activos() {
    # Unidades de rebuild REALES, activas o arrancando. El propio vigía
    # (sentinel-omega-rebuild-WATCH.service) calza en el glob y se excluye:
    # el estado del watcher no es un rebuild.
    systemctl --user list-units --all --no-pager --no-legend \
        'sentinel-omega-rebuild-*.service' 2>/dev/null \
        | grep -v 'rebuild-watch' \
        | awk '$3 == "active" || $3 == "activating" {print $1}'
}

# ¿hay un rebuild corriendo?
if [ -z "$(rebuilds_activos)" ]; then
    echo "$(date -u +%FT%TZ) sin rebuild en curso — nada que vigilar"
    exit 0
fi

# esperar a que termine (con tope de 4 h)
for i in $(seq 1 960); do
    if [ -z "$(rebuilds_activos)" ]; then
        echo "$(date -u +%FT%TZ) rebuild terminó — verificando y subiendo servicios"
        break
    fi
    sleep 15
done

# verificar el último log de rebuild (cualquier convención de nombre)
LOG=$(ls -t $R/estado/rebuild*.log 2>/dev/null | grep -v 'rebuild_watchdog' | head -1)
if [ -z "$LOG" ]; then
    echo "no se encontró log de rebuild"
    exit 1
fi

echo "verificando $LOG…"
if grep -q "✔ Generar reportes" "$LOG" 2>/dev/null; then
    echo "rebuild COMPLETO según el log"
    # subir servicios en el orden documentado (launcher antes del watchdog,
    # timers al final — AGENTS.md). vigia-sentinel: enabled, pero si la
    # máquina reinició durante el rebuild hay que asegurarlo.
    systemctl --user start sentinel-omega.service vigia-sentinel.service \
        sentinel-omega-dashboard-api.service sentinel-omega-dashboard-web.service \
        sentinel-omega-dashboard.service sentinel-omega-watchdog.service \
        sentinel-omega-rutinas.timer sentinel-omega-mantenimiento.timer \
        sentinel-omega-onnx-retrain.timer sentinel-omega-autofix.timer \
        sos70-descarga.timer
    sleep 5
    # verificar el timer de rutinas (la trampa conocida del infinity)
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
elif grep -qE '\[X\] .* FALLO' "$LOG" 2>/dev/null; then
    echo "rebuild con FALLOS de paso — revisar $LOG (las líneas 'JUEZ: FALLO' del entrenamiento NO cuentan)"
    exit 2
else
    echo "rebuild aún corriendo o estado desconocido — $LOG"
    exit 0
fi
