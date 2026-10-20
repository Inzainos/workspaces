defmodule VigiaSentinel.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      VigiaSentinel.Watcher
    ]

    opts = [strategy: :one_for_one, name: VigiaSentinel.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
