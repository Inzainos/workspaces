"""El muro de 5 se entrena aparte para cada magnitud, senal por senal.

Una senal entra a una magnitud solo si la separa de las otras.
Encendida para todas, no cuenta para esa clase y no se borra.
Un 4.5 no le ensena al muro de un 6. El 2.5 no es blanco.
El conteo de cada clase lo dice este entrenamiento; no se copia el 3.
"""
from sentinel_omega.core.precursor.muro_cinco_eventos import (
    CLASES_BLANCO_MURO,
    WALL_ATMOSFERICO,
    WALL_GEOFISICO,
    WALL_MEMBERS,
    WALL_OCEANICO,
    WALL_SOLAR,
    MuroCincoEventos,
    clase_blanco_muro,
    entrenar_umbral_por_magnitud,
    filas_muros_antes_del_sismo,
)
from sentinel_omega.infrastructure.pipeline.entrenamiento import _event_class


def test_por_debajo_de_la_prediccion_no_hay_blanco():
    assert clase_blanco_muro(2.5) is None
    assert clase_blanco_muro(4.49) is None
    assert clase_blanco_muro(4.5) == "SISMO_M4"
    assert clase_blanco_muro(6.0) == "SISMO_M6"
    for mag in (2.5, 4.5, 5.0, 6.0, 7.0):
        blanco = clase_blanco_muro(mag)
        if blanco is None:
            assert _event_class(mag).endswith("_obs")
        else:
            assert blanco == _event_class(mag)


def test_un_4_5_no_le_ensena_al_muro_de_un_6():
    filas = [((), None)] * 100
    filas += [((WALL_OCEANICO,), 4.6)] * 40
    filas += [((WALL_ATMOSFERICO,), 6.2)] * 40
    muro = entrenar_umbral_por_magnitud(filas)
    assert muro["SISMO_M4"]["senales"] == (WALL_OCEANICO,)
    assert muro["SISMO_M6"]["senales"] == (WALL_ATMOSFERICO,)
    assert WALL_OCEANICO not in muro["SISMO_M6"]["senales"]
    assert set(muro) == set(CLASES_BLANCO_MURO)


def test_encendida_para_todas_no_cuenta_y_puede_servir_a_otra():
    filas = [((), None)] * 100
    filas += [((WALL_GEOFISICO,), 4.6)] * 30
    filas += [((WALL_GEOFISICO,), 6.1)] * 30
    filas += [((WALL_GEOFISICO, WALL_SOLAR), 5.2)] * 30
    muro = entrenar_umbral_por_magnitud(filas)
    assert muro["SISMO_M4"]["senales"] == ()
    assert muro["SISMO_M4"]["umbral"] is None
    assert muro["SISMO_M6"]["senales"] == ()
    assert muro["SISMO_M5"]["senales"] == (WALL_SOLAR,)
    assert WALL_GEOFISICO in WALL_MEMBERS
    assert WALL_SOLAR in WALL_MEMBERS
    assert len(WALL_MEMBERS) == 5


def test_geofisico_entra_si_separa_y_no_entra_si_no():
    filas = [((), None)] * 100
    filas += [((WALL_GEOFISICO,), 6.4)] * 30
    filas += [((WALL_OCEANICO,), 4.7)] * 30
    muro = entrenar_umbral_por_magnitud(filas)
    assert muro["SISMO_M6"]["senales"] == (WALL_GEOFISICO,)
    assert WALL_GEOFISICO not in muro["SISMO_M4"]["senales"]
    assert muro["SISMO_M6"]["umbral"] == 1
    assert muro["SISMO_M6"]["umbral"] != 3


def test_sin_sismos_suficientes_no_se_copia_el_3():
    filas = [((WALL_ATMOSFERICO,), 7.2)] * 5 + [((), None)] * 50
    muro = entrenar_umbral_por_magnitud(filas)
    assert muro["SISMO_M7"]["umbral"] is None
    assert muro["SISMO_M7"]["senales"] == ()


def test_el_2_5_no_abre_clase_ni_borra_senales():
    filas = [((WALL_SOLAR,), 2.5)] * 40 + [((), None)] * 40
    muro = entrenar_umbral_por_magnitud(filas)
    assert all(v["umbral"] is None for v in muro.values())
    assert "SISMO_M2_obs" not in muro
    assert len(WALL_MEMBERS) == 5
    assert MuroCincoEventos().min_walls_for_breach == 3



