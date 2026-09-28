# Despliegue de Sentinel Omega — servidor permanente

Guía para dejar a Roy corriendo 24/7 en tu servidor (Linux) o en la MSI Katana (Windows).

## Linux (recomendado — systemd con auto-restart)

```bash
# 1. Clonar (o git pull si ya existe)
git clone https://github.com/Inzainos/workspaces.git sentinel-omega
cd sentinel-omega

# 2. Instalar (crea venv, dependencias y las units de USUARIO systemd; sin sudo)
bash deploy/install.sh

# 3. Poner tus keys
nano deploy/.env

# 4. UNA SOLA VEZ: cargar 30 años + entrenar firmas (tarda ~30-60 min)
.venv/bin/python sentinel_omega/launcher.py --backcast --entrenar --once --dry-run

# 5. Arrancar 24/7 (install.sh ya hace enable --now; esto es por si usaste --no-start)
systemctl --user enable --now sentinel-omega sentinel-omega-watchdog
sudo loginctl enable-linger $USER   # una vez, si install.sh no pudo (polkit)
```

Sentinel corre como **units de usuario** (`~/.config/systemd/user/`,
`WantedBy=default.target`, linger activo). Las units de sistema
`/etc/systemd/system/sentinel-omega{,-watchdog}.service` deben quedar
**enmascaradas** (`sudo systemctl mask sentinel-omega sentinel-omega-watchdog`);
`install.sh` avisa y no arranca nada si no lo estan. Los timers
(mantenimiento 00:00, retrain ONNX) siguen siendo units de sistema.

El servicio se reinicia solo si el proceso muere y arranca solo al prender el servidor.

### Operación diaria

| Qué | Comando |
|---|---|
| Estado | `systemctl --user status sentinel-omega` |
| Logs en vivo | `journalctl --user -u sentinel-omega -f` |
| Actualizar versión | `git pull && systemctl --user restart sentinel-omega` |
| Detener | `systemctl --user stop sentinel-omega` |
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

## Desde la iPad (o cualquier dispositivo)

La iPad no corre el servidor, pero es el centro de mando:

```bash
# En el servidor, una vez (dashboard 24/7 en el puerto 8501):
sudo cp deploy/sentinel-omega-dashboard.service /etc/systemd/system/
sudo sed -i "s|__REPO_DIR__|$(pwd)|g" /etc/systemd/system/sentinel-omega-dashboard.service
sudo systemctl daemon-reload && sudo systemctl enable --now sentinel-omega-dashboard
```

| En la iPad | Para qué |
|---|---|
| **Safari** → `http://IP-DEL-SERVIDOR:8501` | Dashboard completo (9 pestañas, mapas, fantasma, muro) |
| **Telegram** | Alertas rojas/amarillas al instante |
| **Termius** (o Blink) → SSH al servidor | `journalctl --user -u sentinel-omega -f`, reiniciar, actualizar |
| **Working Copy** | Ver/editar el repo, pull de versiones |

