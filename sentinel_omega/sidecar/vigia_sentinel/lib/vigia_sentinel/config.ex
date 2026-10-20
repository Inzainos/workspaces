defmodule VigiaSentinel.Config do
  @moduledoc false

  @defaults [
    log_path: "/home/deamon/workspaces/sentinel_omega/data/sentinel_omega.log",
    env_path: "/home/deamon/workspaces/sentinel_omega/deploy/.env",
    state_path: "/home/deamon/workspaces/sentinel_omega/sidecar/state.json",
    log_path_vigia: "/home/deamon/workspaces/sentinel_omega/sidecar/logs/vigia_sentinel.log",
    check_interval_minutes: 5,
    stale_after_minutes: 15,
    realert_minutes: 120,
    frozen_factor: 2.5,
    dry_run: false
  ]

  def load do
    Keyword.new(@defaults, fn {k, v} ->
      {k, get_env(k, v)}
    end)
  end

  defp get_env(key, default) do
    name = "VIGIA_#{key |> Atom.to_string() |> String.upcase()}"

    case System.get_env(name) do
      nil -> default
      "" -> default
      val -> cast(key, val)
    end
  end

  defp cast(:dry_run, val), do: val in ["1", "true", "TRUE"]

  defp cast(key, val)
       when key in [:check_interval_minutes, :stale_after_minutes, :realert_minutes] do
    case Integer.parse(val) do
      {n, ""} when n > 0 -> n
      _ -> raise ArgumentError, "VIGIA_#{key}: entero positivo esperado, llegó #{inspect(val)}"
    end
  end

  defp cast(_key, val), do: val

  @doc false
  # El token NUNCA se guarda en el estado del GenServer. Se lee del .env al
  # momento de cada envío (EnvironmentFile del unit de systemd lo inyecta).
  def telegram_creds(env_path) do
    creds = %{
      token: System.get_env("TELEGRAM_BOT_TOKEN"),
      chat_id: System.get_env("TELEGRAM_CHAT_ID")
    }

    case {creds.token, creds.chat_id} do
      {nil, nil} ->
        creds_from_file(env_path)

      {nil, _} ->
        # Si falta una de las dos, completar del archivo para no regalar un
        # envío a medias.
        merge(creds, creds_from_file(env_path))

      {_, nil} ->
        merge(creds, creds_from_file(env_path))

      _ ->
        creds
    end
  end

  defp creds_from_file(env_path) do
    env =
      env_path
      |> File.read()
      |> case do
        {:ok, data} -> parse_env(data)
        {:error, _} -> %{}
      end

    %{
      token: Map.get(env, "TELEGRAM_BOT_TOKEN"),
      chat_id: Map.get(env, "TELEGRAM_CHAT_ID")
    }
  end

  defp merge(base, extra) do
    %{
      token: base.token || extra.token,
      chat_id: base.chat_id || extra.chat_id
    }
  end

  def parse_env(data) when is_binary(data) do
    data
    |> String.split(["\r\n", "\n"])
    |> Map.new(fn line ->
      line = String.trim(line)

      cond do
        line == "" or String.starts_with?(line, "#") -> {:skip, nil}
        true -> split_kv(line)
      end
    end)
    |> Map.drop([:skip])
  end

  defp split_kv(line) do
    case String.split(line, "=", parts: 2) do
      [k, v] -> {String.trim(k), String.trim(v)}
      _ -> {:skip, nil}
    end
  end
end
