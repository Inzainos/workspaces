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


def test_el_ritmo_del_juez_es_de_4h_y_se_autoimpone():
    """Orden del operador (2026-09-30): revisiones del Juez cada 4 h.

    AGENTS.md, el encabezado de verificacion_juez.py y el comentario de
    rutinas_locales.sh SIEMPRE dijeron 4 h; el código decía RITMO_HORAS=2 y
    además el caller pasaba forzar=True, que pisaba el ritmo: la verificación
    corría forzada cada 2 h. Este test fija las dos puntas del acuerdo."""
    assert verificacion.RITMO_HORAS == 4
    fuente = inspect.getsource(verificacion.verificar_juez)
    i = fuente.index("if not forzar and ultima")
    assert "RITMO_HORAS * 3600" in fuente[i:i + 200]
    # Y el vigilante ya no fuerza (el llamado va sin forzar):
    lanzador = (
        __import__("pathlib").Path("deploy/verificacion_juez.py").read_text()
    )
    assert "verificar_juez(conn)" in lanzador
    assert "verificar_juez(conn, forzar=True)" not in lanzador


def test_la_pasada_se_salta_si_la_ultima_resolucion_es_reciente(tmp_path):
    """La puerta: última resolución hace <4 h → saltada; forzar la abre."""
    import sqlite3
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    db = tmp_path / "juez.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE TBL_JUEZ_AUDITORIA (resuelto_at TEXT, fase TEXT)")
    hace_1h = datetime.now(timezone.utc).replace(
        microsecond=0) - timedelta(hours=1)
    ts = hace_1h.strftime("%Y-%m-%d %H:%M:%S")
    con.execute("INSERT INTO TBL_JUEZ_AUDITORIA VALUES (?, 'viva')", (ts,))
    con.commit()

    with patch.object(verificacion, "RITMO_HORAS", 4):
        r = verificacion.verificar_juez(con)  # sin forzar: la puerta cierra
        assert r.get("saltada") is True

    # forzar abre la puerta: llega HASTA el fetch de USGS (parcheado para
    # no tocar la red) — el motivo «usgs_caido» demuestra que el ritmo
    # ya fue respetado y pasado por encima.
    with patch.object(verificacion, "RITMO_HORAS", 4), \
         patch("sentinel_omega.infrastructure.api.usgs.fetch_earthquakes",
               return_value=None):
        r = verificacion.verificar_juez(con, forzar=True)
        assert r.get("saltada") is True and r.get("motivo") == "usgs_caido"
    con.close()
