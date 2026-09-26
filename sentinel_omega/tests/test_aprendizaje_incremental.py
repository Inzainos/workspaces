"""El sistema tiene que poder aprender sin parar 36 horas.

Medido el 2026-09-25: `entrenar_reconocimiento` recorre los 186.806 bloques del
histórico a 1,5 eventos por segundo --- **36 horas** --- y por eso nunca se
programó. Resultado: entre reconstrucciones manuales el sistema dejaba de
aprender, y la última firma era del 23-sep con eventos nuevos desde el 3.

Con el corte por `desde`, los 22 días acumulados se aprendieron en 190 s y
dejaron 89 firmas nuevas: eso sí cabe en el barrido diario.
"""
import sqlite3

import pytest

from sentinel_omega.infrastructure.pipeline.entrenamiento import (
    MIN_MAGNITUD_OBSERVAR,
    entrenar_incremental,
    entrenar_reconocimiento,
    ultimo_bloque_aprendido,
)


@pytest.fixture
def db(tmp_path):
    ruta = tmp_path / "aprende.db"
    conn = sqlite3.connect(ruta)
    conn.executescript("""
        CREATE TABLE tbl_historico_sismico_raw (
            timestamp_blk TEXT NOT NULL, id_nodo INTEGER NOT NULL,
            sismo_count INTEGER, sismo_max_mag REAL,
            PRIMARY KEY (timestamp_blk, id_nodo));
        CREATE TABLE tbl_firma_eventos (
            firma_id INTEGER, evento_ref TEXT, ts_evento TEXT, orden INTEGER);
        CREATE TABLE TBL_FIRMAS (
            firma_id INTEGER PRIMARY KEY AUTOINCREMENT, bot_name TEXT NOT NULL,
            event_class TEXT NOT NULL, id_nodo INTEGER, features_json TEXT NOT NULL,
            ventana_horas INTEGER DEFAULT 336, recurrencia INTEGER DEFAULT 1,
            estado TEXT DEFAULT 'nueva', primera_vista TEXT, ultima_vista TEXT,
            eventos_json TEXT DEFAULT '[]', created_at TEXT);
    """)
    conn.commit()
    return str(ruta), conn


def test_sin_firmas_previas_no_hay_corte(db):
    ruta, _ = db
    assert ultimo_bloque_aprendido(ruta) is None


def test_el_corte_es_el_ultimo_bloque_con_firma(db):
    ruta, conn = db
    conn.executemany(
        "INSERT INTO tbl_firma_eventos VALUES (1,'x',?,1)",
        [("2026-09-01 10:00",), ("2026-09-03 21:00",), ("2026-08-15 03:00",)])
    conn.commit()
    assert ultimo_bloque_aprendido(ruta) == "2026-09-03 21:00"


def test_sin_la_tabla_no_revienta(tmp_path):
    ruta = tmp_path / "vacia.db"
    sqlite3.connect(ruta).close()
    assert ultimo_bloque_aprendido(str(ruta)) is None


def test_desde_deja_fuera_lo_ya_aprendido(db, monkeypatch):
    ruta, conn = db
    mag = MIN_MAGNITUD_OBSERVAR + 1.0
    conn.executemany(
        "INSERT INTO tbl_historico_sismico_raw VALUES (?,1,1,?)",
        [("2026-09-01 10:00", mag), ("2026-09-03 21:00", mag),
         ("2026-09-10 05:00", mag), ("2026-09-20 08:00", mag)])
    conn.commit()

    vistos = []
    import sentinel_omega.infrastructure.pipeline.entrenamiento as ent
    monkeypatch.setattr(ent, "extraer_features_ventana",
                        lambda c, ts, nodo: vistos.append(ts) or None)

    entrenar_reconocimiento(ruta, desde="2026-09-03 21:00")
    assert vistos == ["2026-09-10 05:00", "2026-09-20 08:00"]


def test_sin_desde_se_recorre_todo(db, monkeypatch):
    ruta, conn = db
    mag = MIN_MAGNITUD_OBSERVAR + 1.0
    conn.executemany("INSERT INTO tbl_historico_sismico_raw VALUES (?,1,1,?)",
                     [("2026-09-01 10:00", mag), ("2026-09-20 08:00", mag)])
    conn.commit()
    vistos = []
    import sentinel_omega.infrastructure.pipeline.entrenamiento as ent
    monkeypatch.setattr(ent, "extraer_features_ventana",
                        lambda c, ts, nodo: vistos.append(ts) or None)
    entrenar_reconocimiento(ruta)
    assert len(vistos) == 2


def test_el_incremental_toma_el_corte_solo(db, monkeypatch):
    ruta, conn = db
    mag = MIN_MAGNITUD_OBSERVAR + 1.0
    conn.executemany("INSERT INTO tbl_historico_sismico_raw VALUES (?,1,1,?)",
                     [("2026-09-01 10:00", mag), ("2026-09-20 08:00", mag)])
    conn.execute("INSERT INTO tbl_firma_eventos VALUES (1,'x','2026-09-01 10:00',1)")
    conn.commit()
    vistos = []
    import sentinel_omega.infrastructure.pipeline.entrenamiento as ent
    monkeypatch.setattr(ent, "extraer_features_ventana",
                        lambda c, ts, nodo: vistos.append(ts) or None)
    st = entrenar_incremental(ruta)
    assert vistos == ["2026-09-20 08:00"]
    assert st["desde"] == "2026-09-01 10:00"


def test_el_barrido_diario_aprende_lo_que_promueve():
    # Promover sin aprender deja los datos en la memoria sin convertirlos en
    # firmas, que es lo que el sistema usa para reconocer.
    import inspect

    from sentinel_omega.infrastructure.pipeline import mantenimiento
    fuente = inspect.getsource(mantenimiento.barrido_diario)
    assert "promover_eventos_vivos(" in fuente
    assert "entrenar_incremental(" in fuente
    assert fuente.index("promover_eventos_vivos(") < fuente.index("entrenar_incremental(")
