"""Un sismo no son veintitrés sismos: el filtro de «mismo evento».

Idea del operador, 2026-09-28: *«si te da la misma telemetría, es el mismo
evento. Si ya cambia algún detalle, ahí es otro distinto. Si es la misma que ya
habías detectado, omites hasta que pase su ventana»*.

Por qué hacía falta, medido ese día en producción:

  * el Juez registraba una predicción POR CICLO, cada ~5 min;
  * un solo M4.7 dentro de la ventana de 2 h produjo **23 filas por bot**;
  * el castigo se aplicaba a las 23, no al evento;
  * 184 FALLO en 4 h eran **8 episodios** --- factor **23x**;
  * los pesos de los nueve bots cayeron de 1,425 al suelo de 0,300 en esas
    cuatro horas, y con peso <0,6 el consenso degrada todo a WATCH.

El sistema ya contaba por episodios en el REFUERZO (`merito_relativo` usa
`evaluar_episodios`: «37 ventanas-ciclo con evento eran 3 episodios reales») y
seguía castigando por ciclo. Esto cierra esa mitad.

Se cuenta, no se omite --- el mismo criterio que `tbl_cimatica_patrones`, que
suma +1 a la frecuencia en vez de crear una fila: el episodio guarda cuántos
ciclos lo vieron, así que no se pierde el registro.
"""
import json
import sqlite3

import pytest

from sentinel_omega.infrastructure.pipeline.juez_cycle_register import (
    SIMILITUD_MISMO_EVENTO, _episodio_abierto, _sumar_ciclo,
)

# Telemetría del episodio real del 2026-09-28 (ciclo de alfa1).
BASE = {"bz_mean": -1.83, "bz_min": -6.4, "viento_avg": 431.2, "viento_max": 502.0,
        "kp_mean": 1.94, "kp_max": 4.0, "kp_max_72h": 4.0, "proton_max": 0.29,
        "sismo_count_win": 99.0, "sismo_count_72h": 27.0, "fase_lunar": 0.39}


def _base(tmp_path, filas=()):
    c = sqlite3.connect(tmp_path / "j.db")
    c.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (id INTEGER PRIMARY KEY, "
              "timestamp REAL, bot_name TEXT, fase TEXT, detalles_json TEXT)")
    for bot, hace_s, feats in filas:
        c.execute("INSERT INTO TBL_JUEZ_AUDITORIA (timestamp, bot_name, fase, detalles_json)"
                  " VALUES (strftime('%s','now')-?, ?, 'viva', ?)",
                  (hace_s, bot, json.dumps({"features_generales": feats})))
    c.commit()
    return c


def test_misma_telemetria_dentro_de_la_ventana_es_el_mismo_evento(tmp_path):
    """El caso que costó 176 castigos de más."""
    c = _base(tmp_path, [("alfa1", 600, BASE)])
    assert _episodio_abierto(c, "alfa1", dict(BASE), ventana_h=2) is not None


def test_una_derivacion_pequena_sigue_siendo_el_mismo_evento(tmp_path):
    """Medido: los extremos de un episodio de 23 ciclos daban 0,9775 contra su
    inicio. Si el umbral no tolera eso, el episodio se parte a la mitad."""
    c = _base(tmp_path, [("alfa1", 600, BASE)])
    derivado = dict(BASE, bz_mean=-1.79, viento_avg=438.0, kp_mean=1.97)
    assert _episodio_abierto(c, "alfa1", derivado, ventana_h=2) is not None


def test_telemetria_distinta_es_otro_evento(tmp_path):
    """Medido: un ciclo de hace un día daba 0,8017. Debe abrir fila nueva."""
    c = _base(tmp_path, [("alfa1", 600, BASE)])
    otro = {"bz_mean": 4.1, "bz_min": 0.2, "viento_avg": 310.0, "viento_max": 350.0,
            "kp_mean": 0.3, "kp_max": 1.0, "kp_max_72h": 1.0, "proton_max": 0.1,
            "sismo_count_win": 12.0, "sismo_count_72h": 2.0, "fase_lunar": 0.9}
    assert _episodio_abierto(c, "alfa1", otro, ventana_h=2) is None


def test_fuera_de_la_ventana_es_otro_evento(tmp_path):
    """«Si pasa su ventana, se cataloga como nuevo evento» --- aunque la
    telemetría sea idéntica."""
    c = _base(tmp_path, [("alfa1", 3 * 3600, BASE)])
    assert _episodio_abierto(c, "alfa1", dict(BASE), ventana_h=2) is None


def test_no_se_cruzan_los_bots(tmp_path):
    """El episodio es POR BOT: el de beta1 no cierra el de alfa1."""
    c = _base(tmp_path, [("beta1", 600, BASE)])
    assert _episodio_abierto(c, "alfa1", dict(BASE), ventana_h=2) is None


def test_sin_telemetria_no_filtra(tmp_path):
    """Ante la duda se registra: es el comportamiento de antes, y perder una
    prediccion es peor que registrar una de mas."""
    c = _base(tmp_path, [("alfa1", 600, BASE)])
    assert _episodio_abierto(c, "alfa1", {}, ventana_h=2) is None
    assert _episodio_abierto(None, "alfa1", dict(BASE), ventana_h=2) is None


