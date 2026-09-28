#!/usr/bin/env bash
# Sentinel Omega — instalador Linux (systemd de USUARIO + linger)
# Uso:  bash deploy/install.sh [--no-venv] [--no-start]
#   --no-venv   no crea/actualiza .venv ni dependencias
#   --no-start  instala y habilita las units pero no las arranca (sin --now)
#
# Decision vigente: Sentinel corre como units de USUARIO de systemd
# (~/.config/systemd/user/, WantedBy=default.target, linger activo).
# Las units de SISTEMA /etc/systemd/system/sentinel-omega{,-watchdog}.service
# deben quedar ENMASCARADAS (-> /dev/null) para no tener dos launchers.
# Este script NO usa sudo para instalar units; sudo solo puede hacer falta
# para `loginctl enable-linger` si polkit no lo permite al propio usuario.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="$(id -un)"
RUN_UID="$(id -u)"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
# `systemctl --user` necesita el runtime dir del usuario (ssh/cron sin sesion)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$RUN_UID}"

DO_VENV=1
DO_START=1
for arg in "$@"; do
    case "$arg" in
        --no-venv)  DO_VENV=0 ;;
        --no-start) DO_START=0 ;;
        -h|--help)  sed -n '2,12p' "$0"; exit 0 ;;
        *) echo "argumento desconocido: $arg" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    echo "!! No corras install.sh como root/sudo: las units son de USUARIO." >&2
    exit 1
fi

cd "$REPO_DIR"
echo ">> Instalando Sentinel Omega en $REPO_DIR (usuario $RUN_USER)"

if [ "$DO_VENV" -eq 1 ]; then
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r sentinel_omega/requirements.txt -q
    .venv/bin/pip install "onnxruntime>=1.14" "scikit-learn>=1.3" "skl2onnx>=1.16" "ephem>=4.1" -q 2>/dev/null || true
    echo ">> Dependencias instaladas."
fi

if [ ! -f deploy/.env ]; then
    if [ -f deploy/.env.example ]; then
        cp deploy/.env.example deploy/.env
    else
        touch deploy/.env
    fi
    chmod 600 deploy/.env
    echo ""
    echo "⚠️  EDITA deploy/.env CON TUS KEYS antes de continuar:"
    echo "    nano deploy/.env"
    echo ""
fi

# Units de usuario que corren en vivo (instaladas en $USER_UNIT_DIR)
USER_UNITS=(
    sentinel-omega.service
    sentinel-omega-watchdog.service
    sentinel-omega-dashboard-api.service
    # sentinel-omega-dashboard-web.service  # fuera por ahora: la viva usa el npm de Windows
)
# Units de SISTEMA que deben estar enmascaradas (si no, habria doble launcher)
MASKED_SYSTEM_UNITS=(
    sentinel-omega.service
    sentinel-omega-watchdog.service
)

# --- Guardia: las units de sistema deben seguir enmascaradas ---------------
check_system_units_masked() {
    local u path state rc=0
    for u in "${MASKED_SYSTEM_UNITS[@]}"; do
        path="/etc/systemd/system/$u"
        state="$(systemctl is-enabled "$u" 2>/dev/null || true)"
        if [ -L "$path" ] && [ "$(readlink -f "$path")" = "/dev/null" ]; then
            echo "   OK  $path enmascarada (-> /dev/null)"
        elif [ -e "$path" ] || [ -L "$path" ]; then
            echo "!! AVISO: $path existe y NO esta enmascarada (estado: ${state:-?})."
            echo "   Correria un segundo Sentinel como root junto a la unit de usuario."
            echo "   Corrige (requiere sudo, manual):"
            echo "     sudo systemctl disable --now $u && sudo systemctl mask $u"
            rc=1
        elif [ "$state" = "masked" ]; then
            echo "   OK  $u enmascarada"
        else
            echo "   (i) $path no existe. Recomendado (sudo, manual): sudo systemctl mask $u"
        fi
    done
    return $rc
}

echo ">> Verificando units de sistema enmascaradas..."
if ! check_system_units_masked; then
    echo "!! No se arrancaran las units (--now) hasta que las de sistema esten enmascaradas."
    DO_START=0
fi

# --- Render de placeholders (una sola funcion para units de usuario y sistema)
#   %h/workspaces -> REPO_DIR (solo si el repo no esta en ~/workspaces)
#   __REPO_DIR__ -> REPO_DIR, __RUN_USER__ -> usuario, __RUN_UID__ -> `id -u`
render_unit() {
    local src="$1" out="$2"
    local sed_args=(-e "s|__REPO_DIR__|$REPO_DIR|g"
                    -e "s|__RUN_USER__|$RUN_USER|g"
                    -e "s|__RUN_UID__|$RUN_UID|g")
    if [ "$REPO_DIR" != "$HOME/workspaces" ]; then
        sed_args+=(-e "s|%h/workspaces|$REPO_DIR|g")
    fi
    sed "${sed_args[@]}" "$src" > "$out"
    if grep -qE '__[A-Z_]+__' "$out"; then
        echo "!! $src: quedan placeholders sin sustituir:" >&2
        grep -nE '__[A-Z_]+__' "$out" >&2
        return 1
    fi
}

