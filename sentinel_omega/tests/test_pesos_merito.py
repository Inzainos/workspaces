"""El peso de un bot tiene que decir si aporta algo, no si sobrevivió a la calma.

Origen (2026-09-25): 8 de los 9 bots estaban clavados en el techo 1.0 y un
castigo se borraba en 5,9 horas de mediana, porque cada ACIERTO reforzaba y el
98,9 % de los aciertos son «dije calma y hubo calma». Se replicaron los 19.422
veredictos reales con tres reglas de refuerzo: o todos al techo (dispersión
0.072) o todos al suelo (0.017). El paseo multiplicativo no puede expresar
mérito relativo; hay que medirlo contra la estrategia tonta.
"""
import sqlite3

import pytest

from sentinel_omega.core.juez.pesos import (
    PESO_MAX,
    PESO_MIN,
    merito_relativo,
    pesos_por_merito,
)

# Estos tests miden la ARITMÉTICA del mérito, no el freno de evidencia (ese
# está en test_episodios.py): por eso pasan `minimo_eventos=1`. Sin decirlo,
# todos devolverían None y pasarían en verde sin comprobar nada.
CALMA = "sin eventos en ventana de 72h (global)"
EVENTO = "M5.2 a 130 km"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE TBL_JUEZ_AUDITORIA (timestamp REAL, bot_name TEXT, "
        "verdad TEXT, resultado TEXT, fase TEXT)"
    )
    return c


# Cada fila va SEPARADA un día: así cada evento y cada alarma son episodios
# distintos y no chocan con el freno de evidencia (ver test_episodios.py, donde
# se mide por qué la cuenta por ciclos multiplicaba la misma evidencia).
_DIA = 86400.0


def _poblar(conn, bot, calma_ok=0, fallos=0, falsos_pos=0, detectados=0, fase="viva"):
    crudas = (
        [(bot, CALMA, "ACIERTO", fase)] * calma_ok
        + [(bot, EVENTO, "FALLO", fase)] * fallos
        + [(bot, CALMA, "FALSO_POSITIVO", fase)] * falsos_pos
        + [(bot, EVENTO, "ACIERTO", fase)] * detectados
    )
    base = conn.execute(
        "SELECT COALESCE(MAX(timestamp), 0) FROM TBL_JUEZ_AUDITORIA "
        "WHERE bot_name = ?", (bot,)).fetchone()[0]
    filas = [(base + (i + 1) * _DIA,) + f for i, f in enumerate(crudas)]
    conn.executemany("INSERT INTO TBL_JUEZ_AUDITORIA VALUES (?,?,?,?,?)", filas)
    conn.commit()


def test_el_bot_mudo_pesa_exactamente_uno(conn):
    # Nunca alarma: su coste ES el del silencio. Ni premio ni castigo.
    _poblar(conn, "mudo", calma_ok=90, fallos=10)
    m = merito_relativo(conn, "mudo", minimo_eventos=1)
    assert m["peso"] == pytest.approx(1.0)
    assert m["ahorro"] == pytest.approx(0.0)


def test_el_que_detecta_barato_pesa_mas(conn):
    # Caza 5 de 10 eventos con 2 falsas alarmas: ahorra 50 de coste, paga 2.
    _poblar(conn, "util", calma_ok=83, fallos=5, falsos_pos=2, detectados=5)
    m = merito_relativo(conn, "util", minimo_eventos=1)
    assert m["peso"] > 1.0
    assert m["coste"] < m["coste_mudo"]


def test_el_que_grita_sin_acertar_pesa_menos(conn):
    _poblar(conn, "griton", calma_ok=40, fallos=10, falsos_pos=50)
    m = merito_relativo(conn, "griton", minimo_eventos=1)
    assert m["peso"] < 1.0


def test_detectar_a_cualquier_precio_no_compensa(conn):
    # Caza los 10 eventos (ahorra 100) pero a costa de 300 falsas alarmas.
    _poblar(conn, "paranoico", calma_ok=0, falsos_pos=300, detectados=10)
    m = merito_relativo(conn, "paranoico", minimo_eventos=1)
    assert m["peso"] < 1.0, "300 falsas alarmas cuestan mas que los 10 eventos"


def test_el_peso_respeta_el_suelo_y_el_techo(conn):
    _poblar(conn, "desastre", calma_ok=0, fallos=10, falsos_pos=5000)
    _poblar(conn, "perfecto", calma_ok=90, detectados=10)
    assert merito_relativo(conn, "desastre", minimo_eventos=1)["peso"] == PESO_MIN
    assert merito_relativo(conn, "perfecto", minimo_eventos=1)["peso"] <= PESO_MAX


def test_con_pocas_ventanas_no_se_juzga(conn):
    # Un peso sacado de 10 ventanas seria ruido, no merito.
    _poblar(conn, "novato", calma_ok=8, fallos=2)
    assert merito_relativo(conn, "novato", minimo_eventos=1) is None
    assert merito_relativo(conn, "novato", minimo_ventanas=5, minimo_eventos=1) is not None


