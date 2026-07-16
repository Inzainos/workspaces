"""Tests for Júpiter — solar-storm correlation engine + connectors."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from sentinel_omega.core.precursor import jupiter


def _kp_df(n=30, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "time_tag": pd.date_range("2026-04-01", periods=n, freq="1D"),
        "kp_index": rng.uniform(0, 6, n),
    })


class TestJupiterEngine:

    def test_perfect_correlation_detected(self):
        kp = _kp_df(30)
        # trends tracks kp exactly -> Spearman ~ +1
        trends = pd.DataFrame({
            "date": kp["time_tag"],
            "solar_interest": kp["kp_index"].values * 10.0,
        })
        res = jupiter.analyze(kp_df=kp, trends_df=trends)
        assert "kp" in res.series_available and "trends" in res.series_available
        corr = next(c for c in res.correlations if c.pair == "kp~trends")
        assert corr.n >= 25
        assert corr.spearman_rho is not None and corr.spearman_rho > 0.95

    def test_needs_two_series(self):
        res = jupiter.analyze(kp_df=_kp_df(10))
        assert res.correlations == []
        assert any("at least two" in n for n in res.notes)

    def test_lag_detection(self):
        kp = _kp_df(40, seed=3)
        # trends = kp shifted forward 3 days -> best lag should be around +3
        shifted = kp["kp_index"].shift(3).bfill().values
        trends = pd.DataFrame({"date": kp["time_tag"], "solar_interest": shifted})
        res = jupiter.analyze(kp_df=kp, trends_df=trends, max_lag=7)
        corr = next(c for c in res.correlations if c.pair == "kp~trends")
        assert abs(corr.best_lag_days - 3) <= 1

    def test_to_dict_serializable(self):
        import json
        res = jupiter.analyze(kp_df=_kp_df(30),
                              trends_df=pd.DataFrame({
                                  "date": pd.date_range("2026-04-01", periods=30, freq="1D"),
                                  "solar_interest": np.arange(30.0),
                              }))
        json.dumps(res.to_dict())  # must not raise


class TestGoogleTrendsConnector:

    def test_degrades_when_pytrends_missing(self):
        from sentinel_omega.infrastructure.api import google_trends
        with patch.dict("sys.modules", {"pytrends.request": None}):
            # forcing import failure inside the function -> None, no crash
            out = google_trends.fetch_solar_storm_trends()
        assert out is None or isinstance(out, pd.DataFrame)

    def test_builds_solar_interest_column(self):
        from sentinel_omega.infrastructure.api import google_trends
        fake = pd.DataFrame(
            {"solar storm": [1, 5, 2], "aurora": [3, 4, 9], "isPartial": [False, False, True]},
            index=pd.date_range("2026-07-01", periods=3, freq="1D"),
        )
        mock_req = MagicMock()
        mock_req.interest_over_time.return_value = fake
        with patch("pytrends.request.TrendReq", return_value=mock_req):
            out = google_trends.fetch_solar_storm_trends()
        assert out is not None
        assert "solar_interest" in out.columns
        assert list(out["solar_interest"]) == [3, 5, 9]  # row-wise max


class TestGfzKpConnector:

    def test_parses_gfz_json(self):
        from sentinel_omega.infrastructure.api import gfz_kp
        payload = {
            "Kp": [1.667, 3.0, 3.667],
            "datetime": ["2026-07-10T00:00:00Z", "2026-07-10T03:00:00Z", "2026-07-10T06:00:00Z"],
        }
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        with patch("sentinel_omega.infrastructure.api.gfz_kp.requests.get", return_value=resp):
            df = gfz_kp.fetch_kp_history(days=1)
        assert df is not None
        assert list(df.columns) == ["time_tag", "kp_index"]
        assert len(df) == 3

    def test_degrades_on_error(self):
        from sentinel_omega.infrastructure.api import gfz_kp
        with patch("sentinel_omega.infrastructure.api.gfz_kp.requests.get", side_effect=Exception("boom")):
            assert gfz_kp.fetch_kp_history() is None
