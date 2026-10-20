defmodule VigiaSentinel.DecisionTest do
  use ExUnit.Case, async: true

  @opts [stale_after_minutes: 15, realert_minutes: 120, frozen_after_minutes: 25]

  defp ndt(y, mo, d, h, mi, s) do
    {:ok, ndt} = NaiveDateTime.new(y, mo, d, h, mi, s, 0)
    ndt
  end

  defp now, do: ndt(2026, 10, 17, 18, 0, 0)

  defp hb(minutes_ago) do
    NaiveDateTime.add(now(), -round(minutes_ago * 60), :second)
  end

  test "ciclo fresco: nada que hacer" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(10)}, ok_state(), @opts) ==
             {:skip, :still_ok_pending, nil}
  end

  test "ciclo fresco tras parada: recuperación" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(10)}, stale_state(), @opts) ==
             {:recover, :stale_returned, nil}
  end

  test "ciclo parado 20 min (> umbral 15): alerta primera vez" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(20)}, ok_state(), @opts) ==
             {:alert, :stale, now()}
  end

  test "ciclo parado 10 min (< umbral 15): aún no alerta" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(10)}, ok_state(), @opts) ==
             {:skip, :still_ok_pending, nil}
  end

  test "parado ya alertado hace poco: silencio" do
    state = %{stale_state() | last_alert_at: hb(10)}

    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(20)}, state, @opts) ==
             {:skip, :still_stale_silent, nil}
  end

  test "parado y última alerta hace >= realert: re-alerta" do
    state = %{stale_state() | last_alert_at: hb(150)}

    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:ok, hb(20)}, state, @opts) ==
             {:realert, :stale, now()}
  end

  test "sin líneas de ciclo en el log: alerta, no default benigno" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(10), {:error, :no_log}, ok_state(), @opts) ==
             {:alert, :no_data, nil}
  end

  test "log ilegible: alerta" do
    assert VigiaSentinel.Decision.evaluate(
             now(),
             hb(10),
             {:error, {:tail_exit, 1}},
             ok_state(),
             @opts
           ) ==
             {:alert, {:unreadable, {:tail_exit, 1}}, nil}
  end

  test "pausa del sistema: gap propio > frozen_after, no alerta aunque esté parado" do
    assert VigiaSentinel.Decision.evaluate(now(), hb(120), {:ok, hb(200)}, ok_state(), @opts) ==
             {:skip, :frozen_wakeup, nil}
  end

  defp ok_state, do: %{status: :ok, stale_since: nil, last_alert_at: nil}

  defp stale_state, do: %{status: :stale, stale_since: hb(20), last_alert_at: nil}
end

defmodule VigiaSentinel.HeartbeatTest do
  use ExUnit.Case, async: false

  @tmp Path.join(System.tmp_dir(), "vigia_sentinel_test_#{System.unique_integer()}")

  setup do
    File.mkdir_p!(@tmp)
    log = Path.join(@tmp, "sentinel_omega.log")

    File.write!(log, ~s"""
    2026-10-17 17:13:11,465 [LAUNCHER] INFO --- Starting cycle #10 ---
    2026-10-17 17:16:19,585 [LAUNCHER] INFO --- Starting cycle #1 ---
    2026-10-17 17:21:19,586 [LAUNCHER] INFO --- Starting cycle #2 ---
    2026-10-17 17:22:30,000 [LAUNCHER] INFO Searching on provider cop_dataspace
    """)

    on_exit(fn -> File.rm_rf!(@tmp) end)
    {:ok, log: log}
  end

  test "lee última línea de ciclo y la parsea", %{log: log} do
    assert {:ok, %NaiveDateTime{} = ndt} = VigiaSentinel.Heartbeat.last_cycle(log)
    assert NaiveDateTime.to_iso8601(ndt) == "2026-10-17T17:21:19.000000"
  end

  test "log sin líneas de ciclo: {:error, :no_lines}", %{log: log} do
    empty = Path.join(@tmp, "vacio.log")
    File.write!(empty, "2026-10-17 17:22:30 [LAUNCHER] INFO hola\n")
    assert {:error, :no_lines} = VigiaSentinel.Heartbeat.last_cycle(empty)
  end

  test "log inexistente: {:error, :no_log}" do
    assert {:error, :no_log} =
             VigiaSentinel.Heartbeat.last_cycle(Path.join(@tmp, "no_existe.log"))
  end
end

defmodule VigiaSentinel.ConfigTest do
  use ExUnit.Case, async: true

  test "parsea .env estilo KEY=VALUE" do
    env =
      VigiaSentinel.Config.parse_env(
        "TELEGRAM_BOT_TOKEN=abc\n# comentario\nTELEGRAM_CHAT_ID=42\n"
      )

    assert env["TELEGRAM_BOT_TOKEN"] == "abc"
    assert env["TELEGRAM_CHAT_ID"] == "42"
  end
end
