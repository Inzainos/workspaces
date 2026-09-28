# Operaciones 2026-09-27 (noche) — C

Registro de operaciones del domingo 27 de septiembre de 2026. Horas en CST (UTC-6).
Rama `local/recuperacion-datos-2026-09`, HEAD `d60b3eb`. **Nada de esto está
commiteado todavía**: son cambios en el árbol, aprobados por T, con GO del Capitán
para aplicarlos. Sin push y sin tocar `main`.

Revisa: T.

---

## 1. Un solo Sentinel, como unidad de usuario

- Se encontró un Sentinel de sistema (root, `/etc/systemd/system/sentinel-omega.service`,
  código de las 13:42, `Restart=always`) corriendo junto al de usuario, los dos
  escribiendo en la misma base. Detalle en `deploy/DEPLOY.md`, sección del 27.
- Decisión del Capitán: **se quedan las unidades de usuario** ("por practicidad").
  Las de sistema `sentinel-omega` y `sentinel-omega-watchdog` quedan **enmascaradas**.

### Paquete `install.sh` + unidades (aplicado 20:57, sin commit)

Diff aprobado: `diff_unidad_usuario_sin_dashweb.txt` (T aprobó la versión con
`dashboard-web` fuera). Archivos:

| archivo | cambio |
|---|---|
| `deploy/install.sh` | Instala y habilita solo unidades de usuario; se niega a correr como root; comprueba que las de sistema sigan enmascaradas y no arranca nada si no; sustituye `__REPO_DIR__`, `__RUN_USER__` y `__RUN_UID__` en una sola función y falla si queda alguno; deja las unidades de sistema de los timers renderizadas en `~/.cache/sentinel-omega/system-units/`; `--no-start` para instalar sin arrancar. |
| `deploy/sentinel-omega.service`, `-watchdog`, `-dashboard-api`, `-dashboard-web` | Formato de usuario: `%h`, `WantedBy=default.target`, sin `User=`, límites de arranque en la sección correcta. |
| `deploy/sentinel-omega-mantenimiento.service`, `-onnx-retrain.service` | Siguen siendo de sistema (las dispara su timer), pero corren con `User=__RUN_USER__` y con `XDG_RUNTIME_DIR` y el bus del usuario, para poder hacer `systemctl --user`. El reinicio tras el reentreno es condicional: `systemctl --user is-active --quiet ... && systemctl --user restart ... \|\| true`. |
| `sentinel_omega/infrastructure/watchdog/network_watchdog.py` | Usa `systemctl --user` con una copia del entorno (XDG a partir de `os.getuid()`). Por defecto solo restaura `sentinel-omega`; el dashboard Streamlit :8510 es de sistema y queda fuera. `WATCHDOG_RESTORE_UNITS` permite agregar otras. |
| `sentinel_omega/tests/test_network_watchdog_systemctl_user.py` | 4 tests nuevos. |
| `deploy/DEPLOY.md` | La línea "Pendiente" de la sección del 27 queda como resuelta. |

**`dashboard-web` fuera de `USER_UNITS` por ahora.** La unidad viva arranca con el
npm de Windows (`/mnt/c/.../hermes/node/npm`); la del repo usa `/usr/bin/env npm`,
que puede no estar en el PATH del gestor de usuario. En `install.sh` la línea queda
comentada, así que `install.sh` no toca la unidad viva. La plantilla del repo sí
cambió, pero no se instala. Pasarla a un npm de Linux queda para otra sesión.

Verificación al aplicar: `git apply --check` OK, `bash -n deploy/install.sh` OK,
tests nuevos en verde.

---

## 2. ONNX entrena solo con filas en vivo (aplicado 20:57, sin commit)

Diff aprobado: `diff_onnx_en_vivo.txt`.

- `sentinel_omega/models/train_onnx_from_db.py`: nueva `_filtro_juez_en_vivo(conn)`.
  Agrega `AND COALESCE(en_vivo,1)=1` solo si la columna existe. Si no existe,
  avisa con `TBL_JUEZ_AUDITORIA sin en_vivo: se entrena con todas las filas viva`.
- `sentinel_omega/tests/test_onnx_entrena_solo_en_vivo.py`: 4 tests.
- Conteo esperado de etiquetas: **23 283** con filtro, frente a 23 670 sin él
  (387 menos: 378 del marcado de hoy y 9 del 25-sep, ids 6373641–6373649).
- El paso ONNX encadenado al rebuild arranca como proceso nuevo, así que ya usa
  el filtro. G revisa el conteo en el log; si salen 23 670, se reentrena a mano.

---

## 3. Schumann: el 8.26 / 21.46 venía de una imagen vieja (aplicado ~20:30, sin commit)

