defmodule VigiaSentinel.Watcher do
  @moduledoc false

  use GenServer
  require Logger

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(opts) do
    # En test no arranca el watcher: un `mix test` que coincidiera con un
    # ciclo parado intentaría un envío REAL de Telegram.
    if test_env?() do
      :ignore
    else
      init_watcher(opts)
    end
  end

  defp test_env? do
    function_exported?(Mix, :env, 0) and Mix.env() == :test
  end

  defp init_watcher(opts) do
    cfg = opts[:cfg] || VigiaSentinel.Config.load()

    state = %{
      cfg: cfg,
      check_fn: opts[:check_fn] || (&VigiaSentinel.Heartbeat.last_cycle/1),
      now_fn: opts[:now_fn] || fn -> :calendar.local_time() |> naivedt() end,
      run: load_run_state(cfg)
    }

    log(
      state,
      :info,
      "vigía de Sentinel arriba · log=#{cfg[:log_path]} cada #{cfg[:check_interval_minutes]} min · umbral #{cfg[:stale_after_minutes]} min"
    )

    # Primera comprobación casi inmediata: que un arranque del servicio se
    # pueda verificar sin esperar el intervalo entero.
    Process.send_after(self(), :check, 5_000)
    {:ok, state}
  end

  @impl true
  def handle_info(:check, state) do
    now = state.now_fn.()
    hb = state.check_fn.(state.cfg[:log_path])

    opts = [
      stale_after_minutes: state.cfg[:stale_after_minutes],
      realert_minutes: state.cfg[:realert_minutes],
      frozen_after_minutes:
        round(state.cfg[:check_interval_minutes] * state.cfg[:frozen_factor] * 60)
    ]

    verdict = VigiaSentinel.Decision.evaluate(now, state.run.last_check_at, hb, state.run, opts)
    run = act(verdict, now, hb, state)
    run = %{run | last_check_at: now}
    persist(state.cfg, run)

    schedule_next(state)
    {:noreply, %{state | run: run}}
  end

  defp act({:skip, :frozen_wakeup, _}, now, _hb, state) do
    gap = seconds_between(state.run.last_check_at, now)

    log(
      state,
      :warning,
      "reinicio tras pausa del sistema (el propio vigía estuvo congelado #{gap} s); " <>
        "la falta de ciclos se explica por la pausa, no se alerta"
    )

    state.run
  end

  defp act({:skip, :still_ok_pending, _}, _now, {:ok, hb}, state) do
    log(state, :info, "ok · último ciclo #{format_dt(hb)}")
    %{state.run | status: :ok}
  end

  defp act({:skip, :still_stale_silent, _}, _now, {:ok, hb}, state) do
    log(state, :info, "ciclo parado (ya alertado) · último ciclo #{format_dt(hb)}")
    state.run
  end

  defp act({:recover, :stale_returned, _}, _now, {:ok, hb}, state) do
    msg =
      "vigía · Sentinel Omega volvió a reportar\n" <>
        "último ciclo: #{format_dt(hb)}\n" <>
        "parado desde: #{fmt(state.run.stale_since)}"

    log(state, :info, "recuperación · #{msg}")
    send_msg(state, msg)
    %{state.run | status: :ok, stale_since: nil, last_alert_at: nil}
  end

  defp act({:alert, :stale, ts}, _now, {:ok, hb}, state) do
    min = round(NaiveDateTime.diff(ts, hb) / 60)

    msg =
      "vigía · SENTINEL OMEGA PARADO\n" <>
        "último ciclo: #{format_dt(hb)} (hace #{min} min, hora local)\n" <>
        "el launcher dejó de escribir ciclos en el log\n" <>
        "re-alerta cada #{state.cfg[:realert_minutes]} min mientras siga parado"

    log(state, :error, "ALERTA ciclo parado · #{msg}")
    send_msg(state, msg)
    %{state.run | status: :stale, stale_since: hb, last_alert_at: ts}
  end

  defp act({:realert, :stale, ts}, _now, {:ok, hb}, state) do
    hours = Float.round(NaiveDateTime.diff(ts, state.run.stale_since || hb) / 3600, 1)

    msg =
      "vigía · Sentinel Omega sigue parado\n" <>
        "sin ciclos desde #{format_dt(state.run.stale_since || hb)} (#{hours} h)"

    log(state, :warning, "re-alerta · #{msg}")
    send_msg(state, msg)
    %{state.run | last_alert_at: ts}
  end

  defp act({:alert, :no_data, _}, now, {:error, :no_lines}, state) do
    msg =
      "vigía · sin latido de Sentinel\n" <>
        "no hay líneas de ciclo en #{state.cfg[:log_path]}"

    log(state, :error, "ALERTA sin latido · #{msg}")
    send_msg(state, msg)
    %{state.run | status: :stale, last_alert_at: now}
  end

  defp act({:alert, :no_data, _}, now, {:error, :no_log}, state) do
    msg =
      "vigía · sin latido de Sentinel\n" <>
        "no existe el log #{state.cfg[:log_path]}"

    log(state, :error, "ALERTA sin log · #{msg}")
    send_msg(state, msg)
    %{state.run | status: :stale, last_alert_at: now}
  end

  defp act({:alert, {:unreadable, reason}, _}, now, {:error, r}, state) do
    msg =
      "vigía · latido ilegible\n" <>
        "no se pudo leer #{state.cfg[:log_path]}: #{inspect(r)}"

    log(state, :error, "ALERTA ilegible (#{inspect(reason)}) · #{msg}")
    send_msg(state, msg)
    %{state.run | status: :stale, last_alert_at: now}
  end

  defp send_msg(state, msg) do
    cfg = state.cfg
    VigiaSentinel.Log.append(cfg, "SEND", msg)
    creds = VigiaSentinel.Config.telegram_creds(cfg[:env_path])

    VigiaSentinel.Telegram.send(
      [
        token: creds.token,
        chat_id: creds.chat_id,
        dry_run: cfg[:dry_run],
        env_path: cfg[:env_path]
      ],
      msg
    )
  end

  defp schedule_next(state) do
    Process.send_after(self(), :check, state.cfg[:check_interval_minutes] * 60_000)
  end

  defp persist(cfg, run) do
    lines = [
      "last_check_at=#{fmt(run.last_check_at)}",
      "status=#{run.status}",
      "stale_since=#{fmt(run.stale_since)}",
      "last_alert_at=#{fmt(run.last_alert_at)}"
    ]

    File.mkdir_p(Path.dirname(cfg[:state_path]))
    File.write(cfg[:state_path], Enum.join(lines, "\n") <> "\n")
  end

  defp load_run_state(cfg) do
    case File.read(cfg[:state_path]) do
      {:ok, data} ->
        decode_run_state(data)

      {:error, _} ->
        %{last_check_at: nil, status: :ok, stale_since: nil, last_alert_at: nil}
    end
  end

  defp decode_run_state(data) do
    m = VigiaSentinel.Config.parse_env(data)

    %{
      last_check_at: ndt(m["last_check_at"]),
      status: if(m["status"] == "stale", do: :stale, else: :ok),
      stale_since: ndt(m["stale_since"]),
      last_alert_at: ndt(m["last_alert_at"])
    }
  rescue
    e ->
      Logger.warning("[vigia] estado ilegible (#{inspect(e)}), arranca limpio")
      %{last_check_at: nil, status: :ok, stale_since: nil, last_alert_at: nil}
  end

  defp ndt(nil), do: nil

  defp ndt(iso) do
    case NaiveDateTime.from_iso8601(iso) do
      {:ok, ndt} -> ndt
      {:error, _} -> nil
    end
  end

  defp fmt(nil), do: nil
  defp fmt(%NaiveDateTime{} = ndt), do: NaiveDateTime.to_iso8601(ndt)

  defp format_dt(%NaiveDateTime{} = ndt), do: NaiveDateTime.to_iso8601(ndt)
  defp format_dt(nil), do: "?"

  defp seconds_between(nil, _now), do: 0
  defp seconds_between(prev, now), do: NaiveDateTime.diff(now, prev)

  defp log(state, level, msg) do
    VigiaSentinel.Log.append(state.cfg, level |> Atom.to_string() |> String.upcase(), msg)

    case level do
      :info -> Logger.info(msg)
      :warning -> Logger.warning(msg)
      :error -> Logger.error(msg)
    end
  end

  defp naivedt({{y, mo, d}, {h, mi, s}}) do
    case NaiveDateTime.new(y, mo, d, h, mi, s, 0) do
      {:ok, ndt} -> ndt
      :error -> NaiveDateTime.new(2000, 1, 1, 0, 0, 0, 0)
    end
  end
end
