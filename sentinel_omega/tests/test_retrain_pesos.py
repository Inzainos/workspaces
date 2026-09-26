"""El reentrenamiento tiene que heredar la asimetría del Juez.

Origen (2026-09-25, dos días antes del reentrenamiento semanal): de las 19.422
muestras del Juez en fase viva, 19.089 (98,3 %) enseñaban NEUTRAL y 333 (1,7 %)
enseñaban ALARMAR. Sin pesos, un FALLO (callarse y que pase algo) contaba lo
mismo que un falso positivo, cuando el Juez castiga el primero DIEZ veces más.
El domingo los modelos habrían aprendido a callar.

Ninguna prueba escribe en los modelos de producción: MODELS_DIR se redirige.
"""
import sqlite3

import numpy as np
import pytest

from sentinel_omega.models import train_onnx_from_db as tr

CALMA = "sin eventos en ventana de 72h (global)"


def _db(tmp_path, filas):
    """DB mínima con la auditoría del Juez. `filas`: (pred, resultado)."""
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
    conn.executemany(
        "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
        "resultado, detalles_json, fase) VALUES (?,?,?,?,?,'viva')",
        # kp_mean SÍ está en FEATURE_ORDER["alfa1"]; kp_index no, y una muestra
        # que no mapea ningún rasgo se descarta (ver el test de más abajo).
        [("alfa1", p, 0.3, r, '{"kp_mean": 4.0}') for p, r in filas],
    )
    conn.commit()
    conn.close()
    return str(ruta)


# ─── El peso sale del coste de equivocarse ───────────────────────────────────

def test_perder_un_evento_pesa_diez_veces_una_falsa_alarma(tmp_path):
    ruta = _db(tmp_path, [("neutral", "FALLO"), ("alert", "FALSO_POSITIVO")])
    _, _, _, w = tr.load_juez_feedback(ruta)["alfa1"]
    assert sorted(w.tolist()) == [tr._SEV_CALMA, tr._SEV_EVENTO]
    assert tr._SEV_EVENTO == 10 * tr._SEV_CALMA


def test_la_alarma_acertada_pesa_como_el_evento_que_habria_perdido(tmp_path):
    ruta = _db(tmp_path, [("alert", "ACIERTO")])
    _, _, _, w = tr.load_juez_feedback(ruta)["alfa1"]
    assert w.tolist() == [tr._SEV_EVENTO]


def test_el_silencio_acertado_pesa_lo_que_una_ventana_en_calma(tmp_path):
    ruta = _db(tmp_path, [("neutral", "ACIERTO")])
    _, _, _, w = tr.load_juez_feedback(ruta)["alfa1"]
    assert w.tolist() == [tr._SEV_CALMA]


def test_el_desbalance_efectivo_baja_al_que_eligio_el_operador(tmp_path):
    # 57 calmas por cada evento, como en los datos reales de ese día.
    ruta = _db(tmp_path, [("neutral", "ACIERTO")] * 57 + [("neutral", "FALLO")])
    _, _, ys, w = tr.load_juez_feedback(ruta)["alfa1"]
    crudo = (ys == tr.NEUTRAL).sum() / max((ys != tr.NEUTRAL).sum(), 1)
    pesado = w[ys == tr.NEUTRAL].sum() / w[ys != tr.NEUTRAL].sum()
    assert crudo == pytest.approx(57.0)
    assert pesado == pytest.approx(5.7, abs=0.05)


# ─── Los pesos viajan con las muestras ───────────────────────────────────────

def test_lo_que_no_trae_peso_pesa_uno():
    X = np.zeros((3, 4), dtype=np.float32)
    _, _, _, w = tr._con_pesos((X, np.zeros(3), np.zeros(3)))
    assert w.tolist() == [tr.PESO_BOOTSTRAP] * 3


def test_al_mezclar_se_conservan_los_pesos_de_cada_lado():
    a = (np.zeros((2, 4), np.float32), np.zeros(2), np.zeros(2), np.full(2, 10.0, np.float32))
    b = (np.ones((3, 4), np.float32), np.ones(3), np.ones(3))
    _, _, _, w = tr._merge_xy(a, b)
    assert w.tolist() == [10.0, 10.0, 1.0, 1.0, 1.0]


