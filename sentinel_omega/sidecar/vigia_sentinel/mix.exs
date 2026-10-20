defmodule VigiaSentinel.MixProject do
  use Mix.Project

  def project do
    [
      app: :vigia_sentinel,
      version: "0.1.0",
      elixir: "~> 1.20",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:logger, :inets, :ssl, :crypto, :public_key],
      mod: {VigiaSentinel.Application, []}
    ]
  end

  # Sin dependencias Hex a propósito: el vigía debe arrancar con la
  # instalación base de Elixir.
  defp deps do
    []
  end
end
