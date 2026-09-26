"""El Juez tiene que guardar CON QUÉ predijo, o no puede enseñar nada.

Origen (2026-09-25): las 19.422 filas vivas de TBL_JUEZ_AUDITORIA tenían
`"features_generales": {}`. La clave se añadió el 2026-08-20 exactamente para
que el reentrenamiento pudiera reconstruir el vector, pero la cadena estaba
rota por los DOS extremos:

  - `launcher.py` llamaba a register_cycle_predictions SIN `features=`, aunque
    ya las tenía calculadas ochenta líneas antes en el mismo ciclo.
  - `load_juez_feedback` no abría `features_generales`: leía las claves de
    primer nivel y las de `firma_matches`, que son metadatos de la firma
    (firma_id, similitud, recurrencia), no señales físicas.

La señal medida y no conectada, dos veces seguidas. Estas pruebas cierran la
cadena entera: se escribe, se guarda, se lee.
"""
import json
import sqlite3

import numpy as np
import pytest

from sentinel_omega.infrastructure.pipeline.juez_cycle_register import (
    register_cycle_predictions,
)
from sentinel_omega.models import train_onnx_from_db as tr

RASGOS = {"bz_mean": -4.2, "kp_mean": 5.0, "viento_avg": 520.0, "fase_lunar": 0.8}


class _Senal:
    def __init__(self, nombre, tipo="watch", conf=0.6):
        self.agent_name = nombre
        self.signal_type = type("T", (), {"value": tipo})()
        self.confidence = conf
        self.reasoning = "por la prueba"


class _Geo:
    def __init__(self, bots=("alfa1",)):
        self.final_signal = type("T", (), {"value": "neutral"})()
        self.confidence = 0.3
        self.agent_signals = [_Senal(b) for b in bots]


class _JuezFalso:
    """Guarda lo que le pasan, sin base de datos."""

    def __init__(self):
        self.filas = []

    def registrar_prediccion(self, **kw):
        self.filas.append(kw)
        return len(self.filas)


def test_los_rasgos_del_ciclo_llegan_a_cada_fila():
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo(("alfa1", "beta1")), features=RASGOS)
    assert len(juez.filas) == 3           # padre + dos bots
    for fila in juez.filas:
        assert fila["detalles"]["features_generales"] == RASGOS


def test_sin_rasgos_la_fila_queda_marcada_vacia():
    # Es el estado que se encontró el 2026-09-25: la clave está, vacía.
    juez = _JuezFalso()
    register_cycle_predictions(juez, _Geo())
    assert juez.filas[0]["detalles"]["features_generales"] == {}


def test_el_entrenamiento_lee_features_generales(tmp_path):
    ruta = tmp_path / "juez.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        # `id` va porque producción lo tiene (PRIMARY KEY AUTOINCREMENT) y el
        # lector lo necesita para cruzar los rasgos reconstruidos. Un fixture
        # que se aparta del esquema real es como se cuela un fallo en verde.
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT)"
    )
    conn.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
        "resultado, detalles_json, fase) "
        "VALUES ('alfa1','neutral',0.3,'FALLO',?,'viva')",
        (json.dumps({"firma_matches": [], "nodos": [], "features_generales": RASGOS}),),
    )
    conn.commit()
    conn.close()
    muestras = tr.load_juez_feedback(str(ruta))
    assert "alfa1" in muestras, "la muestra se descartó: no se leyeron los rasgos"
    X, _, _, w = muestras["alfa1"]
    assert np.any(np.abs(X[0]) > 1e-12)
    assert w.tolist() == [tr._SEV_EVENTO]


def test_los_metadatos_de_firma_no_valen_como_rasgos(tmp_path):
    # firma_id, similitud y recurrencia describen la COINCIDENCIA, no el estado
    # físico. Una fila con solo eso sigue sin poder enseñar nada.
    ruta = tmp_path / "solo_firma.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        # `id` va porque producción lo tiene (PRIMARY KEY AUTOINCREMENT) y el
        # lector lo necesita para cruzar los rasgos reconstruidos. Un fixture
        # que se aparta del esquema real es como se cuela un fallo en verde.
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT)"
    )
    conn.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
        "resultado, detalles_json, fase) "
        "VALUES ('alfa1','neutral',0.3,'FALLO',?,'viva')",
        (json.dumps({"firma_matches": [{"firma_id": 3163, "similitud": 1.0,
                                        "recurrencia": 71}],
                     "features_generales": {}}),),
    )
    conn.commit()
    conn.close()
    assert tr.load_juez_feedback(str(ruta)) == {}


def test_la_cadena_completa_de_punta_a_punta(tmp_path):
    """Del ciclo a la muestra de entrenamiento, sin saltarse un paso."""
    ruta = tmp_path / "cadena.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        # `id` va porque producción lo tiene (PRIMARY KEY AUTOINCREMENT) y el
        # lector lo necesita para cruzar los rasgos reconstruidos. Un fixture
        # que se aparta del esquema real es como se cuela un fallo en verde.
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT)"
    )

    class _JuezReal:
        def registrar_prediccion(self, bot_name, prediccion, confianza,
                                 ventana_h=72, detalles=None, fase=None, **kw):
            conn.execute(
                "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, "
                "confianza, resultado, detalles_json, fase) "
                "VALUES (?,?,?,'FALLO',?,?)",
                (bot_name, prediccion, confianza, json.dumps(detalles or {}), fase),
            )
            conn.commit()

    register_cycle_predictions(_JuezReal(), _Geo(("alfa1",)), features=RASGOS)
    conn.close()
    muestras = tr.load_juez_feedback(str(ruta))
    assert "alfa1" in muestras
    X, _, _, w = muestras["alfa1"]
    # alfa1 espera bz_mean en la posición 0 y kp_mean en la 5 (FEATURE_ORDER)
    orden = tr.FEATURE_ORDER["alfa1"]
    assert X[0][orden.index("bz_mean")] == pytest.approx(RASGOS["bz_mean"])
    assert X[0][orden.index("kp_mean")] == pytest.approx(RASGOS["kp_mean"])
    assert w[0] == tr._SEV_EVENTO


def test_el_lanzador_que_corre_el_servicio_pasa_los_rasgos():
    # Guarda contra la regresión exacta: la llamada existía y no pasaba
    # `features`, así que la cadena quedó muda dos meses.
    import inspect
    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher)
    i = fuente.index("register_cycle_predictions(\n")
    llamada = fuente[i:fuente.index(")", i)]
    assert "features=features" in llamada