def test_al_remuestrear_el_peso_sigue_a_su_muestra(monkeypatch):
    # El híbrido replica lo real para equilibrarlo con el prior sintético: el
    # peso tiene que replicarse con los mismos índices, no rellenarse con unos.
    monkeypatch.setattr(tr, "bootstrap_xy", lambda bot, n=2500: (
        np.zeros((100, 10), np.float32), np.zeros(100, np.float32), np.zeros(100, np.float32)))
    real = (np.ones((4, 10), np.float32), np.ones(4, np.float32),
            np.full(4, tr.ALERT, np.float32), np.full(4, tr._SEV_EVENTO, np.float32))
    X, _, _, w, fuente = tr.merge_or_bootstrap("alfa1", {"alfa1": real}, min_samples=20)
    assert "hybrid" in fuente
    assert len(w) == len(X)
    assert (w == tr._SEV_EVENTO).sum() > 4      # se replicó con su peso


def test_sin_datos_del_juez_se_entrena_igual(monkeypatch):
    monkeypatch.setattr(tr, "bootstrap_xy", lambda bot, n=2500: (
        np.zeros((50, 10), np.float32), np.zeros(50, np.float32), np.zeros(50, np.float32)))
    X, _, _, w, fuente = tr.merge_or_bootstrap("alfa1", {}, min_samples=20)
    assert "bootstrap-only" in fuente and len(w) == len(X)


# ─── Que el peso cambie el modelo, no solo el argumento ──────────────────────

def _conjunto_desbalanceado(n_calma=570, n_evento=10):
    """Una sola variable separa los dos casos: con 57:1 y sin pesos, el bosque
    aprende a decir NEUTRAL siempre."""
    rng = np.random.default_rng(0)
    X_calma = np.zeros((n_calma, 10), np.float32)
    X_calma[:, 0] = rng.normal(0.0, 0.1, n_calma)
    X_evento = np.zeros((n_evento, 10), np.float32)
    X_evento[:, 0] = rng.normal(1.0, 0.1, n_evento)
    X = np.vstack([X_calma, X_evento])
    y_sig = np.concatenate([np.full(n_calma, tr.NEUTRAL, np.float32),
                            np.full(n_evento, tr.ALERT, np.float32)])
    y_conf = np.concatenate([np.full(n_calma, 0.35, np.float32),
                             np.full(n_evento, 0.7, np.float32)])
    w = np.concatenate([np.full(n_calma, tr._SEV_CALMA, np.float32),
                        np.full(n_evento, tr._SEV_EVENTO, np.float32)])
    return X, y_conf, y_sig, w


def test_con_pesos_el_modelo_se_moja_mas(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, "MODELS_DIR", tmp_path)   # NUNCA los modelos reales
    X, yc, ys, w = _conjunto_desbalanceado()
    sonda = np.zeros((1, 10), np.float32)
    sonda[0, 0] = 1.0                                  # el patrón del evento

    import onnxruntime as ort

    def _senal(pesos):
        ruta = tr.train_export("alfa1", X, yc, ys, pesos)
        sesion = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
        salida = sesion.run(None, {"input": sonda})[0]
        return float(np.ravel(salida)[1])

    sin_pesos = _senal(None)
    con_pesos = _senal(w)
    assert con_pesos > sin_pesos, (
        f"los pesos no cambiaron nada: {con_pesos} vs {sin_pesos}")
    assert tmp_path.joinpath("alfa1_spaceweather_rf.onnx").exists()


def test_el_entrenamiento_no_escribe_en_los_modelos_reales(tmp_path, monkeypatch):
    # Guarda explícito: un test que exporte a MODELS_DIR pisaría producción.
    monkeypatch.setattr(tr, "MODELS_DIR", tmp_path)
    X, yc, ys, w = _conjunto_desbalanceado(n_calma=30, n_evento=5)
    ruta = tr.train_export("alfa1", X, yc, ys, w)
    assert tmp_path in ruta.parents