**Causa.** `infrastructure/api/schumann.py` cuenta píxeles en
`sosrff.tsu.ru/new/shm.jpg`, que es estática (Last-Modified 1-sep-2025). Siempre
daba 21.46 % = 8.26 Hz (25.0 con la escala vieja ×0.8). No era una lectura en vivo.

**Arreglo** (diff `diff_schumann_wpc.txt`, aprobado por T; solo `.py`):
- Rechaza imágenes sin Last-Modified o con más de 6 horas.
- Rechaza repetir la última lectura en vivo de una hora anterior.
- `fetchers.SchumannData.es_locf` nuevo; `data_pipeline` guarda
  `geo_schumann_deviation = None` cuando la serie es LOCF (dato arrastrado).
- 77 de 77 tests relacionados en verde.
- Entra en vigor al reiniciar. Al arrancar, G busca en el log `is not a live reading`
  y que las filas PREC nuevas salgan NULL/NULL.

**Marcado pendiente (después del arranque, con GO ya dado):**
- `marcar_schumann_vivo_wpc.py --apply`: marca `en_vivo=0` las filas 534 y 541 de
  `tbl_schumann_vivo` (8.26/21.46). Respaldo `_pre_marcar_schumann_vivo_wpc`;
  aborta si no encuentra exactamente 2 filas. Va justo después del arranque,
  porque `_schumann_from_db` promedia las filas `en_vivo=1`.
- PREC: extender `marcar_prec_schumann_falso.py` a las 983 filas de hoy
  (823 con 8.26/21.46, ids 11114–11936; 160 con 25.0/21.46, ids 38–8466) más las
  nuevas desde 12345 hasta un tope fijado después del arranque. Solo `en_vivo=0`,
  respaldo antes, T revisa y luego se aplica.

---

## 4. Archivos de root y timer de mantenimiento

- Había **2 915** archivos de root bajo el repo (lista en
  `Temp\omega_diag\usr2_root_owned_files.txt`): el log, 331 de `data/cache` (FRP del
  pipeline vivo), 169 reportes en `estado/historial/2026/09` (de la unidad `rutinas`
  que corre como root) y unos 2 400 `.pyc`.
- 20:58, el Capitán corrió:
  `sudo chown -R deamon:deamon /home/deamon/workspaces/sentinel_omega && sudo systemctl stop sentinel-omega-mantenimiento.timer`
  Resultado: `0` archivos de root en `sentinel_omega` y el timer `inactive`.
- **El timer de mantenimiento está parado esta noche.** Su ExecStart efectivo (por
  `dry-run.conf`) es `launcher.py --disciplina --barrido --dry-run`. `--dry-run`
  solo quita Telegram: **sigue escribiendo en la base, como root, a las 00:00**.
  Se reactiva cuando se reinstale como `User=deamon` (punto 5).

---

## 5. Pendientes que necesitan sudo (Capitán)

1. **Antes del 4 de octubre** (el timer de `onnx-retrain` corre el 4-oct a las 03:07):
   reinstalar `sentinel-omega-mantenimiento.service` y
   `sentinel-omega-onnx-retrain.service` desde `~/.cache/sentinel-omega/system-units/`
   (las deja ahí `install.sh`) y `sudo systemctl daemon-reload`. La versión viva de
   `onnx-retrain` intenta reiniciar la unidad de sistema enmascarada y falla sin avisar.
   El override `dry-run.conf` seguirá reemplazando ExecStart tras reinstalar.
   Después, reactivar `sentinel-omega-mantenimiento.timer`.
2. **Unidad `rutinas` que corre como root**: escribe los reportes de
   `estado/historial`. Pasarla a usuario o a `User=deamon`.
3. `.venv` y `estado/historial` siguen con archivos de root; no impiden arrancar.

## 6. Otros pendientes de operaciones

- Enlaces muertos en `~/.config/systemd/user/multi-user.target.wants/`, entre ellos
  `sentinel-omega-scheduler.service` (un segundo launcher). Limpiar.
- Las unidades de usuario vivas dicen `WantedBy=multi-user.target` y funcionan solo
  por enlaces hechos a mano en `default.target.wants`; `install.sh --no-start` lo corrige.
- Permisos de `sos70-descarga.*` (escribibles por cualquiera).
- `consenso_vigilante.py:895` no oculta el token en el log.
- Retirar `launcher_fixed.py`.

---

## Orden después de la cadena rebuild + ONNX

1. G revisa en el log del ONNX: 23 283 etiquetas (si 23 670, reentrena a mano).
2. G corre `bash deploy/install.sh --no-start` y arranca con
   `systemctl --user start sentinel-omega sentinel-omega-watchdog`.
3. G confirma la línea de Schumann y PREC en NULL.
4. C marca las filas 534 y 541 (`marcar_schumann_vivo_wpc.py --apply`).
5. C prepara el marcado de PREC con tope; T revisa; se aplica con respaldo.
6. Capitán: reinstalación sudo de los timers (punto 5) antes del 4-oct.
