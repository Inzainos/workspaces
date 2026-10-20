defmodule VigiaSentinel.Log do
  @moduledoc false

  @doc false
  def append(cfg, level, msg) do
    {{y, mo, d}, {h, mi, s}} = :calendar.local_time()
    ts = "#{pad(y)}-#{pad(mo)}-#{pad(d)}T#{pad(h)}:#{pad(mi)}:#{pad(s)}Z"
    File.mkdir_p(Path.dirname(cfg[:log_path_vigia]))
    File.write(cfg[:log_path_vigia], "#{ts} | #{level} | #{msg}\n", [:append])
    :ok
  end

  defp pad(n) when n < 10, do: "0" <> Integer.to_string(n)
  defp pad(n), do: Integer.to_string(n)
end