# ─── Faltante es faltante: nada de rasgos fabricados ─────────────────────────

def test_una_muestra_sin_rasgos_no_entra(tmp_path):
    # El detalles_json real de la fase viva: firma_matches, que NO está en el
    # FEATURE_ORDER de ningún bot. Antes se rellenaba con vec[0] = confianza y
    # el modelo aprendía «con esta confianza, esta salida», sin mirar señales.
    ruta = tmp_path / "vacio.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        # `id` va porque producción lo tiene (PRIMARY KEY AUTOINCREMENT) y el
        # lector lo necesita para cruzar los rasgos reconstruidos. Un fixture
        # que se aparta del esquema real es como se cuela un fallo en verde.
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT)"
    )
    conn.executemany(
        "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
        "resultado, detalles_json, fase) VALUES ('alfa1',?,0.3,?,?,'viva')",
        [("neutral", "FALLO", '{"firma_matches": [{"firma_id": 1, "similitud": 1.0}]}'),
         ("neutral", "ACIERTO", '{"nodos": [{"id": 83}]}'),
         ("alert", "FALSO_POSITIVO", "")],
    )
    conn.commit()
    conn.close()
    assert tr.load_juez_feedback(str(ruta)) == {}


def test_solo_entra_lo_que_mapea_algun_rasgo(tmp_path):
    # Dos filas idénticas salvo el detalles_json: una trae kp_mean (está en
    # FEATURE_ORDER) y la otra kp_index (no está). Solo la primera entra.
    ruta = tmp_path / "mixto.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        # `id` va porque producción lo tiene (PRIMARY KEY AUTOINCREMENT) y el
        # lector lo necesita para cruzar los rasgos reconstruidos. Un fixture
        # que se aparta del esquema real es como se cuela un fallo en verde.
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT)"
    )
    conn.executemany(
        "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
        "resultado, detalles_json, fase) "
        "VALUES ('alfa1','neutral',0.3,'FALLO',?,'viva')",
        [('{"kp_mean": 5.0, "bz_mean": -3.0}',), ('{"kp_index": 5.0}',)],
    )
    conn.commit()
    conn.close()
    X, _, _, w = tr.load_juez_feedback(str(ruta))["alfa1"]
    assert len(X) == 1 and w.tolist() == [tr._SEV_EVENTO]


def test_sin_prior_sintetico_y_sin_datos_no_se_entrena():
    # jupiter y loki no tienen generador. Con pocas muestras reales, la
    # respuesta correcta es NO reentrenar, no rellenar con nada.
    assert tr.bootstrap_xy("jupiter") is None
    pocas = (np.ones((3, 8), np.float32), np.ones(3, np.float32),
             np.zeros(3, np.float32), np.ones(3, np.float32))
    X, yc, ys, w, fuente = tr.merge_or_bootstrap("jupiter", {"jupiter": pocas}, min_samples=50)
    assert X is None and yc is None and ys is None and w is None
    assert "NO se reentrena" in fuente and "3 muestras" in fuente


def test_el_bot_que_no_se_reentrena_conserva_su_modelo(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(tr, "load_firmas_from_db", lambda db: {})
    monkeypatch.setattr(tr, "load_juez_feedback", lambda db: {})
    res = tr.retrain(str(tmp_path / "no_existe.db"), min_samples=50, bots=["jupiter"])
    assert res["jupiter"]["reentrenado"] is False
    assert res["jupiter"]["path"] is None
    assert not list(tmp_path.glob("jupiter*.onnx"))   # no se escribió nada


def test_el_prior_existente_si_se_usa(tmp_path, monkeypatch):
    monkeypatch.setattr(tr, "MODELS_DIR", tmp_path)
    X, _, _, w, fuente = tr.merge_or_bootstrap("alfa1", {}, min_samples=50)
    assert X is not None and "bootstrap-only" in fuente
    assert w.tolist() == [tr.PESO_BOOTSTRAP] * len(X)
