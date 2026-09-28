"""Un 401 de Telegram (token revocado) fallaba sin decir por qué.

`send_alert` / `send_photo` / `send_document` sólo hacían `raise_for_status()`:
un 200 con `{"ok": false}` pasaba en silencio, y un 401 dejaba en el log la
URL de la API (con el token enmascarado, pero la URL entera) y nunca la
`description` de Telegram. Ahora toda respuesta no OK se registra con el
código y la descripción, y NI el token NI la URL `/bot<token>/` salen al log.

Sin red: `get_session` se sustituye por un doble.
"""

from __future__ import annotations

import logging

import pytest
import requests

from sentinel_omega.infrastructure.api import telegram

TOKEN = "8412345678:" + "AAHdummyDUMMYdummyDUMMYdummyDUMMY"
RARO = "abc:no-canonico"  # un token que el patrón numérico no reconoce
URL_API = "https://api.telegram.org/bot{tok}/sendMessage"


class _Resp:
    def __init__(self, status, cuerpo, tok):
        self.status_code = status
        self._cuerpo = cuerpo
        self._tok = tok

    def json(self):
        return self._cuerpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Client Error: Unauthorized for url: "
                + URL_API.format(tok=self._tok))


class _Sesion:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.llamadas = resp, exc, []

    def post(self, url, **kw):
        self.llamadas.append(url)
        if self.exc is not None:
            raise self.exc
        return self.resp


@pytest.fixture
def directo(monkeypatch):
    """Fuerza el envío directo (sin la cola del Concilio)."""
    monkeypatch.setattr(telegram, "ALERT_QUEUE_AVAILABLE", False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.delenv("SENTINEL_DRY_RUN", raising=False)

    def poner(sesion, tok=TOKEN):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", tok)
        monkeypatch.setattr(telegram, "get_session", lambda: sesion)
        return sesion
    return poner


def _sin_fuga(texto, tok):
    assert tok not in texto
    assert f"/bot{tok}" not in texto
    assert "api.telegram.org/bot" + tok not in texto


@pytest.mark.parametrize("tok", [TOKEN, RARO])
def test_401_se_registra_con_codigo_y_descripcion_sin_token(directo, caplog, tok):
    cuerpo = {"ok": False, "error_code": 401, "description": "Unauthorized"}
    s = directo(_Sesion(_Resp(401, cuerpo, tok)), tok)
    with caplog.at_level(logging.WARNING, logger=telegram.logger.name):
        assert telegram.send_alert("hola") is False  # mismo retorno que antes
    assert s.llamadas, "no se llegó a hacer la petición"
    errores = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert errores
    texto = caplog.text
    assert "401" in texto
    assert "Unauthorized" in texto
    assert "sendMessage no OK" in texto
    _sin_fuga(texto, tok)


def test_200_con_ok_false_ya_no_es_silencioso(directo, caplog):
    cuerpo = {"ok": False, "error_code": 400,
              "description": "Bad Request: chat not found"}
    directo(_Sesion(_Resp(200, cuerpo, TOKEN)))
    with caplog.at_level(logging.WARNING, logger=telegram.logger.name):
        ok = telegram.send_alert("hola")
    assert ok is True  # comportamiento intacto: sólo se añade el registro
    assert "chat not found" in caplog.text
    assert "status=200" in caplog.text
    _sin_fuga(caplog.text, TOKEN)


def test_200_ok_no_registra_error(directo, caplog):
    directo(_Sesion(_Resp(200, {"ok": True, "result": {}}, TOKEN)))
    with caplog.at_level(logging.WARNING, logger=telegram.logger.name):
        assert telegram.send_alert("hola") is True
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


@pytest.mark.parametrize("tok", [TOKEN, RARO])
def test_excepcion_de_red_se_registra_sin_url_con_token(directo, caplog, tok):
    exc = requests.ConnectionError(
        f"Max retries exceeded with url: /bot{tok}/sendMessage")
    directo(_Sesion(exc=exc), tok)
    with caplog.at_level(logging.WARNING, logger=telegram.logger.name):
        assert telegram.send_alert("hola") is False
    assert "Telegram send failed" in caplog.text
    _sin_fuga(caplog.text, tok)


def test_foto_y_documento_401(directo, caplog, tmp_path):
    f = tmp_path / "x.png"
    f.write_bytes(b"x")
    cuerpo = {"ok": False, "error_code": 401, "description": "Unauthorized"}
    directo(_Sesion(_Resp(401, cuerpo, TOKEN)))
    with caplog.at_level(logging.WARNING, logger=telegram.logger.name):
        assert telegram.send_photo(str(f)) is False
        assert telegram.send_document(str(f)) is False
    assert "sendPhoto no OK" in caplog.text
    assert "sendDocument no OK" in caplog.text
    _sin_fuga(caplog.text, TOKEN)