> **Fuera de casa**: instala [Tailscale](https://tailscale.com) (gratis) en el
> servidor y en la iPad — te da una IP privada segura para llegar al dashboard
> y SSH desde cualquier red, sin abrir puertos al internet.

## Rutinas 24/7 sin servidor (Roy Vigilante — GitHub Actions)

Si no hay servidor propio, `.github/workflows/roy-vigilante.yml` corre el
sistema completo en Actions (el cron dispara en `main`). Hora MX = UTC-6:

| Ritmo | Tarea |
|---|---|
| Cada 2 h | Ciclo del Padre (status + registro + cimática) |
| Cada 4 h | El Juez verifica real vs predicción (USGS, verdad por fila) |
| Cada 6 h | Reporte ejecutivo → correo |
| 12am/12pm | Comparativo contra el día anterior (con gráfica) |
| Dom 12:15pm | Reporte semanal |
| Fin de mes 12:30pm | Reporte mensual |
| Cada corrida | Despacho del outbox de correo |

**Correo (canal de alertas, sin Telegram)** — secrets del repo
(Settings → Secrets and variables → Actions):
- `SMTP_USER` + `SMTP_PASS` — cuenta emisora (app password de Gmail:
  myaccount.google.com/apppasswords)
- `CORREO_DESTINO` — opcional (default elan.zainos.corona@gmail.com)

Sin credenciales los correos quedan PENDIENTES en `tbl_correo_salida`
(no se pierden ni se fingen enviados); los reportes siguen publicándose
al repo en `estado/` como siempre.

## Notas

- **Telegram está en pausa** (el canal es correo); el código sigue ahí — con
  `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` se reactivan las alertas al celular.
- **La base de datos** vive en `sentinel_omega/data/SENTINEL_OMEGA_PRO.db`.
  Respáldala si re-instalas: contiene el backcast de 30 años, las firmas
  entrenadas y el ledger del Juez.
- El flag `--backcast` también corre el backfill secundario (SO2 volcánico
  NASA + BTC Yahoo). Todo es idempotente: re-correrlo no duplica datos.
- **Nunca** pongas keys en el código ni subas `deploy/.env` a git.

---

## 2026-09-27 — En ESTA máquina manda la unidad de USUARIO (los `sudo systemctl` de arriba no aplican)

Decisión del operador, **por practicidad: arrancar y parar sin sudo.** El día 27 se
descubrió que había **dos** `sentinel-omega.service` activos a la vez --- uno de
sistema (root) y uno de usuario (deamon) --- ciclando los dos contra la misma base.
Se delató en la auditoría del Juez: veredictos alternándose cada ~45 s, unos con el
tapón de rasgos con fuga y otros sin él. Consecuencia colateral: los conteos
absolutos de ciclos de esos días están inflados (pueden ser dos filas por ciclo).

Estado vigente:

| unidad | estado |
|---|---|
| `sentinel-omega` / `-watchdog` (sistema) | **masked** |
| `sentinel-omega` / `-watchdog` (`--user`) | **enabled**, con `Linger=yes` |

`masked` y no `disable` a propósito: así no las puede levantar el watchdog ni un
`Requires=` de otra unidad. Con `Linger=yes` las de usuario sobreviven al cierre de
sesión y al reinicio, así que la operación 24/7 no depende de una sesión abierta.

**Comandos vigentes (sin sudo):**

```bash
systemctl --user start  sentinel-omega.service sentinel-omega-watchdog.service
systemctl --user stop   sentinel-omega.service sentinel-omega-watchdog.service
systemctl --user status sentinel-omega.service
journalctl --user -u sentinel-omega -f
```

**Efecto secundario bueno:** el launcher corre como `deamon`, así que el pid y el
log dejan de ser de root. Eso retira el defecto del 2026-09-01
(`_check_already_running` fallando con `PermissionError`) y el caso del log rotado
ilegible. El manejo fail-soft del `RotatingFileHandler` en `launcher.py` se queda,
para cubrir que alguien lo arranque con sudo.

**Resuelto (diff unidad de usuario):** `deploy/install.sh` ya instala y
habilita solo las unidades de USUARIO (sin sudo), no instala las de sistema
`sentinel-omega{,-watchdog}` y avisa/no arranca si no están enmascaradas.

### 2026-09-27 (noche) — Instalar con el `install.sh` nuevo

`install.sh` ya no usa sudo. Se niega a correr como root y no arranca nada si las
unidades de sistema `sentinel-omega{,-watchdog}` no están enmascaradas.

```bash
bash deploy/install.sh --no-start        # instala las units de usuario, sin arrancar
systemctl --user start sentinel-omega sentinel-omega-watchdog
```

- `dashboard-web` **no** está en `USER_UNITS` por ahora: la unidad viva usa el npm de
  Windows y `install.sh` no la toca.
- Los timers `mantenimiento` y `onnx-retrain` siguen siendo de sistema, pero ahora
  corren con `User=` del repo. `install.sh` deja las unidades listas en
  `~/.cache/sentinel-omega/system-units/`; instalarlas requiere sudo:

```bash
sudo cp ~/.cache/sentinel-omega/system-units/sentinel-omega-{mantenimiento,onnx-retrain}.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start sentinel-omega-mantenimiento.timer   # parado desde el 27-sep 20:58
```

  Hacerlo **antes del 4-oct 03:07** (siguiente reentreno). Detalle y pendientes en
  `estado/OPERACIONES_2026-09-27.md`.
