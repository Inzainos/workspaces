"""La disciplina no puede premiar a quien no participa.

Medido el 2026-09-25/26 sobre la fase viva:

    alfa1    669 alarmas, 664 falsos positivos  ->  peso 0.300 (el suelo)
    jupiter  216 alarmas, 216 falsos positivos  ->  peso 1.000
    loki       0 alarmas,   0 castigos, 37 eventos perdidos -> peso 1.000
    delta      0 alarmas,   0 castigos, 37 eventos perdidos -> peso 1.000

El que se moja acumula falsos positivos y se hunde; el que calla acumula
«aciertos» por silencio --- el 98,9 % de los aciertos son «dije calma y hubo
calma» --- y se queda en el techo. Y por episodios, alfa1 era el MÁS preciso de
los nueve (12,5 %).

Ahora solo refuerza el acierto que costó algo: haber alarmado y que el evento
ocurriera. Acertar callando es lo esperable, no un mérito.
"""
import inspect

from sentinel_omega.infrastructure.pipeline import verificacion


def _fuente():
    return inspect.getsource(verificacion.verificar_juez)


def test_el_silencio_acertado_ya_no_refuerza():
    f = _fuente()
    assert "predijo in ALERT_SIGNALS and hubo_evento" in f
    assert "silencios_acertados" in f


def test_el_acierto_con_alarma_si_refuerza():
    f = _fuente()
    i = f.index("predijo in ALERT_SIGNALS and hubo_evento")
    bloque = f[i:i + 260]
    assert "reforzar(conn, bot)" in bloque


def test_la_verdad_viaja_en_el_veredicto():
    """Sin ella la disciplina no puede distinguir los dos tipos de acierto."""
    from sentinel_omega.core.juez import juez
    f = inspect.getsource(juez)
    i = f.index('"gravedad": float(max(1.0, gravedad))')
    assert '"verdad": verdad' in f[i:i + 400]


def test_se_registra_cuantos_silencios_no_reforzaron():
    """Para poder ver en el log que el cambio está actuando."""
    f = _fuente()
    assert "silencios acertados que ya NO refuerzan" in f


def test_los_dos_castigos_siguen_en_pie():
    f = _fuente()
    assert 'res == "FALLO"' in f and 'res == "FALSO_POSITIVO"' in f
    # Y el FALLO sigue pesando por gravedad, no plano.
    assert "gravedad=gravedad" in f
