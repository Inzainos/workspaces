"""
Shared HTTP session factory for all Sentinel Omega API connectors.

Features:
  - Automatic retry with exponential backoff on transient errors
    (429, 500, 502, 503, 504 and network-level ConnectionError/Timeout).
  - Proxy support: respects HTTP_PROXY / HTTPS_PROXY environment variables
    (standard requests behaviour; no extra configuration needed in code).

Usage:
    from sentinel_omega.infrastructure.api._http import get_session

    resp = get_session().get(url, timeout=15)
    resp.raise_for_status()

The session is module-level so it is reused across calls within the same
process, sharing the underlying TCP connection pool.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Retry on these HTTP status codes (transient server / rate-limit errors).
_RETRY_STATUSES = frozenset([429, 500, 502, 503, 504])

# 3 retries → waits ~1s, ~2s, ~4s between attempts (backoff_factor=1).
_RETRY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=_RETRY_STATUSES,
    allowed_methods=["GET", "POST"],
    raise_on_status=False,   # let caller call raise_for_status()
)

_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Return the shared requests Session with retry/backoff configured."""
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session
