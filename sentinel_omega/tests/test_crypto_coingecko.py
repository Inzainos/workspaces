"""CoinGecko Demo-key support in the live-cycle crypto connector (mocked HTTP)."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from sentinel_omega.infrastructure.api import crypto
from sentinel_omega.infrastructure.api.crypto import (
    COINGECKO_BASE_URL,
    COINGECKO_DEMO_HEADER,
    coingecko_headers,
    fetch_coingecko_dominance,
    fetch_coingecko_market_chart,
    mask_coingecko_key,
)

FAKE_KEY = "CG-TESTFAKEKEY-0123456789abcdef"


def _resp(json_data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


_DOMINANCE = {"data": {"market_cap_percentage": {"btc": 54.3, "eth": 17.2}}}
_CHART = {"prices": [[1704067200000, 42000.0], [1704153600000, 42500.0]]}


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", FAKE_KEY)


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)


def test_base_url_is_public_demo_endpoint():
    assert COINGECKO_BASE_URL == "https://api.coingecko.com/api/v3"
    assert COINGECKO_DEMO_HEADER == "x-cg-demo-api-key"


# ── key set ─────────────────────────────────────────────────────────

@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_dominance_with_key_sends_demo_header(mock_sess, with_key):
    mock_sess.return_value.get.return_value = _resp(_DOMINANCE)
    assert fetch_coingecko_dominance()["btc"] == 54.3
    args, kwargs = mock_sess.return_value.get.call_args
    assert args[0] == "https://api.coingecko.com/api/v3/global"
    assert kwargs["headers"] == {"x-cg-demo-api-key": FAKE_KEY}
    assert kwargs["timeout"] == crypto.TIMEOUT
    assert FAKE_KEY not in args[0]  # never in the URL


@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_market_chart_with_key_sends_demo_header(mock_sess, with_key):
    mock_sess.return_value.get.return_value = _resp(_CHART)
    df = fetch_coingecko_market_chart("bitcoin", days=2)
    assert len(df) == 2
    args, kwargs = mock_sess.return_value.get.call_args
    assert args[0].startswith("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?")
    assert kwargs["headers"] == {"x-cg-demo-api-key": FAKE_KEY}
    assert FAKE_KEY not in args[0]


def test_key_read_at_call_time(monkeypatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    assert coingecko_headers() == {}
    monkeypatch.setenv("COINGECKO_API_KEY", FAKE_KEY)
    assert coingecko_headers() == {"x-cg-demo-api-key": FAKE_KEY}


# ── key missing / empty: behaviour unchanged ────────────────────────

@pytest.mark.parametrize("value", [None, "", "   "])
@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_dominance_without_key_unchanged(mock_sess, value, monkeypatch):
    if value is None:
        monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    else:
        monkeypatch.setenv("COINGECKO_API_KEY", value)
    mock_sess.return_value.get.return_value = _resp(_DOMINANCE)
    assert fetch_coingecko_dominance()["btc"] == 54.3
    mock_sess.return_value.get.assert_called_once_with(
        "https://api.coingecko.com/api/v3/global", timeout=crypto.TIMEOUT
    )


@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_market_chart_without_key_unchanged(mock_sess, no_key):
    mock_sess.return_value.get.return_value = _resp(_CHART)
    assert len(fetch_coingecko_market_chart("ethereum", days=7)) == 2
    mock_sess.return_value.get.assert_called_once_with(
        "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
        "?vs_currency=usd&days=7",
        timeout=crypto.TIMEOUT,
    )


# ── key never leaks ─────────────────────────────────────────────────

@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_key_not_in_logs_on_success(mock_sess, with_key, caplog):
    mock_sess.return_value.get.return_value = _resp(_DOMINANCE)
    with caplog.at_level(logging.DEBUG):
        fetch_coingecko_dominance()
        fetch_coingecko_market_chart("bitcoin", days=1)
    assert FAKE_KEY not in caplog.text


@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_key_masked_in_error_logs(mock_sess, with_key, caplog):
    # Worst case: an exception whose message embeds the key.
    mock_sess.return_value.get.side_effect = requests.HTTPError(
        f"401 Unauthorized: bad {COINGECKO_DEMO_HEADER}={FAKE_KEY}"
    )
    with caplog.at_level(logging.DEBUG):
        assert fetch_coingecko_dominance() is None
        assert fetch_coingecko_market_chart("bitcoin", days=1) is None
    assert FAKE_KEY not in caplog.text
    assert "***" in caplog.text
    for rec in caplog.records:
        assert FAKE_KEY not in rec.getMessage()
        if rec.exc_info:
            assert FAKE_KEY not in str(rec.exc_info[1])


@patch("sentinel_omega.infrastructure.api.crypto.get_session")
def test_http_error_does_not_raise_or_leak(mock_sess, with_key, caplog):
    r = _resp({}, status_code=401)
    r.raise_for_status.side_effect = requests.HTTPError(
        "401 Client Error: Unauthorized for url: https://api.coingecko.com/api/v3/global"
    )
    mock_sess.return_value.get.return_value = r
    with caplog.at_level(logging.DEBUG):
        assert fetch_coingecko_dominance() is None
    assert FAKE_KEY not in caplog.text


def test_mask_helper(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", FAKE_KEY)
    assert mask_coingecko_key(ValueError(f"x {FAKE_KEY} y")) == "x *** y"
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    assert mask_coingecko_key("plain") == "plain"


# ── backcast reuses the shared helper ───────────────────────────────

def test_backcast_uses_shared_helper(with_key, caplog):
    from sentinel_omega.infrastructure.pipeline import backcast
    fetch = backcast.extraer_psique_financiera  # CoinGecko BTC range fetch
    with patch.object(backcast.requests, "get") as mget:
        mget.side_effect = requests.ConnectionError(f"boom {FAKE_KEY}")
        with caplog.at_level(logging.DEBUG):
            fetch(2020)
        _, kwargs = mget.call_args
        assert kwargs["headers"] == {"x-cg-demo-api-key": FAKE_KEY}
    assert FAKE_KEY not in caplog.text