# --- Instalar units de usuario ---------------------------------------------
install_user_unit() {
    local name="$1"
    local src="deploy/$name"
    local dst="$USER_UNIT_DIR/$name"
    local tmp
    tmp="$(mktemp)"
    render_unit "$src" "$tmp"
    if [ -f "$dst" ] && ! cmp -s "$tmp" "$dst"; then
        cp -p "$dst" "$dst.bak.$(date +%Y%m%d_%H%M%S)"
    fi
    install -m 0644 "$tmp" "$dst"
    rm -f "$tmp"
    # multi-user.target no existe en el manager de usuario: limpiar enlace viejo
    rm -f "$USER_UNIT_DIR/multi-user.target.wants/$name"
    echo "   instalado $dst"
}

echo ">> Instalando units de usuario en $USER_UNIT_DIR ..."
mkdir -p "$USER_UNIT_DIR"
for u in "${USER_UNITS[@]}"; do
    install_user_unit "$u"
done

systemctl --user daemon-reload
echo ">> systemctl --user daemon-reload OK."

for u in "${USER_UNITS[@]}"; do
    if [ "$DO_START" -eq 1 ]; then
        systemctl --user enable --now "$u" \
            && echo "   enable --now $u" \
            || echo "!! fallo enable --now $u (ver: journalctl --user -u $u -n 50)"
    else
        systemctl --user enable "$u" \
            && echo "   enable $u (sin arrancar)" \
            || echo "!! fallo enable $u"
    fi
done

# --- Linger: que el manager de usuario arranque en boot sin sesion ---------
echo ">> Linger para $RUN_USER ..."
if [ "$(loginctl show-user "$RUN_USER" -p Linger --value 2>/dev/null || true)" = "yes" ]; then
    echo "   OK  linger ya activo"
elif loginctl enable-linger "$RUN_USER" 2>/dev/null; then
    echo "   OK  linger activado"
elif command -v sudo >/dev/null 2>&1 && sudo -n loginctl enable-linger "$RUN_USER" 2>/dev/null; then
    echo "   OK  linger activado (sudo)"
else
    echo "!! No se pudo activar linger (polkit lo niega sin privilegios)."
    echo "   Ejecutalo a mano una vez:  sudo loginctl enable-linger $RUN_USER"
    echo "   Sin linger, las units de usuario solo corren con una sesion abierta."
fi

# --- Timer de mantenimiento: se mantiene como unit de SISTEMA -------------
# deploy/sentinel-omega-mantenimiento.{service,timer} (OnCalendar=daily = 00:00
# hora local) se instala como unit de SISTEMA; este script no la toca.
if [ -f "$USER_UNIT_DIR/sentinel-omega-mantenimiento.timer" ] \
   && systemctl --user is-enabled --quiet sentinel-omega-mantenimiento.timer 2>/dev/null; then
    echo "!! AVISO: sentinel-omega-mantenimiento.timer esta habilitado como unit de USUARIO;"
    echo "   duplica al timer de sistema (00:00). Deshabilitalo:"
    echo "     systemctl --user disable --now sentinel-omega-mantenimiento.timer"
fi

# --- Units de SISTEMA (timers): solo se RENDERIZAN; instalarlas es manual --
SYSTEM_UNITS=(
    sentinel-omega-mantenimiento.service
    sentinel-omega-mantenimiento.timer
    sentinel-omega-onnx-retrain.service
    sentinel-omega-onnx-retrain.timer
)
RENDER_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sentinel-omega/system-units"
mkdir -p "$RENDER_DIR"
for u in "${SYSTEM_UNITS[@]}"; do
    render_unit "deploy/$u" "$RENDER_DIR/$u"
done
echo ">> Units de sistema renderizadas (User=$RUN_USER, uid $RUN_UID) en $RENDER_DIR"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  BOOTSTRAP (una sola vez — carga 30 años y entrena):"
echo "    .venv/bin/python sentinel_omega/launcher.py \\"
echo "        --backcast --entrenar --entrenar-onnx --once --dry-run"
echo ""
echo "  UNITS DE USUARIO (sin sudo):"
echo "    systemctl --user status sentinel-omega sentinel-omega-watchdog"
echo "    systemctl --user restart sentinel-omega"
echo "    journalctl --user -u sentinel-omega -f"
echo ""
echo "  UNITS DE SISTEMA (timers; corren como User=$RUN_USER; instalacion manual con sudo):"
echo "    # ya renderizadas (sin placeholders) en $RENDER_DIR"
echo "    sudo install -m 0644 $RENDER_DIR/sentinel-omega-mantenimiento.{service,timer} \\"
echo "        $RENDER_DIR/sentinel-omega-onnx-retrain.{service,timer} /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now sentinel-omega-mantenimiento.timer   # diario 00:00"
echo "    sudo systemctl enable --now sentinel-omega-onnx-retrain.timer    # domingos 03:00"
echo "    # NUNCA instalar deploy/sentinel-omega{,-watchdog}.service en /etc/systemd/system"
echo ""
echo "  VER TIMERS / LOGS:"
echo "    systemctl list-timers 'sentinel-omega*'"
echo "    journalctl -u sentinel-omega-mantenimiento -n 50"
echo ""
echo "  ALTERNATIVA CRON (si no usas timers):"
echo "    sed \"s|__REPO_DIR__|$REPO_DIR|g\" deploy/crontab.example"
echo "    crontab -e   # pegar la línea generada"
echo "═══════════════════════════════════════════════════════════"
