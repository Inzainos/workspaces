"""La marea terrestre: que sea física, no un número que sube y baja.

Se añadió el 2026-09-26 porque beta2 llevaba sin fuente viva desde el
2026-07-31. Antes de conectarla se comprobó contra valores de libro; estas
pruebas dejan esa comprobación clavada, para que un cambio de constantes o de
fórmula no pase en silencio.
"""

from __future__ import annotations

import datetime

import pytest

from sentinel_omega.core.features_onnx import BOT_DIMS, FEATURE_ORDER, vector_para
from sentinel_omega.core.mareas import marea_en, marea_para_ciclo, marea_ventana

ephem = pytest.importorskip("ephem")


def test_la_razon_sol_luna_es_la_de_libro():
    """La marea solar es ~0,46 de la lunar. Es LA comprobación de la fórmula:
    el Sol tiene 27 millones de veces la masa de la Luna y aun así pesa menos,
    porque la marea va con d³ y no con d²."""
    m = marea_en(datetime.datetime(2026, 9, 26, 12, 0))
    razon = m["marea_sol"] / m["marea_luna"]
    assert 0.42 <= razon <= 0.50, razon


def test_la_sicigia_da_marea_maxima_y_la_cuadratura_minima():
    """Luna llena/nueva: los dos tiran en línea. Cuartos: se restan."""
    mejor = peor = None
    for dia in range(1, 30):
        m = marea_en(datetime.datetime(2026, 9, dia, 12, 0))
        if mejor is None or m["marea_sicigia"] > mejor["marea_sicigia"]:
            mejor = m
        if peor is None or m["marea_sicigia"] < peor["marea_sicigia"]:
            peor = m
    assert mejor["marea_sicigia"] > 0.9    # casi alineados
    assert peor["marea_sicigia"] < -0.9    # casi en cuadratura
    assert mejor["marea_total"] > peor["marea_total"] * 1.8


def test_la_marea_esta_en_el_orden_de_magnitud_correcto():
    """~1e-6 m/s², que en µm/s² son números de orden 1."""
    m = marea_en(datetime.datetime(2026, 9, 26, 12, 0))
    assert 0.3 <= m["marea_total"] <= 3.0
    assert 0.8 <= m["marea_dist_luna"] <= 1.2   # perigeo/apogeo, ±6 %


def test_la_ventana_mide_el_movimiento_no_solo_el_valor():
    """Lo que se asocia al disparo es la VARIACIÓN del esfuerzo."""
    m = marea_ventana(datetime.datetime(2026, 9, 26, 12, 0), horas=24)
    assert m["marea_rango_24h"] > 0
    assert m["marea_max_24h"] >= m["marea_total"]
    assert "marea_deriv" in m


def test_es_determinista_en_vivo_y_reconstruida():
    """Lo que valida la reconstrucción histórica: la misma función, el mismo
    instante, el mismo número. No hay «lo que el bot vio» que contradecir."""
    t = datetime.datetime(2026, 3, 15, 7, 30)
    assert marea_ventana(t) == marea_ventana(t)


def test_beta2_deja_de_ser_cuatro_rasgos_repetidos():
    orden = FEATURE_ORDER["beta2"]
    assert len(orden) == BOT_DIMS["beta2"] == 16
    assert len(set(orden)) == 12          # antes eran 4
    assert sum(1 for k in orden if k.startswith("marea_")) == 12
    # su dominio no se perdió: los volcánicos siguen ahí
    for k in ("so2_kt_win", "erupciones_win", "so2_kt_90d", "erupciones_90d"):
        assert k in orden


def test_el_vector_de_beta2_ya_no_sale_en_ceros():
    """Antes, sin desgasificación, beta2 preguntaba con dieciséis ceros ---
    que para el modelo significan «cero SO2 medido», no «no lo sé»."""
    import numpy as np

    rasgos = marea_para_ciclo(datetime.datetime(2026, 9, 26, 12, 0))
    vec = vector_para("beta2", rasgos)
    assert vec.shape == (16,)
    assert int(np.count_nonzero(vec)) >= 12
    # y sin desgasificación, esas cuatro posiciones siguen en 0: faltante es
    # faltante, no se inventa
    assert vec[8] == 0.0 and vec[11] == 0.0


def test_sin_efemerides_no_se_inventa_un_cero(monkeypatch):
    """Si `ephem` no está, la marea queda AUSENTE. Un 0.0 diría «no hay
    marea», que es físicamente imposible."""
    import builtins

    real = builtins.__import__

    def sin_ephem(nombre, *a, **k):
        if nombre == "ephem":
            raise ImportError("simulado")
        return real(nombre, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_ephem)
    assert marea_en(datetime.datetime(2026, 9, 26, 12, 0)) == {}
