"""Un número por bot aplasta al especialista.

Lo planteó el operador: «tal vez en esto estás mal, pero para tal evento
siempre le has atinado». Medido el 2026-09-26 sobre la fase de trasfondo, que
es la que discrimina (la de reconocimiento tiene 984.413 veredictos y TODOS son
ACIERTO: ahí todos los bots son perfectos en todo y no se puede aprender nada):

    bot         M3             M4             M5
    padre    65/133 (49 %)  331/543 (61 %)   2/29 ( 7 %)   <- el mejor en M3
    beta1    45/133 (34 %)  413/543 (76 %)   1/29 ( 3 %)   <- el mejor en M4
    beta2    12/133 ( 9 %)  121/543 (22 %)  11/29 (38 %)   <- el mejor en M5
    omega    52/133 (39 %)  383/543 (71 %)   1/29 ( 3 %)
    jupiter   0/133 ( 0 %)   60/543 (11 %)   0/29 ( 0 %)

beta2 es MALO en M3 y M4 y el MEJOR en M5 --- los eventos más grandes medidos.
Con un solo número era un bot flojo; por clase es el especialista.
"""
import sqlite3

import pytest

from sentinel_omega.core.juez.pesos import (
    MINIMO_POR_CLASE,
    PESO_MAX,
    PESO_MIN,
    _clase_de,
    competencia_por_clase,
    pesos_por_competencia,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (bot_name TEXT, verdad TEXT, "
              "resultado TEXT, fase TEXT)")
    return c


def _sembrar(conn, bot, clase, vistos, perdidos, fase="trasfondo"):
    filas = ([(bot, f"2026-01-01 00:00|nodo1|{clase}.1", "ACIERTO", fase)] * vistos
             + [(bot, f"2026-01-01 00:00|nodo1|{clase}.1", "FALLO", fase)] * perdidos)
    conn.executemany("INSERT INTO TBL_JUEZ_AUDITORIA VALUES (?,?,?,?)", filas)
    conn.commit()


def test_la_clase_sale_de_la_verdad():
    assert _clase_de("2026-09-23 16:38|nodo19|M3.4") == "M3"
    assert _clase_de("1 eventos en ventana de 2h (máx M5.0, global)") == "M5"
    assert _clase_de("sin eventos en ventana de 2h") is None
    assert _clase_de("") is None


def test_cada_bot_tiene_su_perfil_por_clase(conn):
    _sembrar(conn, "b", "M4", vistos=30, perdidos=10)
    _sembrar(conn, "b", "M6", vistos=5, perdidos=25)
    perfil = competencia_por_clase(conn)["b"]
    assert perfil["M4"]["tasa"] == pytest.approx(0.75)
    assert perfil["M6"]["tasa"] == pytest.approx(1 / 6)


def test_una_clase_con_pocos_eventos_no_se_juzga(conn):
    _sembrar(conn, "b", "M7", vistos=2, perdidos=1)
    assert competencia_por_clase(conn) == {}
    assert "M7" in competencia_por_clase(conn, minimo=3).get("b", {})


def test_el_especialista_conserva_su_voz(conn):
    """El caso de beta2: malo en general, el mejor en la clase grande."""
    _sembrar(conn, "generalista", "M4", vistos=40, perdidos=10)   # 80 %
    _sembrar(conn, "generalista", "M6", vistos=5, perdidos=45)    # 10 %
    _sembrar(conn, "especialista", "M4", vistos=10, perdidos=40)  # 20 %
    _sembrar(conn, "especialista", "M6", vistos=40, perdidos=10)  # 80 %
    pesos = pesos_por_competencia(conn)
    assert pesos["especialista"] == pytest.approx(1.0)
    assert pesos["generalista"] == pytest.approx(1.0)


def test_el_que_no_ve_nada_baja_al_suelo(conn):
    _sembrar(conn, "bueno", "M4", vistos=40, perdidos=10)
    _sembrar(conn, "ciego", "M4", vistos=0, perdidos=50)
    pesos = pesos_por_competencia(conn)
    assert pesos["bueno"] == pytest.approx(1.0)
    assert pesos["ciego"] == PESO_MIN


def test_el_peso_respeta_suelo_y_techo(conn):
    _sembrar(conn, "a", "M4", vistos=50, perdidos=0)
    _sembrar(conn, "b", "M4", vistos=1, perdidos=49)
    for p in pesos_por_competencia(conn).values():
        assert PESO_MIN <= p <= PESO_MAX


def test_la_fase_de_reconocimiento_no_cuenta(conn):
    """Sus 984.413 veredictos son todos ACIERTO: incluirla haría a todos
    perfectos y borraría cualquier diferencia."""
    _sembrar(conn, "b", "M4", vistos=50, perdidos=0, fase="reconocimiento")
    assert competencia_por_clase(conn) == {}


def test_la_fase_viva_si_cuenta(conn):
    _sembrar(conn, "b", "M5", vistos=15, perdidos=15, fase="viva")
    assert "M5" in competencia_por_clase(conn)["b"]


def test_sin_datos_no_se_inventan_pesos(conn):
    assert pesos_por_competencia(conn) == {}


def test_los_pesos_llegan_al_padre(conn):
    """De la competencia al voto, sin saltarse un paso."""
    from sentinel_omega.core.juez.pesos import cargar_pesos
    conn.execute("CREATE TABLE TBL_PESOS_BOTS (bot_name TEXT PRIMARY KEY, peso REAL)")
    conn.execute("INSERT INTO TBL_PESOS_BOTS VALUES ('ciego', 1.0)")
    _sembrar(conn, "bueno", "M4", vistos=40, perdidos=10)
    _sembrar(conn, "ciego", "M4", vistos=0, perdidos=50)
    conn.commit()
    pesos = cargar_pesos(conn, por_merito=True)
    assert pesos["ciego"] == PESO_MIN       # el almacenado (1.0) queda atrás
    assert int(pesos["_competencias_aplicadas"]) == 2


def test_el_minimo_por_clase_es_razonable():
    assert MINIMO_POR_CLASE >= 10, "con menos, la tasa por clase es ruido"
