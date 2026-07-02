# Despliegue de Sentinel Omega — servidor permanente

Guía para dejar a Roy corriendo 24/7 en tu servidor (Linux) o en la MSI Katana (Windows).

## Linux (recomendado — systemd con auto-restart)

```bash
# 1. Clonar (o git pull si ya existe)
git clone https://github.com/Inzainos/workspaces.git sentinel-omega
cd sentinel-omega

# 2. Instalar (crea venv, dependencias y el servicio)
bash deploy/install.sh

# 3. Poner tus keys
nano deploy/.env

# 4. UNA SOLA VEZ: cargar 30 años + entrenar firmas (tarda ~30-60 min)
.venv/bin/python sentinel_omega/launcher.py --backcast --entrenar --once --dry-run

# 5. Arrancar 24/7
sudo systemctl enable --now sentinel-omega
```

El servicio se reinicia solo si el proceso muere y arranca solo al prender el servidor.

### Operación diaria

| Qué | Comando |
|---|---|
| Estado | `systemctl status sentinel-omega` |
| Logs en vivo | `journalctl -u sentinel-omega -f` |
| Actualizar versión | `git pull && sudo systemctl restart sentinel-omega` |
| Detener | `sudo systemctl stop sentinel-omega` |
| Dashboard | `.venv/bin/streamlit run sentinel_omega/infrastructure/dashboard/app.py` |

## Windows (MSI Katana)

```bat
git clone https://github.com/Inzainos/workspaces.git sentinel-omega
cd sentinel-omega
python -m venv .venv
.venv\Scripts\pip install -r sentinel_omega\requirements.txt
REM Pon tus keys como variables de entorno de Windows (Panel de control
REM → Sistema → Variables de entorno), los nombres están en deploy\.env.example
.venv\Scripts\python sentinel_omega\launcher.py --backcast --entrenar --once --dry-run
deploy\run_windows.bat
```

Para auto-arranque: agrega `deploy\run_windows.bat` al Programador de Tareas
(al iniciar sesión) o a la carpeta de Inicio.

## Notas

- **Sin Telegram configurado** el sistema corre igual (dry-run automático);
  con `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` las alertas llegan al celular.
- **La base de datos** vive en `sentinel_omega/data/SENTINEL_OMEGA_PRO.db`.
  Respáldala si re-instalas: contiene el backcast de 30 años, las firmas
  entrenadas y el ledger del Juez.
- El flag `--backcast` también corre el backfill secundario (SO2 volcánico
  NASA + BTC Yahoo). Todo es idempotente: re-correrlo no duplica datos.
- **Nunca** pongas keys en el código ni subas `deploy/.env` a git.
