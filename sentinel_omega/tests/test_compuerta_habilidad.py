"""Un modelo sin medición de habilidad es numerología.

Por qué existe esta compuerta (2026-10-07)
------------------------------------------
Hasta hoy el único control de calidad de `train_onnx_from_db.py` era:

    pred = model.predict(X)        # las MISMAS X del entrenamiento
    mae  = np.mean(np.abs(pred[:,0] - y_conf))

Error **en muestra**. Un bosque que memoriza saca MAE ~0 y se publica igual, y
`models_meta.json` no guardaba ni un número de calidad --- solo `{path, n,
source, reentrenado}`.

Lo que costó: el 2026-10-05 se publicaron **ocho** modelos sin habilidad sin
que nada chistara. Cinco bots alarmaron el 100 % de los ciclos durante dos
días, con ganancia de Molchan 0,81x ---peor que el azar--- y 159 falsos
positivos que hundieron seis pesos al suelo de 0,300.

Medido el 2026-10-07 con corte TEMPORAL y objetivo real (hubo evento en el
horizonte aprendido), los seis bots con material dan **AUC 0,465-0,515**, o sea
azar. Y la causa de fondo está en el objetivo: `y_conf` sale de
`EVENT_CLASS_LABEL[clase] + ESTADO_BOOST[estado]`, **no es función de `X`**, y
como las firmas nacen de eventos, el 96-100 % de las muestras llevan etiqueta
de alarma.

La compuerta niega el envío en los dos casos que importan ---objetivo
degenerado y habilidad por debajo del azar útil--- y cuando niega **deja el
`.onnx` anterior intacto**: preferimos el de ayer, cuya habilidad al menos es
conocida, a uno nuevo del que no sabemos nada.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from sentinel_omega.models import train_onnx_from_db as tr

ARCHIVO_ALFA1 = "alfa1_spaceweather_rf.onnx"


@pytest.fixture(autouse=True)
def _nunca_los_modelos_reales(tmp_path, monkeypatch):
    """Sin esto, un fallo de esta prueba pisa producción."""
    monkeypatch.setattr(tr, "MODELS_DIR", tmp_path)
    return tmp_path


def _conjunto(n_calma, n_evento, separable=True, semilla=0):
    """Diez rasgos. Si `separable`, la posición 0 distingue; si no, es ruido."""
    rng = np.random.RandomState(semilla)
    X = rng.normal(0.0, 0.1, (n_calma + n_evento, 10)).astype(np.float32)
    if separable:
        X[n_calma:, 0] = rng.normal(1.0, 0.1, n_evento)
    y_sig = np.concatenate([np.full(n_calma, tr.NEUTRAL, np.float32),
                            np.full(n_evento, tr.ALERT, np.float32)])
    y_conf = np.concatenate([np.full(n_calma, 0.35, np.float32),
                             np.full(n_evento, 0.70, np.float32)])
    return X, y_conf, y_sig


# ─── Lo que la compuerta tiene que negar ─────────────────────────────────────

def test_un_objetivo_de_UNA_SOLA_CLASE_no_se_puede_medir(tmp_path):
    """El estado real del 2026-10-07: `delta` tenía el 100 % de sus 718
    muestras etiquetadas como alarma. Sin dos clases no hay nada que
    discriminar, y eso NO es un AUC bajo: es que no hay AUC."""
    X, yc, ys = _conjunto(0, 200)
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert ruta is None, "se publicó un modelo cuyo objetivo era una constante"
    assert hab["auc"] is None
    assert "degenerado" in hab["motivo"]
    assert hab["aprueba"] is False
    assert not (tmp_path / ARCHIVO_ALFA1).exists()


def test_con_pocas_muestras_el_AUC_es_ruido_y_se_niega(tmp_path):
    X, yc, ys = _conjunto(20, 10)
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert ruta is None
    assert hab["auc"] is None and str(tr.MIN_PARA_MEDIR) in hab["motivo"]
    assert not (tmp_path / ARCHIVO_ALFA1).exists()


def test_un_modelo_SIN_habilidad_no_se_publica(tmp_path):
    """Rasgos que son puro ruido: el AUC de prueba ronda 0,5."""
    X, yc, ys = _conjunto(120, 120, separable=False)
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert hab["auc"] is not None, hab["motivo"]
    assert hab["auc"] < tr.AUC_MINIMA, (
        f"el ruido dio AUC {hab['auc']:.3f}: revisa el conjunto de prueba")
    assert ruta is None and hab["aprueba"] is False
    assert not (tmp_path / ARCHIVO_ALFA1).exists()


def test_al_negar_NO_se_borra_el_modelo_anterior(tmp_path):
    """Preferimos el de ayer, cuya habilidad al menos es conocida, a ninguno."""
    viejo = tmp_path / ARCHIVO_ALFA1
    viejo.write_bytes(b"modelo de ayer")
    X, yc, ys = _conjunto(120, 120, separable=False)
    ruta, _ = tr.train_export("alfa1", X, yc, ys)
    assert ruta is None
    assert viejo.read_bytes() == b"modelo de ayer", (
        "la compuerta negó el nuevo y además se llevó el anterior")


# ─── El techo: un AUC demasiado alto es una fuga, no un buen modelo ──────────
#
# La PRIMERA versión de esta compuerta aprobó a los seis bots con AUC
# 0,989-0,999, o sea que habría dejado pasar exactamente los modelos que
# costaron los 159 falsos positivos. La causa, medida el 2026-10-07:
#
#     AUC de «¿esta fila es una firma o una fila del Juez?» = 1,0000
#
# La clase alarma son las firmas (96-100 % de ellas la llevan, porque nacen de
# eventos) y la clase calma son las 28 filas vivas del Juez (3,6 %). Cualquier
# bosque saca 0,99 aprendiendo la TABLA de origen.
#
# Es la fuga de procedencia del 2026-09-27 con otra cara: aquella era «el rasgo
# vale 0 en toda la mitad de alarma» y se cerró declarando los rasgos.
# `test_fuga_de_procedencia.py` la vigila rasgo por rasgo y NO puede ver esta,
# porque aquí todos están declarados y llenos --- lo que difiere es de dónde
# salen. Por eso hace falta un techo además de un suelo.

def test_un_AUC_demasiado_alto_se_niega_por_sospecha_de_fuga(tmp_path):
    """Predecir un sismo con 0,99 no es un buen modelo: es una fuga."""
    X, yc, ys = _conjunto(120, 120, separable=True)
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert hab["auc"] > tr.AUC_MAXIMA_CREIBLE, (
        f"el conjunto separable dio {hab['auc']:.3f}: ajusta la prueba")
    assert ruta is None, "se publicó un modelo con AUC increíble"
    assert hab["aprueba"] is False
    assert "DEMASIADO BUENO" in hab["motivo"]
    assert "procedencia" in hab["motivo"]
    assert not (tmp_path / ARCHIVO_ALFA1).exists()


def test_el_techo_nombra_la_causa_probable(tmp_path):
    """El mensaje tiene que mandar al sitio correcto, no solo decir «no».
    La lección del 2026-10-07: un mensaje que diagnostica mal cuesta medio día.
    """
    X, yc, ys = _conjunto(120, 120, separable=True)
    _, hab = tr.train_export("alfa1", X, yc, ys)
    texto = hab["motivo"].lower()
    for pista in ("misma extracción", "procedencia", "1,0000", "fuentes distintas"):
        assert pista.lower() in texto, f"al mensaje le falta «{pista}»"


# ─── Lo que tiene que dejar pasar ────────────────────────────────────────────

def _conjunto_con_senal_realista(n=1600, semilla=1):
    """Separable pero NO perfecto: el rasgo 0 informa con solape, que es como
    se ve una señal de verdad. Cae dentro de la banda creíble."""
    rng = np.random.RandomState(semilla)
    X = rng.normal(0.0, 1.0, (n, 10)).astype(np.float32)
    # etiqueta con solape fuerte: el rasgo 0 empuja, no decide
    p = 1.0 / (1.0 + np.exp(-0.9 * X[:, 0]))
    alarma = (rng.uniform(size=n) < p).astype(int)
    y_sig = np.where(alarma == 1, tr.ALERT, tr.NEUTRAL).astype(np.float32)
    y_conf = np.where(alarma == 1, 0.70, 0.35).astype(np.float32)
    return X, y_conf, y_sig


def test_un_modelo_CON_habilidad_CREIBLE_se_publica(tmp_path):
    X, yc, ys = _conjunto_con_senal_realista()
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert hab["auc"] is not None, hab["motivo"]
    assert tr.AUC_MINIMA <= hab["auc"] <= tr.AUC_MAXIMA_CREIBLE, (
        f"AUC {hab['auc']:.3f} fuera de la banda creíble "
        f"[{tr.AUC_MINIMA}, {tr.AUC_MAXIMA_CREIBLE}]")
    assert ruta is not None and hab["aprueba"] is True
    assert hab["escrito"] is True
    assert (tmp_path / ARCHIVO_ALFA1).exists()


# ─── La barra de error: un punto suelto por encima del suelo no es habilidad ──

def test_un_AUC_sin_significancia_se_niega(tmp_path):
    """`delta` dio AUC 0,551 el 2026-10-07 --- 0,001 por encima del suelo, con
    218 positivas de prueba. Eso es azar con ruido, y pasaba. Lo que tiene que
    cruzar el suelo es el EXTREMO INFERIOR."""
    rng = np.random.RandomState(7)
    n = 260
    X = rng.normal(0.0, 1.0, (n, 10)).astype(np.float32)
    p = 1.0 / (1.0 + np.exp(-0.18 * X[:, 0]))       # señal muy débil
    alarma = (rng.uniform(size=n) < p).astype(int)
    ys = np.where(alarma == 1, tr.ALERT, tr.NEUTRAL).astype(np.float32)
    yc = np.where(alarma == 1, 0.70, 0.35).astype(np.float32)
    ruta, hab = tr.train_export("alfa1", X, yc, ys)
    assert hab["auc"] is not None, hab["motivo"]
    assert hab["auc_inferior"] < hab["auc"], "la barra de error no se calculó"
    if hab["auc"] >= tr.AUC_MINIMA:
        assert ruta is None, "pasó un AUC cuyo extremo inferior no cruza el suelo"
        assert "extremo inferior" in hab["motivo"]


def test_la_barra_de_error_se_estrecha_con_mas_muestras():
    """Contrato del número: con la misma señal y más datos, el intervalo
    aprieta. Si no, el cálculo no depende de n y no sirve de nada."""
    def _inf(n):
        rng = np.random.RandomState(3)
        X = rng.normal(0.0, 1.0, (n, 10)).astype(np.float32)
        p = 1.0 / (1.0 + np.exp(-0.9 * X[:, 0]))
        a = (rng.uniform(size=n) < p).astype(int)
        ys = np.where(a == 1, tr.ALERT, tr.NEUTRAL).astype(np.float32)
        yc = np.where(a == 1, 0.70, 0.35).astype(np.float32)
        h = tr.medir_habilidad("alfa1", X, yc, ys)
        return h["auc"] - h["auc_inferior"]

    assert _inf(2000) < _inf(300), "la barra no se estrecha con más muestras"


# ─── Omori: habilidad REAL que no es un precursor ────────────────────────────

def test_la_habilidad_que_sale_de_los_sismo_se_etiqueta_y_se_niega(tmp_path):
    """Medido el 2026-10-07: `beta1` da AUC 0,802 con sus rasgos `sismo_*` y
    **0,515 sin ellos**. Eso predice RÉPLICAS --- agrupamiento de Omori ---,
    comparte catálogo y nodo con el objetivo, y no es un precursor.

    No se niega por ruido: se niega porque venderlo como detección de
    precursores sería exactamente el error de leer un número alto como
    habilidad. Si se quiere usar, que sea con su nombre y su propia vara.
    """
    from sentinel_omega.core.features_onnx import FEATURE_ORDER

    orden = FEATURE_ORDER["beta1"]
    cols_sismo = [i for i, k in enumerate(orden) if k.startswith("sismo_")]
    assert cols_sismo, "beta1 dejó de declarar rasgos sismo_*: revisa la prueba"

    rng = np.random.RandomState(11)
    n = 1600
    X = rng.normal(0.0, 1.0, (n, len(orden))).astype(np.float32)
    alarma = (rng.uniform(size=n) < 0.3).astype(int)
    # TODA la señal vive en los sismo_*, igual que en el caso real --- y con
    # SOLAPE, para que caiga en la banda creíble (0,55-0,95) y la negativa
    # venga de la etiqueta de Omori y no del techo. Con señal limpia salía
    # AUC 1,000 y lo paraba el techo, que es otra cosa.
    for c in cols_sismo:
        X[:, c] = alarma * 1.1 + rng.normal(0.0, 1.0, n)
    ys = np.where(alarma == 1, tr.ALERT, tr.NEUTRAL).astype(np.float32)
    yc = np.where(alarma == 1, 0.70, 0.35).astype(np.float32)

    ruta, hab = tr.train_export("beta1", X, yc, ys)
    assert hab["origen"] == "agrupamiento_omori", hab
    assert hab["auc_sin_sismo"] is not None
    assert hab["auc_sin_sismo"] < tr.AUC_MINIMA <= hab["auc"]
    assert ruta is None and hab["aprueba"] is False
    assert "Omori" in hab["motivo"] and "RÉPLICAS" in hab["motivo"]


def test_una_habilidad_que_NO_depende_de_los_sismo_no_se_etiqueta_de_omori():
    """La otra cara: si la señal sobrevive sin el catálogo del nodo, es de los
    rasgos propios del bot y no se marca."""
    from sentinel_omega.core.features_onnx import FEATURE_ORDER

    orden = FEATURE_ORDER["beta1"]
    rng = np.random.RandomState(13)
    n = 600
    X = rng.normal(0.0, 1.0, (n, len(orden))).astype(np.float32)
    alarma = (rng.uniform(size=n) < 0.3).astype(int)
    X[:, 2] = alarma * 3.0 + rng.normal(0.0, 0.5, n)   # schumann_mean, no sismo
    ys = np.where(alarma == 1, tr.ALERT, tr.NEUTRAL).astype(np.float32)
    yc = np.where(alarma == 1, 0.70, 0.35).astype(np.float32)
    hab = tr.medir_habilidad("beta1", X, yc, ys)
    assert hab["origen"] == "rasgos_propios", hab
    assert hab["auc_sin_sismo"] >= tr.AUC_MINIMA


def test_la_banda_creible_no_esta_vacia():
    """Regla dura 8 --- un umbral se calibra. Suelo 0,55 y techo 0,95 dejan una
    banda útil: por debajo no hay señal, por encima no es creíble."""
    assert tr.AUC_MINIMA < tr.AUC_MAXIMA_CREIBLE
    assert tr.AUC_MAXIMA_CREIBLE < 1.0


def test_el_corte_es_TEMPORAL_cuando_hay_marcas_de_tiempo():
    """Un corte aleatorio sobre series con autocorrelación sobrestima. Si hay
    marcas, se parte por tiempo; y se DICE cuál se usó, porque un AUC con corte
    aleatorio no es comparable con uno temporal."""
    X, yc, ys = _conjunto(120, 120, separable=True)
    ts = np.array([f"2026-01-{1 + i % 28:02d} {i % 24:02d}:00" for i in range(len(X))])
    con = tr.medir_habilidad("alfa1", X, yc, ys, ts=ts)
    sin = tr.medir_habilidad("alfa1", X, yc, ys)
    assert con["corte"] == "temporal"
    assert "aleatorio" in sin["corte"]


# ─── La salida de emergencia, que no puede ser silenciosa ────────────────────

def test_sin_compuerta_publica_pero_lo_deja_escrito(tmp_path):
    X, yc, ys = _conjunto(120, 120, separable=False)
    ruta, hab = tr.train_export("alfa1", X, yc, ys, con_compuerta=False)
    assert ruta is not None and (tmp_path / ARCHIVO_ALFA1).exists()
    assert hab["forzado"] is True, (
        "se forzó el envío y el metadato no lo dice: nadie podría saberlo después")
    assert hab["aprueba"] is False


def test_el_forzado_se_registra_en_el_log(caplog):
    import logging

    X, yc, ys = _conjunto(120, 120, separable=False)
    with caplog.at_level(logging.WARNING, logger=tr.logger.name):
        tr.train_export("alfa1", X, yc, ys, con_compuerta=False)
    assert "sin-compuerta" in caplog.text or "fuerza" in caplog.text


def test_la_negativa_se_registra_en_el_log(caplog):
    import logging

    X, yc, ys = _conjunto(0, 200)
    with caplog.at_level(logging.ERROR, logger=tr.logger.name):
        tr.train_export("alfa1", X, yc, ys)
    assert "NO se escribe el modelo" in caplog.text


# ─── El número tiene que quedar guardado, no solo dicho ──────────────────────

def test_la_habilidad_viaja_al_metadato(tmp_path, monkeypatch):
    """`models_meta.json` no guardaba ni un número de calidad. Si la habilidad
    no se persiste, «no se escribió» llega sin su motivo y hay que adivinarlo
    --- regla dura 10."""
    monkeypatch.setattr(tr, "load_firmas_from_db", lambda p: {})
    monkeypatch.setattr(tr, "load_juez_feedback", lambda p: {})
    X, yc, ys = _conjunto(0, 200)

    def _falso_merge(bot, firmas, min_samples):
        if bot != "alfa1":
            return None, None, None, None, "sin material"
        return X, yc, ys, None, "prueba"

    monkeypatch.setattr(tr, "merge_or_bootstrap", _falso_merge)
    res = tr.retrain("/no/existe.db", bots=["alfa1"])

    assert res["alfa1"]["reentrenado"] is False
    assert res["alfa1"]["path"] is None
    hab = res["alfa1"]["habilidad"]
    assert hab["auc"] is None and "degenerado" in hab["motivo"]

    meta = json.loads((tmp_path / "models_meta.json").read_text())
    assert meta["compuerta"]["auc_minima"] == tr.AUC_MINIMA
    assert meta["compuerta"]["activa"] is True
    assert "alfa1" in meta["compuerta"]["niega"]
    assert meta["bots"]["alfa1"]["habilidad"]["motivo"]


def test_el_mae_en_muestra_queda_etiquetado_como_tal():
    """Ese número fue durante meses el único control de calidad y no mide
    generalización. Que su nombre lo diga, para que nadie lo vuelva a leer como
    si fuera habilidad."""
    import inspect

    fuente = inspect.getsource(tr.train_export)
    assert "MAE EN MUESTRA" in fuente
    assert "no mide" in fuente
