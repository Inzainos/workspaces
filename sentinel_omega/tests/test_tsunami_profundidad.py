"""Tsunami: profundidad del sismo de mayor magnitud. Sin red."""

import inspect

import numpy as np
import pandas as pd

from sentinel_omega.core.precursor.precursor_types import (
    PrecursorType,
    detect_tsunami_potential,
)
from sentinel_omega.core.precursor.scanner import PrecursorScanner
from sentinel_omega.infrastructure.pipeline.data_pipeline import (
    GeodynamicPipeline,
    depth_km_o_null,
    profundidad_del_sismo_mayor,
)


def _tsunamis(beta1, delta=None):
    dets = PrecursorScanner().scan({}, beta1, delta or {})
    return [d for d in dets if d.tipo == PrecursorType.TSUNAMI]


def test_m74_a_110_km_no_dispara():
    # El mayor es profundo; un M6 somero en el mismo catálogo no cuenta.
    beta1 = {
        "seismic_magnitudes": np.array([6.0, 7.4, 4.2]),
        "max_quake_depth_km": 110.0,
    }
    assert _tsunamis(beta1) == []


def test_m70_a_20_km_dispara():
    beta1 = {
        "seismic_magnitudes": np.array([5.5, 7.0, 3.2]),
        "max_quake_depth_km": 20.0,
    }
    tsunami = _tsunamis(beta1)
    assert len(tsunami) == 1
    assert tsunami[0].values["magnitude"] == 7.0
    assert tsunami[0].values["depth_km"] == 20.0


def test_profundidad_ausente_no_dispara():
    mags = {"seismic_magnitudes": np.array([8.2, 4.0])}
    assert _tsunamis(mags) == []
    assert _tsunamis({**mags, "max_quake_depth_km": None}) == []
    assert detect_tsunami_potential(7.5, None) is False


def test_la_profundidad_es_la_del_mayor_y_la_ausente_es_null():
    df = pd.DataFrame({
        "magnitude": [6.2, 7.4, 5.0],
        "depth_km": [8.0, 110.0, None],
    })
    assert profundidad_del_sismo_mayor(df) == 110.0
    sin_dato = pd.DataFrame({
        "magnitude": [7.4, 6.0],
        "depth_km": [None, 5.0],
    })
    assert profundidad_del_sismo_mayor(sin_dato) is None
    assert depth_km_o_null(None) is None
    assert depth_km_o_null(float("nan")) is None
    assert depth_km_o_null(20.0) == 20.0
    src = inspect.getsource(GeodynamicPipeline.fetch_beta1_data)
    assert "profundidad_del_sismo_mayor" in src
    assert "0.0 if pd.isna(depth)" not in src
