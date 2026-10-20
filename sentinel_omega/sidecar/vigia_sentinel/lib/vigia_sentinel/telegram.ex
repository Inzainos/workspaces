defmodule VigiaSentinel.Telegram do
  @moduledoc false

  require Logger

  @doc """
  Envía `text` al chat de Telegram de Sentinel.

  - Texto plano, SIN `parse_mode` (ningún nombre de archivo puede inyectar ni
    silenciar una alerta).
  - En fallo se loguea el CUERPO de la respuesta, nunca la URL (el token
    viaja en la URL).
  - `dry_run: true` no envía nada.
  """
  @spec send(keyword(), String.t()) :: :ok | {:ok, :dry_run, String.t()} | {:error, term()}
  def send(opts \\ [], text) do
    cond do
      opts[:dry_run] ->
        Logger.info("[telegram] DRY-RUN (no se envía): #{text}")
        {:ok, :dry_run, text}

      is_binary(opts[:token]) and opts[:token] != "" and
        is_binary(opts[:chat_id]) and opts[:chat_id] != "" ->
        post(opts[:token], opts[:chat_id], text)

      true ->
        Logger.error("[telegram] sin TELEGRAM_BOT_TOKEN/CHAT_ID en #{inspect(opts[:env_path])}")
        {:error, :no_credentials}
    end
  end

  defp post(token, chat_id, text) do
    url = ~c"https://api.telegram.org/bot" ++ String.to_charlist(token) ++ ~c"/sendMessage"

    body = :json.encode(%{"chat_id" => chat_id, "text" => text})

    headers = [{~c"content-type", ~c"application/json"}]

    http_opts = [
      ssl: [
        verify: :verify_peer,
        cacertfile: String.to_charlist("/etc/ssl/certs/ca-certificates.crt"),
        depth: 3,
        customize_hostname_check: [
          match_fun: :public_key.pkix_verify_hostname_match_fun(:https)
        ]
      ],
      timeout: 30_000,
      connect_timeout: 15_000
    ]

    case :httpc.request(:post, {url, headers, ~c"application/json", body}, http_opts,
           body_format: :binary
         ) do
      {:ok, {{_, status, _}, _resp_headers, _resp_body}} when status in 200..299 ->
        Logger.info("[telegram] enviado ok (HTTP #{status})")
        :ok

      {:ok, {{_, status, _}, _resp_headers, resp_body}} ->
        Logger.error("[telegram] HTTP #{status} · cuerpo: #{resp_body}")
        {:error, {:http, status}}

      {:error, reason} ->
        Logger.error("[telegram] fallo de red: #{inspect(reason)}")
        {:error, reason}
    end
  end
end