def test_la_fase_de_entrenamiento_no_cuenta(conn):
    # La vara canonica es la fase viva: el reconocimiento es el examen, no la
    # operacion real.
    _poblar(conn, "bot", calma_ok=500, fase="reconocimiento")
    _poblar(conn, "bot", calma_ok=90, fallos=10, fase="viva")
    m = merito_relativo(conn, "bot", minimo_eventos=1)
    assert m["ventanas"] == 100


def test_la_asimetria_del_juez_manda_en_el_peso(conn):
    # Con omitir=10 y falsa alarma=1, cambiar un FALLO por una falsa alarma
    # SIEMPRE conviene. Con severidades iguales, no.
    _poblar(conn, "b", calma_ok=89, fallos=5, falsos_pos=1, detectados=5)
    con_asimetria = merito_relativo(conn, "b", sev_fallo=10.0, sev_falso_positivo=1.0, minimo_eventos=1)
    sin_asimetria = merito_relativo(conn, "b", sev_fallo=1.0, sev_falso_positivo=1.0, minimo_eventos=1)
    assert con_asimetria["peso"] > sin_asimetria["peso"]


def test_todos_los_bots_de_una_vez(conn):
    _poblar(conn, "uno", calma_ok=90, fallos=10)
    _poblar(conn, "dos", calma_ok=83, fallos=5, falsos_pos=2, detectados=5)
    _poblar(conn, "corto", calma_ok=5)
    todos = pesos_por_merito(conn, minimo_eventos=1)
    assert set(todos) == {"uno", "dos"}          # «corto» no llega al mínimo
    assert todos["dos"]["peso"] > todos["uno"]["peso"]


def test_sin_tabla_no_revienta():
    vacia = sqlite3.connect(":memory:")
    assert pesos_por_merito(vacia) == {}
    assert merito_relativo(vacia, "x") is None


def test_un_mundo_sin_eventos_no_da_merito(conn):
    # Sin eventos no hay nada que ahorrar: el merito es indefinido, no cero.
    _poblar(conn, "b", calma_ok=100)
    assert merito_relativo(conn, "b", minimo_eventos=1) is None


def test_el_peso_discrimina_mas_que_el_paseo(conn):
    # La prueba de fondo: con perfiles distintos, los pesos tienen que
    # SEPARARSE. El paseo multiplicativo los dejaba a todos en 1.000.
    import statistics
    _poblar(conn, "bueno", calma_ok=83, fallos=5, falsos_pos=2, detectados=5)
    _poblar(conn, "mudo", calma_ok=90, fallos=10)
    _poblar(conn, "griton", calma_ok=40, fallos=10, falsos_pos=50)
    pesos = [d["peso"] for d in pesos_por_merito(conn, minimo_eventos=1).values()]
    assert statistics.pstdev(pesos) > 0.1


# ─── El umbral de rentabilidad de una alarma ─────────────────────────────────
# Sale de la asimetría del Juez: si omitir cuesta 10 y una falsa alarma 1,
# alarmar conviene cuando P(evento) > 1/(10+1) = 9,1 %.

def test_el_umbral_sale_de_las_severidades(conn):
    _poblar(conn, "b", calma_ok=89, fallos=5, falsos_pos=1, detectados=5)
    m = merito_relativo(conn, "b", sev_fallo=10.0, sev_falso_positivo=1.0, minimo_eventos=1)
    assert m["umbral_rentable"] == pytest.approx(1 / 11)


def test_el_que_alarma_poco_y_bien_pasa_el_liston(conn):
    # El perfil de beta2 medido el 2026-09-25: 12 alarmas, 11 con evento.
    _poblar(conn, "fino", calma_ok=80, fallos=9, falsos_pos=1, detectados=11)
    m = merito_relativo(conn, "fino", minimo_eventos=1)
    assert m["precision"] == pytest.approx(11 / 12)
    assert m["alarma_rentable"] is True


def test_el_que_grita_no_lo_pasa(conn):
    # El perfil de alfa1: 549 alarmas, 5 con evento.
    _poblar(conn, "griton", calma_ok=0, fallos=32, falsos_pos=544, detectados=5)
    m = merito_relativo(conn, "griton", minimo_eventos=1)
    assert m["precision"] < m["umbral_rentable"]
    assert m["alarma_rentable"] is False


def test_el_que_no_alarma_no_tiene_precision(conn):
    # Sin alarmas no hay precisión que medir: None, no cero.
    _poblar(conn, "mudo", calma_ok=90, fallos=10)
    m = merito_relativo(conn, "mudo", minimo_eventos=1)
    assert m["alarmas"] == 0 and m["precision"] is None
    assert m["alarma_rentable"] is False


def test_castigar_mas_el_silencio_baja_el_liston(conn):
    _poblar(conn, "b", calma_ok=85, fallos=5, falsos_pos=5, detectados=5)
    normal = merito_relativo(conn, "b", sev_fallo=10.0, sev_falso_positivo=1.0, minimo_eventos=1)
    duro = merito_relativo(conn, "b", sev_fallo=20.0, sev_falso_positivo=1.0, minimo_eventos=1)
    assert duro["umbral_rentable"] < normal["umbral_rentable"]
