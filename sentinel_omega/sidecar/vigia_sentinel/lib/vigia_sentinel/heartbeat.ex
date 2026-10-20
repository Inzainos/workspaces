defmodule VigiaSentinel.Heartbeat do
  @moduledoc false

  # Línea del launcher: "2026-10-17 17:21:19,586 [LAUNCHER] INFO --- Starting cycle #2 ---"
  @cycle_re ~r/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}),\d+ \[LAUNCHER\] INFO --- Starting cycle #\d+ ---$/

  @doc """
  Lee el latido de Sentinel Omega: la última línea `--- Starting cycle #N ---`
  de su log (hora local).

  Devuelve `{:ok, %NaiveDateTime{}}`, `{:error, :no_lines}` (el log existe pero
  nunca registró un ciclo) o `{:error, :no_log}` (el log no existe). Nunca
  inventa un ciclo: falta de dato no es 0 (regla 7 del home).
  """
  def last_cycle(log_path) do
    case :file.read_file_info(log_path) do
      {:error, :enoent} ->
        {:error, :no_log}

      {:error, _reason} ->
        {:error, :no_log}

      {:ok, _info} ->
        case last_cycle_line(log_path) do
          {:ok, ndt} -> {:ok, ndt}
          {:error, :no_lines} -> {:error, :no_lines}
          {:error, :no_file} -> {:error, :no_log}
          {:error, reason} -> {:error, reason}
        end
    end
  end

  defp last_cycle_line(log_path) do
    case File.read(log_path) do
      {:ok, out} ->
        lines =
          out
          |> String.split("\n")
          |> Enum.filter(&String.match?(&1, @cycle_re))

        case List.last(lines) do
          nil ->
            {:error, :no_lines}

          line ->
            [_, y, mo, d, h, mi, s] = Regex.run(@cycle_re, line)

            case NaiveDateTime.new(
                   String.to_integer(y),
                   String.to_integer(mo),
                   String.to_integer(d),
                   String.to_integer(h),
                   String.to_integer(mi),
                   String.to_integer(s),
                   0
                 ) do
              {:ok, ndt} -> {:ok, ndt}
              :error -> {:error, :bad_line}
            end
        end

      {:error, :enoent} ->
        {:error, :no_file}

      {:error, reason} ->
        {:error, reason}
    end
  end
end
