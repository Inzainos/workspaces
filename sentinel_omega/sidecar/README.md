# Vigía de Sentinel Omega — dead man's switch (sidecar Elixir)

**Qué es:** un sidecar independiente que vigila que el ciclo del launcher de
Sentinel Omega (`launcher.py`, ciclo cada 300 s) esté ocurriendo de verdad. Es
el patrón *watching the watcher*, en un runtime distinto (BEAM) a propósito:
si algo rompe el ecosistema Python, el aviso lo emite este proceso.

## Por qué existe

- El ciclo del launcher **no deja huella confiable en la DB**: `sentinel.db`
  existe pero `insert_ciclo` cae en un `try/rescue` silencioso (`tbl_ciclos`
  no se popula), así que `SELECT MAX(ts)` no sirve de heartbeat.
- El latido real es el log: `data/sentinel_omega.log` y sus líneas
  `--- Starting cycle #N ---` (hora local).
- Un launcher parado no avisa de su propia parada; este vigía sí.

## Cómo funciona

- Lee la última línea `--- Starting cycle #N ---` del log (leo el archivo
  entero, no `tail -n 300`: durante ciclos con mucha salida la línea del ciclo
  puede quedar fuera de las últimas 300 líneas — ya mordió ese punto ciego).
- Chequea cada 5 min (`VIGIA_CHECK_INTERVAL_MINUTES`).
- **Alerta** si el último ciclo supera los 15 min
  (`VIGIA_STALE_AFTER_MINUTES`, = 3 ciclos perdidos; umbral medido sobre la
  cadencia real de 300 s) o si el log no existe / no tiene líneas de ciclo.
- **Re-alerta** cada 2 h mientras siga parado, y avisa la **recuperación**.
- **Pausa del sistema:** si el propio vigía estuvo congelado un gap > 2.5×
  su intervalo (WSL2 duerme con Windows), la falta de ciclos está explicada
  por la pausa — no alerta, solo deja registro del reinicio.
- Telegram: **bot de Sentinel** (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`,
  inyectados por el unit de systemd vía `EnvironmentFile` — el token viaja en
  el entorno, **no** vive en el estado del proceso ni en crash dumps). Mensaje
  en texto plano, sin `parse_mode`.
- `mix test` **no arranca el vigía** (`:ignore` en `init`): un test que
  coincidiera con un ciclo parado intentaría un envío REAL de Telegram.

## Operación

```bash
# Estado
systemctl --user status vigia-sentinel.service
cat sidecar/logs/vigia_sentinel.log
cat sidecar/state.json

# Reiniciar tras tocar código
cd sidecar/vigia_sentinel && mix test && systemctl --user restart vigia-sentinel.service

# Simular una caída sin tocar producción (dry-run + copia del log)
cp data/sentinel_omega.log /tmp/hb.log
# envejecer el último ciclo en la copia...
VIGIA_LOG_PATH=/tmp/hb.log VIGIA_STATE_PATH=/tmp/st VIGIA_LOG_PATH_VIGIA=/tmp/lg \
  VIGIA_DRY_RUN=1 VIGIA_CHECK_INTERVAL_MINUTES=1 mix run --no-halt
```

Variables (`VIGIA_*`, con default): `LOG_PATH`,
`ENV_PATH` (para credenciales de respaldo), `STATE_PATH`,
`LOG_PATH_VIGIA`, `CHECK_INTERVAL_MINUTES` (5), `STALE_AFTER_MINUTES` (15),
`REALERT_MINUTES` (120), `FROZEN_FACTOR` (2.5), `DRY_RUN` (false).

## Detalles de diseño

- **Cero dependencias Hex**: si el vigía no arranca, no es porque un dep de
  Hex falte. SQLite no se usa (heartbeat por log); Telegram vía `:httpc` +
  `:ssl` con verificación de par y CA de Kali.
- **El token nunca está en el estado del GenServer**: `VigiaSentinel.Config`
  lee `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` del entorno (systemd
  `EnvironmentFile`) al momento de cada envío, con fallback al archivo `.env`.
  Un crash dump del GenServer no expone el token.
- **Riesgo residual conocido:** si Windows muere por completo, el vigía
  también está muerto. Un dead man's switch local no sustituye un aviso desde
  fuera de la máquina; cubre "launcher parado en máquina viva".

## Verificación hecha (2026-10-17, instalación)

- 13/13 tests (decisión con reloj inyectado, heartbeat contra log real,
  parseo de .env).
- E2E real: envío de prueba por Telegram entregado (HTTP 200).
- E2E caída simulada: copia del log con último ciclo envejecido + dry-run →
  ALERTA con minutos correctos, Telegram no tocado, estado persistido.
- `vigia-sentinel.service` (systemd --user, enabled) chequeando el log real.
