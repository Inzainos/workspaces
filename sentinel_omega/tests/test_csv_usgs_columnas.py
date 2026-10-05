"""CSV USGS: nombres del CSV y no botar depth/type."""

from sentinel_omega.infrastructure.pipeline.backcast import extraer_sismos_usgs_real
from sentinel_omega.infrastructure.pipeline import topologia_cascada as tc


CSV_SAMPLE = """time,latitude,longitude,depth,mag,magType,nst,gap,dmin,rms,net,id,updated,place,type,horizontalError,depthError,magError,magNst,status,locationSource,magSource
2025-01-01T12:00:00.000Z,-16.9,167.3,11.2,4.5,mb,23,168,1.4,0.8,us,usTEST1,2025-01-02T00:00:00.000Z,Vanuatu,earthquake,9.7,5.9,0.1,18,reviewed,us,us
"""


def test_extraer_sismos_conserva_depth(monkeypatch):
    class R:
        text = CSV_SAMPLE

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "sentinel_omega.infrastructure.pipeline.backcast.requests.get",
        lambda *a, **k: R(),
    )
    df = extraer_sismos_usgs_real(2025)
    assert "depth" in df.columns and "type" in df.columns
    assert float(df.iloc[0]["depth"]) == 11.2
    assert df.iloc[0]["type"] == "earthquake"


def test_fetch_sismos_usgs_conserva_depth(monkeypatch):
    class R:
        text = CSV_SAMPLE

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "sentinel_omega.infrastructure.pipeline.topologia_cascada.requests.get",
        lambda *a, **k: R(),
    )
    df = tc.fetch_sismos_usgs(2025)
    assert "depth" in df.columns and "id" in df.columns
    assert "magType" in df.columns


def test_poblar_dry_run_no_execute(monkeypatch):
    """dry_run=True no debe llamar conn.execute."""
    import pandas as pd

    calls = []

    class FakeConn:
        def execute(self, *a, **k):
            calls.append(a)
            raise AssertionError("execute en dry_run")

        def commit(self):
            raise AssertionError("commit en dry_run")

    df = pd.read_csv(__import__("io").StringIO(CSV_SAMPLE))
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    monkeypatch.setattr(tc, "fetch_sismos_usgs", lambda year: df)
    monkeypatch.setattr(tc, "calcular_version_topologia", lambda: "test")
    monkeypatch.setattr(
        "sentinel_omega.core.shared.geometria_uvg.nodo_mas_cercano",
        lambda lat, lon: {"id": 1},
    )
    # Acotar el rango de años a uno
    monkeypatch.setattr(tc, "YEAR_INI", 2025)
    monkeypatch.setattr(tc, "YEAR_END", 2025)
    n = tc.poblar_eventos_sismicos_fuente(FakeConn(), dry_run=True)
    assert n == 1
    assert calls == []