def test_sin_fila_previa_no_filtra(tmp_path):
    c = _base(tmp_path)
    assert _episodio_abierto(c, "alfa1", dict(BASE), ventana_h=2) is None


def test_el_ciclo_se_cuenta_no_se_pierde(tmp_path):
    """Contar, no omitir: el episodio guarda cuantos ciclos lo vieron."""
    c = _base(tmp_path, [("alfa1", 600, BASE)])
    fid = _episodio_abierto(c, "alfa1", dict(BASE), ventana_h=2)
    for _ in range(4):
        _sumar_ciclo(c, fid)
    d = json.loads(c.execute("SELECT detalles_json FROM TBL_JUEZ_AUDITORIA WHERE id=?",
                             (fid,)).fetchone()[0])
    assert d["ciclos"] == 5, d
    assert d["features_generales"], "se perdio la telemetria del episodio"


def test_el_umbral_esta_calibrado_no_inventado():
    """Regla dura 8. Entre 0,9775 (peor caso del mismo episodio) y 0,8017
    (evento distinto). Si alguien lo mueve fuera de ese hueco, que falle."""
    assert 0.81 < SIMILITUD_MISMO_EVENTO < 0.977


def test_el_registrador_no_abre_fila_si_el_episodio_sigue(tmp_path, monkeypatch):
    """De punta a punta: con un episodio abierto, `register_cycle_predictions`
    suma ciclo y NO llama a `registrar_prediccion`."""
    from sentinel_omega.infrastructure.pipeline import juez_cycle_register as jcr

    c = _base(tmp_path, [("alfa1", 600, BASE)])
    llamadas = []

    class _Juez:
        def registrar_prediccion(self, **kw):
            llamadas.append(kw.get("bot_name"))

    class _Sig:
        agent_name = "alfa1"
        confidence = 0.3
        reasoning = "regla"
        data = {}

        class signal_type:
            value = "neutral"

    class _Geo:
        agent_signals = [_Sig()]
        confidence = 0.3

        class final_signal:
            value = "neutral"

    monkeypatch.setattr(_Juez, "registrar_prediccion", _Juez.registrar_prediccion)
    jcr.register_cycle_predictions(_Juez(), _Geo(), conn=c, features=dict(BASE))
    assert "alfa1" not in llamadas, "abrio fila nueva para el mismo evento"


class _JuezEspia:
    def __init__(self):
        self.llamadas = []

    def registrar_prediccion(self, **kw):
        self.llamadas.append(kw.get("bot_name"))


class _GeoVacio:
    """Consenso sin bots: aisla al padre, que se registra FUERA del bucle."""
    agent_signals = []
    confidence = 0.4

    class final_signal:
        value = "neutral"


def test_el_padre_tambien_entra_al_filtro(tmp_path):
    """El padre quedo FUERA del filtro hasta el 2026-10-01, porque su registro
    vive antes del bucle de bots.

    Medido ese dia en produccion, con el filtro ya vivo para los ocho:

        los ocho bots   2.304 filas -> 320 filas   factor 7,2x
        el padre          290 filas -> 290 filas   factor 1,0x

    Y el padre es el unico que paga DOBLE (`CASTIGO_PADRE = 0.90` contra
    `CASTIGO_HIJO = 0.95`), asi que el sobrecastigo de 23x seguia intacto en el
    voto que pondera a los demas."""
    from sentinel_omega.infrastructure.pipeline import juez_cycle_register as jcr

    c = _base(tmp_path, [("padre", 600, BASE)])
    juez = _JuezEspia()
    jcr.register_cycle_predictions(juez, _GeoVacio(), conn=c, features=dict(BASE))
    assert "padre" not in juez.llamadas, "el padre sigue abriendo fila por ciclo"

    d = json.loads(c.execute(
        "SELECT detalles_json FROM TBL_JUEZ_AUDITORIA WHERE bot_name='padre'"
    ).fetchone()[0])
    assert d["ciclos"] == 2, d


def test_el_padre_sin_episodio_abierto_si_registra(tmp_path):
    """Control: el filtro no puede dejar al padre sin voz. Sin episodio previo
    la fila se abre igual que antes."""
    from sentinel_omega.infrastructure.pipeline import juez_cycle_register as jcr

    c = _base(tmp_path)
    juez = _JuezEspia()
    jcr.register_cycle_predictions(juez, _GeoVacio(), conn=c, features=dict(BASE))
    assert juez.llamadas == ["padre"], juez.llamadas


def test_el_padre_no_cierra_su_episodio_con_telemetria_distinta(tmp_path):
    """Mismo criterio que los hijos: si cambia la telemetria, es otro evento."""
    from sentinel_omega.infrastructure.pipeline import juez_cycle_register as jcr

    c = _base(tmp_path, [("padre", 600, BASE)])
    otro = {"bz_mean": 4.1, "bz_min": 0.2, "viento_avg": 310.0, "viento_max": 350.0,
            "kp_mean": 0.3, "kp_max": 1.0, "kp_max_72h": 1.0, "proton_max": 0.1,
            "sismo_count_win": 12.0, "sismo_count_72h": 2.0, "fase_lunar": 0.9}
    juez = _JuezEspia()
    jcr.register_cycle_predictions(juez, _GeoVacio(), conn=c, features=otro)
    assert juez.llamadas == ["padre"], juez.llamadas
