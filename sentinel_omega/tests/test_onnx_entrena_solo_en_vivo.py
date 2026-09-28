"""El reentrenamiento ONNX solo aprende de filas del Juez medidas en vivo.

Origen (2026-09-27): 594 filas de `TBL_JUEZ_AUDITORIA` con fase='viva' salieron
de un proceso duplicado viejo que arrastraba la fuga de `kp_mean`; se marcaron
`en_vivo=0` (387 de ellas ya resueltas). `load_juez_feedback` filtraba solo por
fase, así que esas etiquetas seguían entrando al entrenamiento.

NULL cuenta como vivo: es el mismo criterio que `COALESCE(en_vivo,1)=1` en el
resto de lectores (las filas anteriores a la bandera no la tienen).

Ninguna prueba escribe en la DB ni en los modelos de producción.
"""
import logging
import sqlite3

from sentinel_omega.models import train_onnx_from_db as tr

RASGOS = '{"kp_mean": 5.0, "bz_mean": -3.0}'


def _db(tmp_path, filas, con_en_vivo=True):
    """DB mínima. `filas`: (prediccion, resultado, en_vivo)."""
    ruta = tmp_path / "juez.db"
    conn = sqlite3.connect(ruta)
    # Mismo esquema que producción: `en_vivo INTEGER DEFAULT 1`.
    extra = ", en_vivo INTEGER DEFAULT 1" if con_en_vivo else ""
    conn.execute(
        "CREATE TABLE TBL_JUEZ_AUDITORIA ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT, prediccion TEXT, "
        "confianza REAL, resultado TEXT, detalles_json TEXT, fase TEXT"
        + extra + ")"
    )
    for pred, res, vivo in filas:
        if con_en_vivo:
            conn.execute(
                "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
                "resultado, detalles_json, fase, en_vivo) "
                "VALUES ('alfa1',?,0.3,?,?,'viva',?)",
                (pred, res, RASGOS, vivo),
            )
        else:
            conn.execute(
                "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, prediccion, confianza, "
                "resultado, detalles_json, fase) "
                "VALUES ('alfa1',?,0.3,?,?,'viva')",
                (pred, res, RASGOS),
            )
    conn.commit()
    conn.close()
    return str(ruta)


def test_la_fila_en_vivo_0_no_entrena_y_la_null_si(tmp_path):
    # en_vivo=1 y NULL son FALLO/ACIERTO con alarma (peso de evento); la de
    # en_vivo=0 es la única FALSO_POSITIVO (NEUTRAL, peso de calma). Si se
    # colara, aparecería una etiqueta NEUTRAL con peso de calma.
    ruta = _db(tmp_path, [
        ("neutral", "FALLO", 1),
        ("alert", "ACIERTO", None),
        ("alert", "FALSO_POSITIVO", 0),
    ])
    X, _, ys, w = tr.load_juez_feedback(ruta)["alfa1"]
    assert len(X) == 2
    assert tr.NEUTRAL not in ys.tolist()
    assert w.tolist() == [tr._SEV_EVENTO, tr._SEV_EVENTO]


def test_si_todas_son_en_vivo_0_no_hay_feedback(tmp_path):
    ruta = _db(tmp_path, [("neutral", "FALLO", 0), ("alert", "ACIERTO", 0)])
    assert tr.load_juez_feedback(ruta) == {}


def _avisos_en_vivo(caplog):
    return [r for r in caplog.records
            if r.levelno == logging.WARNING and "en_vivo" in r.getMessage()]


def test_con_la_columna_no_se_avisa(tmp_path, caplog):
    ruta = _db(tmp_path, [("neutral", "FALLO", 1)])
    with caplog.at_level(logging.WARNING, logger=tr.logger.name):
        tr.load_juez_feedback(ruta)
    assert _avisos_en_vivo(caplog) == []


def test_una_base_sin_la_columna_sigue_entrenando(tmp_path, caplog):
    # Bases anteriores a la bandera: el filtro no puede romper la lectura,
    # pero tiene que AVISAR que no se aplicó (si no, el día que falte la
    # columna en producción las filas en_vivo=0 volverían a entrar en silencio).
    ruta = _db(tmp_path, [("neutral", "FALLO", None), ("alert", "ACIERTO", None)],
               con_en_vivo=False)
    with caplog.at_level(logging.WARNING, logger=tr.logger.name):
        X, _, _, _ = tr.load_juez_feedback(ruta)["alfa1"]
    assert len(X) == 2
    avisos = _avisos_en_vivo(caplog)
    assert len(avisos) == 1
    assert avisos[0].getMessage() == (
        "TBL_JUEZ_AUDITORIA sin en_vivo: se entrena con todas las filas viva"
    )
