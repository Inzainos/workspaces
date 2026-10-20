defmodule VigiaSentinel.Decision do
  @moduledoc """
  Lógica pura de decisión del vigía de Sentinel. Igual que la del watchdog:
  sin efectos, reloj inyectado, fácil de probar.
  """

  @type verdict ::
          {:ok, :fresh}
          | {:alert, :stale, NaiveDateTime.t()}
          | {:alert, :no_data, nil}
          | {:alert, {:unreadable, term()}, nil}
          | {:realert, :stale, NaiveDateTime.t()}
          | {:recover, :stale_returned, nil}
          | {:skip, :frozen_wakeup, nil}
          | {:skip, :still_ok_pending, nil}

  @spec evaluate(NaiveDateTime.t(), NaiveDateTime.t() | nil, tuple(), map(), keyword()) :: verdict
  def evaluate(now, last_check, hb, state, opts) do
    frozen_after = minutes(opts[:frozen_after_minutes])

    if frozen_wakeup?(now, last_check, frozen_after) do
      {:skip, :frozen_wakeup, nil}
    else
      evaluate_heartbeat(now, hb, state, opts)
    end
  end

  defp evaluate_heartbeat(now, {:ok, hb_dt}, state, opts) do
    stale_after = minutes(opts[:stale_after_minutes])

    if NaiveDateTime.diff(now, hb_dt) > stale_after do
      stale(now, state, opts)
    else
      case state.status do
        :stale -> {:recover, :stale_returned, nil}
        _ -> {:skip, :still_ok_pending, nil}
      end
    end
  end

  defp evaluate_heartbeat(_now, {:error, :no_log}, _state, _opts) do
    {:alert, :no_data, nil}
  end

  defp evaluate_heartbeat(_now, {:error, :no_lines}, _state, _opts) do
    {:alert, :no_data, nil}
  end

  defp evaluate_heartbeat(_now, {:error, reason}, _state, _opts) do
    {:alert, {:unreadable, reason}, nil}
  end

  defp stale(now, %{status: :stale, last_alert_at: nil} = _state, _opts) do
    {:alert, :stale, now}
  end

  defp stale(now, %{status: :stale} = state, opts) do
    realert = minutes(opts[:realert_minutes])

    if NaiveDateTime.diff(now, state.last_alert_at) >= realert do
      {:realert, :stale, now}
    else
      {:skip, :still_stale_silent, nil}
    end
  end

  defp stale(now, _state, _opts) do
    {:alert, :stale, now}
  end

  defp frozen_wakeup?(_now, nil, _frozen_after), do: false

  defp frozen_wakeup?(now, last_check, frozen_after) do
    NaiveDateTime.diff(now, last_check) > frozen_after
  end

  defp minutes(n) when is_number(n), do: round(n * 60)
end
