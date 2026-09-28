"""El Kp del ciclo vivo tiene que salir de la ventana de la firma, no del feed.

Hallazgo de Agente-C, verificado el 2026-09-27 contra la fuente en vivo.

`kp_max_72h` se calculaba como `max(kp_series[-24:])` con un comentario que
decía «la serie viene en tramos de 3 h: las últimas 24 muestras son 72 h».
Medido contra el endpoint real (`planetary_k_index_1m.json`):

    filas 358 · paso 1,0 min · span 5,95 h

Es decir: **24 minutos**, y 72 h necesitarían 4.320 muestras que ese feed no
tiene ni puede tener. Mismo nombre, cantidades que difieren 180×.

Y no era sólo ese rasgo. Los tres del Kp salían de una ventana de ~6 h donde el
entrenamiento usa 336 h (`signature_engine.extraer_features_ventana`), medido la
misma noche contra `tbl_clima_espacial_raw`:

    rasgo          entrenamiento (336/72 h)   ciclo vivo (feed de 6 h)
    kp_mean                 1,96                      ≈ 0,30
    kp_max                  4,00                        1,00
    kp_max_72h              4,00                       0,000

La distribución con la que se entrenó tiene p5 = 0,896 y mediana 1,742, así que
el ciclo entregaba el Kp por debajo de su percentil 5 de forma permanente --- y
los modelos de alfa1, loki y omega, que además tenían fuga de procedencia en
`kp_mean` (`test_fuga_de_procedencia.py`), leían eso como alarma. Medido con los
modelos vigentes y todo lo demás fijo:

    bot     Kp del feed (antes)   Kp de la ventana (ahora)
    alfa1     WATCH     0,6771     NO_SIGNAL    0,2150
    omega     WATCH     0,6149     NO_SIGNAL    0,2630
    loki      WATCH     0,8200     NO_SIGNAL    0,3500

loki pasaba de 0,82, o sea por encima del veto bayesiano de 0,8 del tercer acto.

**Lo que esto NO arregla:** la fuga sigue dentro del modelo. Lo que cambia es que
el ciclo ya no le sirve un Kp casi nulo. Un Kp real bajo en una quincena tranquila
volvería a dispararlo, y eso sólo muere reentrenando con las firmas regeneradas.
"""
import sqlite3

import pytest


class _Runner:
    """El feed de 1 min dice 9,0 en todo; la tabla horaria dice otra cosa.

    Deliberadamente contradictorio: si el rasgo saliera del feed, el 9,0
    aparecería en el resultado.
    """
    class pipeline:
        _cache = {"beta1": {"kp_series": [9.0] * 400}}


@pytest.fixture
def base(tmp_path):
    conn = sqlite3.connect(tmp_path / "kp.db")
    conn.execute(
        "CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT, "
        "kp_promedio REAL, kp_max REAL)"
    )
    # Dentro de 72 h el máximo es 4,0; entre 72 h y 336 h hay un 7,0. Así las
    # dos ventanas NO pueden salir iguales, que es el síntoma que delataría que
    # se está usando una sola.
    conn.executemany(
        "INSERT INTO tbl_clima_espacial_raw VALUES (datetime('now', ?), ?, ?)",
        [("-2 hours", 1.0, 2.0), ("-40 hours", 3.0, 4.0),
         ("-200 hours", 5.0, 7.0), ("-300 hours", 1.0, 1.0),
         # Fuera de la ventana de 336 h: no debe entrar en ningún promedio.
         ("-400 hours", 9.0, 9.0)],
    )
    conn.commit()
    return conn


def _rasgos(conn):
    from sentinel_omega.launcher import _build_live_features
    return _build_live_features(_Runner(), conn) or {}


def test_kp_max_72h_es_de_72_horas(base):
    """4,0 es el máximo dentro de 72 h. El 7,0 de hace 200 h queda fuera."""
    assert _rasgos(base)["kp_max_72h"] == 4.0


def test_kp_max_es_de_la_ventana_completa(base):
    """336 h → 7,0. Si diera 4,0, estaría usando la subventana para las dos."""
    assert _rasgos(base)["kp_max"] == 7.0


def test_las_dos_ventanas_no_pueden_dar_lo_mismo(base):
    """El síntoma de usar una sola fuente para dos rasgos distintos."""
    f = _rasgos(base)
    assert f["kp_max"] != f["kp_max_72h"]


def test_kp_mean_promedia_la_ventana_de_336_h(base):
    """(1+3+5+1)/4 = 2,5. El 9,0 de hace 400 h no entra."""
    assert _rasgos(base)["kp_mean"] == pytest.approx(2.5)


def test_el_feed_de_un_minuto_ya_no_alimenta_estos_rasgos(base):
    """El feed dice 9,0 en sus 400 muestras y ninguno de los tres lo refleja."""
    f = _rasgos(base)
    for clave in ("kp_mean", "kp_max", "kp_max_72h"):
        assert f[clave] != 9.0, f"{clave} sigue saliendo de kp_series"


def test_sin_tabla_el_rasgo_queda_AUSENTE_no_en_cero(tmp_path):
    """Regla 7: faltante es faltante. Un 0,0 aquí es «campo quieto» para el
    modelo, y es justo el cero que costó 792 falsas alarmas en alfa1."""
    conn = sqlite3.connect(tmp_path / "vacia.db")
    f = _rasgos(conn)
    for clave in ("kp_mean", "kp_max", "kp_max_72h"):
        assert clave not in f, f"{clave} se inventó sin fuente"


def test_sin_conexion_tampoco_se_inventa():
    from sentinel_omega.launcher import _build_live_features
    f = _build_live_features(_Runner(), None) or {}
    for clave in ("kp_mean", "kp_max", "kp_max_72h"):
        assert clave not in f


def test_el_feed_real_no_puede_cubrir_72_horas():
    """La razón de fondo, fijada como prueba: `planetary_k_index_1m.json` es de
    1 minuto. Si alguien vuelve a leer `kp[-24:]` como 72 h, esto lo explica.

    No pega a la red: comprueba que el código sigue apuntando a ese endpoint.
    """
    import inspect

    from sentinel_omega.infrastructure.api import noaa

    fuente = inspect.getsource(noaa.fetch_kp_index)
    assert "planetary_k_index_1m.json" in fuente, (
        "cambió el endpoint del Kp: vuelve a medir su resolución y su span "
        "antes de tratar N muestras como N×3 horas")
    # 72 h a 1 min son 4.320 muestras: 24 no alcanzan ni para media hora.
    assert 72 * 60 / 1 == 4320
