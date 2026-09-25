"""La métrica no debe premiar el silencio.

Origen (2026-09-25): el reporte decía «GANANCIA REAL 53.50×» con datos en los
que un bot MUDO sacaba 56.70×. La ganancia se calculaba como
(aciertos / TODAS las ventanas) ÷ tasa base, y el numerador contaba cada «dije
calma y hubo calma» — el 98% de las ventanas. Premiar el silencio contradice
el diseño del Juez, donde un FALLO cuesta 10 o 20 y un falso positivo 1.

Sin base de datos: la función recibe los veredictos ya resueltos.
"""
import pytest

from sentinel_omega.core.precursor.baseline import evaluar_veredictos

CALMA = "sin eventos en ventana de 72h (global)"
EVENTO = "M5.2 a 130 km"


def _filas(calma_ok=0, fallos=0, falsos_pos=0, detectados=0):
    """Las cuatro casillas: (verdad, resultado) tal como los deja el Juez."""
    return (
        [(CALMA, "ACIERTO")] * calma_ok        # calló y hubo calma
        + [(EVENTO, "FALLO")] * fallos         # calló y pasó algo
        + [(CALMA, "FALSO_POSITIVO")] * falsos_pos   # alarmó y no pasó nada
        + [(EVENTO, "ACIERTO")] * detectados   # alarmó y pasó algo
    )


def test_el_bot_mudo_no_tiene_ganancia():
    # 98 calmas acertadas y 2 eventos perdidos: asertividad altísima, cero
    # alarmas. Antes esto daba 56.70x; ahora no hay ganancia que reclamar.
    r = evaluar_veredictos(_filas(calma_ok=98, fallos=2))
    assert r.asertividad == pytest.approx(0.98)
    assert r.alarmas == 0
    assert r.ganancia is None
    assert "indefinida" in r.veredicto


def test_el_mudo_nunca_sale_mejor_que_el_sistema_en_la_ganancia():
    # Mismo mundo (2 eventos en 100 ventanas); el sistema detecta 1 alarmando 3
    # veces. Su ganancia tiene que ser > 1 aunque su asertividad BAJE respecto
    # al mudo, que es justo lo que la vieja fórmula castigaba.
    sistema = evaluar_veredictos(_filas(calma_ok=96, fallos=1, falsos_pos=2, detectados=1))
    mudo = evaluar_veredictos(_filas(calma_ok=98, fallos=2))
    assert sistema.asertividad < mudo.asertividad      # peor en el número bonito
    assert sistema.ganancia > 1.0                      # mejor en el que importa
    assert mudo.ganancia is None


def test_un_sistema_con_habilidad_da_ganancia_real():
    # 2 eventos, los dos detectados, con una sola falsa alarma.
    r = evaluar_veredictos(_filas(calma_ok=97, falsos_pos=1, detectados=2))
    assert r.precision == pytest.approx(2 / 3)
    assert r.tasa_base == pytest.approx(0.02)
    assert r.ganancia > 1.5
    assert "GANANCIA REAL" in r.veredicto


def test_alarmar_a_ciegas_no_da_ganancia():
    # Alarma en TODAS las ventanas: acierta los 2 eventos y falla en las 98
    # restantes. Su precisión ES la tasa base, o sea ganancia exactamente 1.
    r = evaluar_veredictos(_filas(falsos_pos=98, detectados=2))
    assert r.precision == pytest.approx(r.tasa_base)
    assert r.ganancia == pytest.approx(1.0)
    assert "SIN ganancia" in r.veredicto


def test_la_diagonal_de_molchan_marca_la_frontera():
    ciego = evaluar_veredictos(_filas(falsos_pos=98, detectados=2))
    habil = evaluar_veredictos(_filas(calma_ok=97, falsos_pos=1, detectados=2))
    assert ciego.diagonal == pytest.approx(1.0)   # sobre la diagonal: sin habilidad
    assert habil.diagonal < 1.0                   # por debajo: habilidad


def test_el_coste_usa_la_asimetria_del_juez():
    # Callarse con evento cuesta 10; la falsa alarma, 1. Un sistema que evita
    # un FALLO a base de 3 falsas alarmas SALE GANANDO (10 > 3).
    r = evaluar_veredictos(_filas(calma_ok=95, fallos=1, falsos_pos=3, detectados=1),
                           sev_fallo=10.0, sev_falso_positivo=1.0)
    assert r.coste_sistema == 1 * 10 + 3 * 1      # 13
    assert r.coste_mudo == 2 * 10                 # 20: peor, como debe ser
    assert r.coste_sistema < r.coste_mudo


def test_el_umbral_rentable_sale_de_las_severidades():
    # Con 10 y 1, alarmar paga cuando la probabilidad de evento supera 1/11.
    r = evaluar_veredictos(_filas(calma_ok=98, fallos=1, detectados=1))
    assert r.umbral_rentable == pytest.approx(1 / 11)
    # Si el silencio se castigara el doble, alarmar sería rentable más pronto.
    r2 = evaluar_veredictos(_filas(calma_ok=98, fallos=1, detectados=1),
                            sev_fallo=20.0, sev_falso_positivo=1.0)
    assert r2.umbral_rentable < r.umbral_rentable


def test_sin_veredictos_no_se_inventa_nada():
    assert evaluar_veredictos([]) is None


def test_un_mundo_sin_eventos_no_da_ganancia():
    r = evaluar_veredictos(_filas(calma_ok=50, falsos_pos=50))
    assert r.tasa_base == 0.0
    assert r.ganancia is None
    assert r.deteccion is None


def test_el_veredicto_no_depende_del_vocabulario_de_predicciones():
    # La función solo ve (verdad, resultado): da igual que la capa diga
    # «watch», «alert» o «rojo». Un ACIERTO con evento ES una alarma.
    r = evaluar_veredictos([(EVENTO, "ACIERTO"), (CALMA, "ACIERTO")])
    assert r.alarmas == 1 and r.detectados == 1