def test_la_fila_es_el_ciclo_anterior_al_sismo():
    ciclos = [
        (10, (WALL_OCEANICO,)),
        (20, (WALL_GEOFISICO,)),
        (30, (WALL_SOLAR,)),
    ]
    filas = filas_muros_antes_del_sismo(
        ciclos, [(20, 4.6), (25, 6.2), (18, 4.8)]
    )
    assert filas[0] == ((WALL_OCEANICO,), 4.8)
    assert filas[1] == ((WALL_GEOFISICO,), 6.2)
    assert filas[2] == ((WALL_SOLAR,), None)
    vacias = filas_muros_antes_del_sismo(ciclos, [(5, 7.1)])
    assert [mag for _, mag in vacias] == [None, None, None]


def test_guarda_null_y_no_copia_el_3(tmp_path):
    import json
    import sqlite3
    from datetime import datetime, timezone

    from sentinel_omega.infrastructure.pipeline.entrenamiento import (
        calcular_umbral_muro,
    )

    db = tmp_path / "muro.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE TBL_MURO_EVENTOS ("
        "timestamp REAL, wall_geofisico INTEGER, wall_atmosferico INTEGER, "
        "wall_oceanico INTEGER, wall_solar INTEGER, wall_financiero INTEGER)"
    )
    conn.execute(
        "CREATE TABLE tbl_eventos_sismicos_fuente "
        "(time_utc TEXT, mag REAL, event_type TEXT)"
    )
    base = 1_700_000_000

    def marca(ts, geo, atm, oce, sol, fin):
        conn.execute(
            "INSERT INTO TBL_MURO_EVENTOS VALUES (?, ?, ?, ?, ?, ?)",
            (ts, geo, atm, oce, sol, fin),
        )

    def sismo(ts, mag, event_type=None):
        texto = datetime.fromtimestamp(ts, timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "INSERT INTO tbl_eventos_sismicos_fuente VALUES (?, ?, ?)",
            (texto, mag, event_type),
        )

    for i in range(30):
        ts = base + i * 100
        marca(ts, 0, 0, 1, 0, 0)
        sismo(ts + 10, 4.6)
    for i in range(30):
        ts = base + 10000 + i * 100
        marca(ts, 0, 1, 0, 0, 0)
        sismo(ts + 10, 6.1)
    for i in range(5):
        ts = base + 20000 + i * 100
        marca(ts, 1, 0, 0, 0, 0)
        sismo(ts + 10, 7.2)
    ts = base + 30000
    marca(ts, 0, 0, 0, 1, 0)
    sismo(ts + 10, 6.4, "landslide")
    conn.commit()
    conn.close()

    umbral = calcular_umbral_muro(str(db))
    assert umbral["SISMO_M4"]["senales"] == (WALL_OCEANICO,)
    assert umbral["SISMO_M4"]["umbral"] == 1
    assert umbral["SISMO_M6"]["senales"] == (WALL_ATMOSFERICO,)
    assert umbral["SISMO_M6"]["senales"] == (WALL_ATMOSFERICO,)
    assert WALL_SOLAR not in umbral["SISMO_M6"]["senales"]
    assert umbral["SISMO_M7"]["umbral"] is None
    assert umbral["SISMO_M7"]["umbral"] != 3
    guardado = sqlite3.connect(db).execute(
        "SELECT clase, umbral, n_filas FROM tbl_muro_umbral_magnitud"
    ).fetchall()
    por_clase = {c: (u, n) for c, u, n in guardado}
    assert por_clase["SISMO_M7"] == (None, 5)
    assert por_clase["SISMO_M6"][1] == 30
    assert por_clase["SISMO_M4"][1] == 30
    assert json.loads(sqlite3.connect(db).execute(
        "SELECT senales FROM tbl_muro_umbral_magnitud WHERE clase = 'SISMO_M4'"
    ).fetchone()[0]) == [WALL_OCEANICO]


def test_cargar_umbral_vivo_fallback(tmp_path):
    from sentinel_omega.core.precursor.muro_cinco_eventos import cargar_umbral_vivo
    db = tmp_path / "t.db"
    u = cargar_umbral_vivo(str(db), clase="SISMO_M6", fallback=3)
    assert u["umbral"] == 3 and u["senales"] is None and u["fuente"] == "fallback"


def test_cargar_umbral_vivo_null_queda_fallback(tmp_path):
    import sqlite3
    from sentinel_omega.core.precursor.muro_cinco_eventos import cargar_umbral_vivo
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE tbl_muro_umbral_magnitud ("
        "clase TEXT PRIMARY KEY, umbral INTEGER, n_filas INTEGER, "
        "senales TEXT, calculado_en TEXT)"
    )
    conn.execute(
        "INSERT INTO tbl_muro_umbral_magnitud VALUES (?,?,?,?,?)",
        ("SISMO_M6", None, 13, "[]", "x"),
    )
    conn.commit()
    conn.close()
    u = cargar_umbral_vivo(str(db), clase="SISMO_M6", fallback=3)
    assert u["umbral"] == 3 and u["fuente"] == "fallback"


