defmodule VigiaSentinel do
  @moduledoc """
  Vigía de Sentinel Omega — dead man's switch para el ciclo de `/home/deamon/workspaces/sentinel_omega`.

  El ciclo del launcher corre cada 300 s y **no deja huella confiable en la DB**
  (`sentinel.db` está vacía: `insert_ciclo` cae en un try/rescue silencioso), así
  que el latido real es el log: `data/sentinel_omega.log` y sus líneas
  `--- Starting cycle #N ---` (hora local).

  Si el heartbeat se estanca más de `stale_after_minutes` (15 por defecto =
  3 ciclos perdidos), avisa por Telegram con el bot compartido de Sentinel
  (`@SismoBio_Bot`, token y chat desde `deploy/.env` vía `EnvironmentFile` del
  unit). Mientras siga parado, re-alerta cada `realert_minutes` y avisa la
  recuperación cuando el ciclo vuelve.

  Detección de pausa: si el propio vigía estuvo congelado, no alerta.

  Es un sidecar: no toca el launcher, ni la DB, ni el crontab, ni el unit de
  Sentinel.
  """
end
