"""La auditoría automática: que detecte lo que hoy depende de que alguien mire.

Y, sobre todo, que NO invente. Un detector ruidoso se desactiva a la semana y
entonces no detecta nada; es peor que no tenerlo.

La prueba que más importa aquí es `test_no_dispara_con_un_bot_plano_por_diseño`:
la primera versión del chequeo de varianza disparaba con «12 ciclos iguales», y
medido contra 229 ciclos reales los bots están en su valor de suelo el 66-86 %
del tiempo. Disparaba solo. Regla dura 8 aplicada al propio detector.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

aud = pytest.importorskip("deploy.auditoria_automatica")


def _base(tmp_path, filas_bot=None, clima_atraso_h=None):
    db = tmp_path / "SENTINEL_OMEGA_PRO.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (timestamp REAL, bot_name TEXT, "
              "prediccion TEXT, confianza REAL, fase TEXT)")
    c.execute("CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT, kp_max REAL)")
    if filas_bot:
        c.executemany(
            "INSERT INTO TBL_JUEZ_AUDITORIA VALUES "
            "(strftime('%s','now')-?, ?, 'neutral', ?, 'viva')", filas_bot)
    if clima_atraso_h is not None:
        c.execute("INSERT INTO tbl_clima_espacial_raw VALUES "
                  "(datetime('now', ?), 2.0)", (f"-{clima_atraso_h} hours",))
    c.commit()
    return c, db


def test_es_de_solo_lectura(tmp_path, monkeypatch):
    """Una auditoría que escribe puede romper lo que audita."""
    c, db = _base(tmp_path, clima_atraso_h=1)
    monkeypatch.setattr(aud, "DB", db)
    conn = aud._conn()
    assert conn is not None
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("CREATE TABLE intruso (x INT)")


def test_frescura_caza_una_fuente_parada(tmp_path, monkeypatch):
    """El chequeo que sí cazó lo del 2026-09-28: la tabla horaria del Kp dejó
    de crecer y las ventanas del vector se congelaron en ese borde."""
    c, db = _base(tmp_path, clima_atraso_h=30)
    monkeypatch.setattr(aud, "DB", db)
    h = aud.chequeo_frescura(aud._conn())
    nombres = [x.titulo for x in h]
    assert any("tbl_clima_espacial_raw" in n for n in nombres), nombres
    assert all(x.evidencia for x in h), "un hallazgo sin evidencia no sirve"


def test_frescura_calla_si_la_fuente_esta_al_dia(tmp_path, monkeypatch):
    c, db = _base(tmp_path, clima_atraso_h=1)
    monkeypatch.setattr(aud, "DB", db)
    assert aud.chequeo_frescura(aud._conn()) == []


def test_no_dispara_con_un_bot_plano_por_diseño(tmp_path, monkeypatch):
    """alfa2 lleva 664 ciclos planos porque no tiene datos satelitales, no
    porque se haya roto algo. Si el detector lo reporta cada noche, se apaga."""
    filas = [(i * 300, "alfa2", 0.2) for i in range(200)]
    c, db = _base(tmp_path, filas_bot=filas)
    monkeypatch.setattr(aud, "DB", db)
    h = aud.chequeo_varianza(aud._conn(), aud.CICLOS_VARIANZA)
    assert h == [], f"disparó con un bot plano por diseño: {[x.titulo for x in h]}"


def test_la_varianza_nunca_es_alarma(tmp_path, monkeypatch):
    """Es un síntoma para un humano, no un detector. Mientras la línea base esté
    contaminada por los días rotos, no puede ser gravedad alta."""
    import inspect
    fuente = inspect.getsource(aud.chequeo_varianza)
    assert 'gravedad="info"' in fuente
    assert 'gravedad="alto"' not in fuente


def test_las_fugas_declarativas_se_auditan():
    """Hoy no hay ninguna; el chequeo tiene que seguir sabiendo mirarlas."""
    h = aud.chequeo_fugas()
    assert h == [], f"fugas vivas: {[x.titulo for x in h]}"


def test_cada_hallazgo_dice_por_que_importa():
    """Un informe sin el porqué obliga a rehacer el diagnóstico cada vez."""
    ejemplo = aud.Hallazgo(chequeo="x", gravedad="alto", titulo="t",
                           evidencia={"n": 1}, porque_importa="razón")
    texto = ejemplo.texto()
    assert "ALTO" in texto and "n: 1" in texto and "razón" in texto


def test_las_paradas_conocidas_no_son_novedad():
    """Reportar cada noche lo que ya se sabe es ruido; se listan aparte."""
    assert "tbl_desgasificacion_raw" in aud.PARADAS_CONOCIDAS
    assert "tbl_psique_financiera" in aud.PARADAS_CONOCIDAS