def test_cargar_umbral_vivo_mode_ro_no_crea_archivo(tmp_path):
    from sentinel_omega.core.precursor.muro_cinco_eventos import cargar_umbral_vivo
    db = tmp_path / "no_existe.db"
    u = cargar_umbral_vivo(str(db), clase="SISMO_M6", fallback=3)
    assert u["fuente"] == "fallback"
    assert not db.exists()


def test_evaluate_releee_tabla_cada_vez(tmp_path):
    import json
    import sqlite3
    from sentinel_omega.core.precursor.muro_cinco_eventos import (
        MuroCincoEventos,
        WALL_GEOFISICO,
        WALL_SOLAR,
    )
    from sentinel_omega.core.precursor.precursor_types import PrecursorType
    from sentinel_omega.core.precursor.scanner import PrecursorDetection

    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE tbl_muro_umbral_magnitud ("
        "clase TEXT PRIMARY KEY, umbral INTEGER, n_filas INTEGER, "
        "senales TEXT, calculado_en TEXT)"
    )
    conn.execute(
        "INSERT INTO tbl_muro_umbral_magnitud VALUES (?,?,?,?,?)",
        (
            "SISMO_M6",
            2,
            50,
            json.dumps([WALL_GEOFISICO, WALL_SOLAR]),
            "x",
        ),
    )
    conn.commit()
    conn.close()

    muro = MuroCincoEventos(min_walls_for_breach=3, db_path=str(db))
    dets = [
        PrecursorDetection(
            tipo=PrecursorType.SEISMIC_CLUSTER,
            display_name="x",
            station="x",
            lat=None,
            lon=None,
            confidence=0.9,
        ),
        PrecursorDetection(
            tipo=PrecursorType.SCHUMANN,
            display_name="x",
            station="x",
            lat=None,
            lon=None,
            confidence=0.8,
        ),
    ]
    r1 = muro.evaluate(dets)
    assert r1.muro_breach is True
    assert muro.last_umbral_fuente == "tabla"

    # Cambia la tabla sin reinstanciar: el siguiente ciclo debe leer el nuevo valor
    conn = sqlite3.connect(str(db))
    conn.execute(
        "UPDATE tbl_muro_umbral_magnitud SET umbral = NULL, senales = '[]' "
        "WHERE clase = 'SISMO_M6'"
    )
    conn.commit()
    conn.close()
    r2 = muro.evaluate(dets)
    # Con fallback 3 y sin senales, 2 muros no alcanzan
    assert r2.muro_breach is False
    assert muro.last_umbral_fuente == "fallback"


def test_evaluate_con_senales_breach():
    from sentinel_omega.core.precursor.muro_cinco_eventos import (
        MuroCincoEventos,
        WALL_GEOFISICO,
        WALL_SOLAR,
        cargar_umbral_vivo,
    )
    from sentinel_omega.core.precursor.precursor_types import PrecursorType
    from sentinel_omega.core.precursor.scanner import PrecursorDetection
    # Sin db_path: usa min_walls; forzamos senales vía evaluate path sin tabla
    # (db_path None => umbral=min_walls, senales=None). Aqui solo probamos
    # el conteo por senales inyectando db con fila.
    import json
    import sqlite3
    from pathlib import Path
    import tempfile
    td = Path(tempfile.mkdtemp())
    db = td / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE tbl_muro_umbral_magnitud ("
        "clase TEXT PRIMARY KEY, umbral INTEGER, n_filas INTEGER, "
        "senales TEXT, calculado_en TEXT)"
    )
    conn.execute(
        "INSERT INTO tbl_muro_umbral_magnitud VALUES (?,?,?,?,?)",
        ("SISMO_M6", 2, 10, json.dumps([WALL_GEOFISICO, WALL_SOLAR]), "x"),
    )
    conn.commit()
    conn.close()
    muro = MuroCincoEventos(min_walls_for_breach=3, db_path=str(db))
    dets = [
        PrecursorDetection(
            tipo=PrecursorType.SEISMIC_CLUSTER,
            display_name="x",
            station="x",
            lat=None,
            lon=None,
            confidence=0.9,
        ),
        PrecursorDetection(
            tipo=PrecursorType.SCHUMANN,
            display_name="x",
            station="x",
            lat=None,
            lon=None,
            confidence=0.8,
        ),
    ]
    r = muro.evaluate(dets)
    assert r.muro_breach is True
