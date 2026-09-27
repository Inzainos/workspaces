"""RTSW (rtsw_mag_1m / rtsw_wind_1m) sustituye a products/solar-wind/*-7-day (404).

Muestras REALES recortadas de la descarga en vivo del 2026-09-27 ~01:56 UTC
(tests/data/rtsw/). Cada minuto trae tres naves (SOLAR1 activa, ACE e IMAP
inactivas). El feed no tenía filas con overall_quality != 0 en ese momento, así
que la última fila de cada muestra es una fila REAL de SOLAR1 a la que se le
puso overall_quality=1 para probar el filtro.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from sentinel_omega.infrastructure.api.noaa import fetch_mag_field, fetch_solar_wind
from sentinel_omega.core.delta_enriched import fetchers as delta_fetchers

DATA = Path(__file__).parent / "data" / "rtsw"
MAG = json.loads((DATA / "rtsw_mag_1m_muestra.json").read_text())
WIND = json.loads((DATA / "rtsw_wind_1m_muestra.json").read_text())


def _validas(rows):
    return [r for r in rows if r["active"] is True and r["overall_quality"] == 0]


def _resp(data):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status.return_value = None
    return r


def test_muestras_tienen_filas_que_deben_descartarse():
    for rows in (MAG, WIND):
        assert any(r["active"] is False for r in rows)
        assert any(r["active"] is True and r["overall_quality"] != 0 for r in rows)
        assert {r["source"] for r in _validas(rows)} == {"SOLAR1"}


@patch("sentinel_omega.infrastructure.api.noaa.get_session")
def test_wind_solo_activa_y_calidad_cero(mock_s):
    mock_s.return_value.get.return_value = _resp(WIND)
    df = fetch_solar_wind()
    esperadas = _validas(WIND)
    assert df is not None and len(df) == len(esperadas)
    assert list(df.columns) == ["time_tag", "proton_speed", "proton_density"]
    assert sorted(df["proton_speed"]) == sorted(r["proton_speed"] for r in esperadas)
    # ACE (inactiva) trae densidades ~0.05: no deben colarse
    assert df["proton_density"].min() > 1.0


@patch("sentinel_omega.infrastructure.api.noaa.get_session")
def test_mag_solo_activa_y_calidad_cero(mock_s):
    mock_s.return_value.get.return_value = _resp(MAG)
    df = fetch_mag_field()
    esperadas = _validas(MAG)
    assert df is not None and len(df) == len(esperadas)
    assert sorted(df["bz_gsm"]) == sorted(r["bz_gsm"] for r in esperadas)
    assert df["time_tag"].is_unique


@pytest.mark.parametrize("fetch", [fetch_solar_wind, fetch_mag_field])
@pytest.mark.parametrize("payload", [
    [],
    [r for r in WIND + MAG if not (r["active"] is True and r["overall_quality"] == 0)],
])
def test_sin_filas_validas_devuelve_none_no_cero(fetch, payload):
    with patch("sentinel_omega.infrastructure.api.noaa.get_session") as mock_s:
        mock_s.return_value.get.return_value = _resp(payload)
        assert fetch() is None


@patch("sentinel_omega.infrastructure.api.noaa.get_session")
def test_time_tag_sin_z_es_utc(mock_s):
    """'2026-09-27T01:55:02' es UTC: no debe leerse como hora de México (-6 h)."""
    fila = dict(_validas(MAG)[0])
    fila["time_tag"] = "2026-09-27T01:55:02"
    mock_s.return_value.get.return_value = _resp([fila])
    df = fetch_mag_field()
    ts = df["time_tag"].iloc[0]
    assert ts.tzinfo is not None
    assert ts == pd.Timestamp("2026-09-27 01:55:02", tz="UTC")
    assert ts.tz_convert("America/Mexico_City") == pd.Timestamp(
        "2026-09-26 19:55:02", tz="America/Mexico_City")


def test_hora_de_clima_espacial_en_utc():
    """La fila horaria persistida lleva la hora UTC del dato, sin corrimiento."""
    from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline
    with patch("sentinel_omega.infrastructure.api.noaa.get_session") as mock_s:
        mock_s.return_value.get.side_effect = [_resp(MAG), _resp(WIND)]
        mag, wind = fetch_mag_field(), fetch_solar_wind()
    omni = pd.concat([mag.set_index("time_tag"),
                      wind.rename(columns={"proton_speed": "plasma_speed"}).set_index("time_tag")],
                     axis=1).reset_index(names=["time_tag"])
    filas = GeodynamicPipeline._filas_clima_horarias(omni, None, None)
    horas = {f[0] for f in filas}
    esperadas = {r["time_tag"][:13].replace("T", " ") + ":00" for r in _validas(MAG) + _validas(WIND)}
    assert horas == esperadas


def test_delta_space_weather_filtra_y_no_usa_7day():
    pedidas = []

    def fake_get(url, timeout=30):
        pedidas.append(url)
        if url.endswith("rtsw_mag_1m.json"):
            return MAG
        if url.endswith("rtsw_wind_1m.json"):
            return WIND
        return []

    with patch.object(delta_fetchers, "_get_json", side_effect=fake_get):
        sw = delta_fetchers.fetch_space_weather(days=36500)
    assert not any("products/solar-wind" in u for u in pedidas)
    bz = [r["bz_gsm"] for r in _validas(MAG)]
    sp = [r["proton_speed"] for r in _validas(WIND)]
    dn = [r["proton_density"] for r in _validas(WIND)]
    i = sw.dates.index(_validas(MAG)[0]["time_tag"][:10])
    assert sw.bz_mean[i] == pytest.approx(sum(bz) / len(bz))
    assert sw.bz_min[i] == pytest.approx(min(bz))
    assert sw.solar_wind_speed[i] == pytest.approx(sum(sp) / len(sp))
    assert sw.solar_wind_density[i] == pytest.approx(sum(dn) / len(dn))


def test_delta_space_weather_sin_validas_es_nan_no_cero():
    import numpy as np
    invalidas = [r for r in MAG + WIND if not (r["active"] is True and r["overall_quality"] == 0)]
    kp = [{"time_tag": invalidas[0]["time_tag"], "kp_index": 2}]

    def fake_get(url, timeout=30):
        if "planetary_k_index" in url:
            return kp
        if "rtsw" in url:
            return invalidas
        return []

    with patch.object(delta_fetchers, "_get_json", side_effect=fake_get):
        sw = delta_fetchers.fetch_space_weather(days=36500)
    assert np.all(np.isnan(sw.bz_mean)) and np.all(np.isnan(sw.solar_wind_speed))
