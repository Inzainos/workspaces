"""Un sismo contado veinte veces no son veinte sismos.

Encontrado el 2026-09-25 replicando reglas de consenso sobre los veredictos
reales: los «11 aciertos» de beta2 eran UN SOLO M5.0 contado once veces --- el
bot alarmó en once ciclos seguidos (03:35 a 04:25) y el evento caía dentro de la
ventana de 2 h de los once.

No era cosa de beta2. El ciclo corre cada 5 min y la ventana dura 2 h, así que
un evento puede «confirmar» hasta 24 predicciones y una alarma sostenida cuenta
como decenas de falsas alarmas. Sobre los 17 días de fase viva:

    ventanas-ciclo con evento: 37     episodios de evento REALES:  3
    alfa1 «544 falsas alarmas»        episodios de alarma:         8  (12,5 %)
    beta2 «11 detecciones»            episodios:                   1

Contado así, alfa1 era el MÁS preciso de los nueve, no el peor --- y el peso por
mérito, que se calculaba por ciclos, lo castigaba a 0.300.
"""
import pytest

from sentinel_omega.core.precursor.baseline import (
    HUECO_EPISODIO_S,
    agrupar_episodios,
    evaluar_episodios,
)

H = 3600
CALMA = "sin eventos en ventana de 2h (global)"
EVENTO = "1 eventos en ventana de 2h (máx M5.0, global)"


def _racha(t0, n, paso=300, verdad=CALMA, resultado="FALSO_POSITIVO"):
    """n ciclos seguidos cada `paso` segundos."""
    return [(t0 + i * paso, verdad, resultado) for i in range(n)]


def test_once_ciclos_seguidos_son_un_episodio():
    # El caso literal de beta2: 11 alarmas en 50 minutos, un solo sismo.
    filas = _racha(1000, 11, verdad=EVENTO, resultado="ACIERTO")
    r = evaluar_episodios(filas, minimo_eventos=1)
    assert r["episodios"] == 1
    assert r["ciclos_alarma"] == 11
    assert r["eventos_distintos"] == 1
    assert r["precision"] == 1.0


def test_dos_rachas_separadas_son_dos_episodios():
    filas = _racha(0, 5) + _racha(10 * H, 5)
    assert evaluar_episodios(filas, minimo_eventos=0)["episodios"] == 2


def test_el_hueco_decide_donde_corta():
    filas = _racha(0, 3) + _racha(2 * H, 3)     # 2 h < 3 h de hueco
    assert evaluar_episodios(filas, minimo_eventos=0)["episodios"] == 1
    assert len(agrupar_episodios(filas, hueco_s=H)) == 2


def test_el_mismo_evento_no_se_cuenta_dos_veces():
    # Tres ventanas consecutivas alcanzan el mismo sismo.
    filas = _racha(0, 3, verdad=EVENTO, resultado="ACIERTO")
    assert evaluar_episodios(filas, minimo_eventos=0)["eventos_distintos"] == 1


def test_eventos_lejanos_si_son_distintos():
    filas = (_racha(0, 2, verdad=EVENTO, resultado="ACIERTO")
             + _racha(20 * H, 2, verdad=EVENTO, resultado="ACIERTO"))
    assert evaluar_episodios(filas, minimo_eventos=0)["eventos_distintos"] == 2


def test_el_silencio_no_abre_episodio():
    filas = [(i * 300.0, CALMA, "ACIERTO") for i in range(50)]
    r = evaluar_episodios(filas, minimo_eventos=0)
    assert r["episodios"] == 0 and r["ciclos_alarma"] == 0


def test_los_eventos_se_cuentan_aunque_nadie_alarme():
    # El bot mudo: sin alarmas, pero los eventos del periodo existen. Si se
    # contaran solo dentro de los episodios de alarma, los bots que nunca
    # abren la boca pasarían el freno de evidencia --- justo los que menos
    # tienen. Fue un error cometido DENTRO de este mismo arreglo.
    filas = ([(i * 300.0, CALMA, "ACIERTO") for i in range(20)]
             + _racha(30 * H, 3, verdad=EVENTO, resultado="FALLO"))
    r = evaluar_episodios(filas, minimo_eventos=0)
    assert r["episodios"] == 0
    assert r["eventos_distintos"] == 1


# ─── El freno de evidencia ───────────────────────────────────────────────────

def test_con_pocos_eventos_no_hay_evidencia():
    filas = _racha(0, 5, verdad=EVENTO, resultado="ACIERTO")
    assert evaluar_episodios(filas, minimo_eventos=20)["evidencia_suficiente"] is False


def test_con_suficientes_eventos_si_la_hay():
    filas = []
    for k in range(25):
        filas += _racha(k * 30 * H, 2, verdad=EVENTO, resultado="ACIERTO")
    r = evaluar_episodios(filas, minimo_eventos=20)
    assert r["eventos_distintos"] == 25 and r["evidencia_suficiente"] is True


def test_el_merito_no_se_calcula_sin_evidencia():
    """El freno donde importa: si no hay eventos suficientes, el peso del bot
    se queda como estaba en vez de moverse con ruido."""
    import sqlite3

    from sentinel_omega.core.juez.pesos import cargar_pesos, merito_relativo

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (timestamp REAL, bot_name TEXT, "
                 "verdad TEXT, resultado TEXT, fase TEXT)")
    conn.execute("CREATE TABLE TBL_PESOS_BOTS (bot_name TEXT PRIMARY KEY, peso REAL)")
    conn.execute("INSERT INTO TBL_PESOS_BOTS VALUES ('b', 0.9)")
    # 100 ventanas, pero UN solo episodio de evento: no alcanza.
    filas = [(i * 300.0, CALMA, "ACIERTO") for i in range(90)] + [
        (90 * 300.0 + i * 300.0, EVENTO, "FALLO") for i in range(10)]
    conn.executemany("INSERT INTO TBL_JUEZ_AUDITORIA VALUES (?, 'b', ?, ?, 'viva')", filas)
    conn.commit()
    assert merito_relativo(conn, "b") is None
    assert cargar_pesos(conn, por_merito=True)["b"] == 0.9     # intacto


def test_el_hueco_por_defecto_cubre_la_ventana_del_juez():
    # La ventana viva son 2 h; el hueco tiene que ser mayor para no partir un
    # episodio que sigue tocando el mismo evento.
    assert HUECO_EPISODIO_S > 2 * H
