"""Un lote nocturno que comparte la base con el launcher no sobrevive con 5 s.

`sentinel-omega-mantenimiento.service` falló el 2026-09-27 a las 00:00:36 con el
launcher vivo. Las MISMAS funciones --- `disciplina_trasfondo` y `barrido_diario`
--- corren sin un error contra una copia sin contención, así que el código está
bien y el fallo fue del entorno.

Que fuera el candado es lo más probable pero NO está probado: el journal de
systemd no es legible por el usuario del repo. Se arregla igual, porque 5 s (el
defecto de SQLite) de presupuesto para un lote que compite con un escritor que
cicla cada 5 minutos es insuficiente en cualquier caso. Un lote puede esperar;
fallar no le sirve a nadie.
"""
import re
import sqlite3
import threading
import time

import pytest

from sentinel_omega.infrastructure.pipeline import entrenamiento, mantenimiento

MODULOS = (mantenimiento, entrenamiento)


@pytest.mark.parametrize("mod", MODULOS, ids=lambda m: m.__name__.split(".")[-1])
def test_ninguna_conexion_de_lote_usa_el_defecto_de_5s(mod):
    import inspect
    fuente = inspect.getsource(mod)
    desnudas = re.findall(r"sqlite3\.connect\(db_path\)(?!\s*,)", fuente)
    assert not desnudas, (
        f"{len(desnudas)} conexiones sin timeout: con el launcher vivo fallan "
        "por candado a los 5 s")


@pytest.mark.parametrize("mod", MODULOS, ids=lambda m: m.__name__.split(".")[-1])
def test_la_espera_es_mayor_que_un_ciclo_del_launcher(mod):
    """El ciclo son ~300 s de periodo pero su escritura es corta; la espera tiene
    que cubrir varias escrituras encadenadas, no un ciclo entero."""
    assert mod.ESPERA_CANDADO_S >= 60, (
        f"{mod.ESPERA_CANDADO_S} s no cubre una racha de escrituras del ciclo")


def test_con_5s_el_lote_habria_fallado(tmp_path):
    """La demostración: un escritor que retiene el candado 8 s hace fallar una
    conexión con el defecto de 5 s y NO una con la espera del lote."""
    db = tmp_path / "candado.db"
    sqlite3.connect(db).executescript(
        "CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (1);")

    listo = threading.Event()
    suelta = threading.Event()

    def retener():
        c = sqlite3.connect(db, isolation_level=None)
        c.execute("BEGIN EXCLUSIVE")
        listo.set()
        suelta.wait(20)
        c.execute("COMMIT")
        c.close()

    hilo = threading.Thread(target=retener, daemon=True)
    hilo.start()
    assert listo.wait(5), "el escritor de prueba no tomó el candado"

    try:
        # Con el defecto de 5 s: falla.
        corto = sqlite3.connect(db, timeout=1)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            corto.execute("INSERT INTO t VALUES (2)")
        corto.close()

        # Con la espera del lote: aguanta a que el otro suelte.
        largo = sqlite3.connect(db, timeout=15)
        t0 = time.time()
        suelta.set()
        largo.execute("INSERT INTO t VALUES (3)")
        largo.commit()
        assert time.time() - t0 < 15
        assert largo.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 2
        largo.close()
    finally:
        suelta.set()
        hilo.join(timeout=5)


def test_el_dry_run_pasa_a_los_lotes():
    """`--dry-run` propaga a los lotes (desde el 2026-09-30): silencia
    Telegram Y bloquea las escrituras de `--disciplina`/`--barrido`.

    Historia: hasta esa fecha el flag SOLO quitaba las variables de Telegram
    (launcher.py), y el drop-in «Harden 2026-09-13: default dry-run» hacía
    creer que la nocturna no escribía --- escribía igual: firmas menores,
    pesos, volcados. La nocturna quedó EN VIVO por decisión del operador
    (sin --dry-run en el ExecStart); el flag existe para corridas manuales
    que deban simular.
    """
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher)
    i = fuente.index("if args.dry_run:")
    bloque = fuente[i: i + 260]
    assert "TELEGRAM" in bloque, "cambió lo que hace --dry-run; revisar el drop-in"
    assert (
        "disciplina_trasfondo(str(db_path), dry_run=args.dry_run)" in fuente
    ), "--dry-run ya no llega a la disciplina: volvería a escribir en seco"
    assert (
        "barrido_diario(str(db_path), dry_run=args.dry_run)" in fuente
    ), "--dry-run ya no llega al barrido: volvería a escribir en seco"


def _db_barrido(tmp_path):
    db = tmp_path / "barrido.db"
    c = sqlite3.connect(db)
    c.executescript(
        """
        CREATE TABLE tbl_resumen_diario (
          dia TEXT PRIMARY KEY, n_ciclos INTEGER, fantasma_max REAL,
          fantasma_media REAL, nivel_max TEXT, breaches INTEGER,
          alertas INTEGER, senal_dominante TEXT,
          creada_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE TBL_CICLOS (
          timestamp REAL, fantasma REAL, nivel_riesgo TEXT,
          muro_breach INTEGER, geo_signal TEXT);
        CREATE TABLE TBL_PRECURSORES_COSMICOS (timestamp REAL, fantasma REAL);
        CREATE TABLE TBL_DETECCIONES (
          id INTEGER PRIMARY KEY, timestamp REAL, tipo TEXT,
          wall_name TEXT, confidence REAL);
        INSERT INTO TBL_CICLOS VALUES (1000000000, 5.0, 'LOW', 0, 'calma');
        INSERT INTO TBL_CICLOS VALUES (1000000001, 50.0, 'HIGH', 1, 'alert');
        INSERT INTO TBL_PRECURSORES_COSMICOS VALUES (1000000000, 3.0);
        INSERT INTO TBL_DETECCIONES VALUES (1, 1000000002, 'schumann', 'muro_a', 0.4);
        INSERT INTO TBL_DETECCIONES VALUES (2, 1000000002, 'schumann', 'muro_a', 0.9);
        """
    )
    c.commit()
    c.close()
    return db


def test_barrido_en_seco_no_escribe_nada(tmp_path):
    """El dry-run del barrido reporta lo que HARÍA y no toca la base."""
    from sentinel_omega.infrastructure.pipeline import mantenimiento

    db = _db_barrido(tmp_path)
    res = mantenimiento.barrido_diario(str(db), dry_run=True)

    c = sqlite3.connect(db)
    ciclos = c.execute("SELECT COUNT(*) FROM TBL_CICLOS").fetchone()[0]
    prec = c.execute("SELECT COUNT(*) FROM TBL_PRECURSORES_COSMICOS").fetchone()[0]
    dets = c.execute("SELECT COUNT(*) FROM TBL_DETECCIONES").fetchone()[0]
    resumenes = c.execute("SELECT COUNT(*) FROM tbl_resumen_diario").fetchone()[0]
    derivadas = c.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name IN ("
        "'tbl_correlaciones_padre','tbl_correlaciones_omega',"
        "'tbl_sesgo_aprendizaje','tbl_orden_precursores',"
        "'tbl_secuencia_nodos','tbl_volcado_vivo_log')"
    ).fetchone()[0]
    c.close()

    assert ciclos == 2 and prec == 1 and dets == 2 and resumenes == 0
    assert derivadas == 0, "el barrido en seco creó tablas derivadas"
    assert res["dry_run"] is True
    # Reporta lo que HARÍA, con el mismo WHERE del DELETE:
    assert res["dias_resumidos"] == 1
    assert res["ciclos_botados"] == 1        # el LOW sin breach
    assert res["precusores_botados"] == 1     # fantasma 3.0 < 15
    assert res["detecciones_colapsadas"] == 1  # la de confianza 0.4 pierde
    # Nada omitido en silencio: lo que no corrió está declarado
    assert "correlaciones_padre" in res["saltados"]
    assert "aprendizaje_incremental" in res["saltados"]
    assert res["volcado_vivo"]["dry_run"] == 1


def test_disciplina_en_seco_no_escribe_ni_castiga(tmp_path, monkeypatch):
    """El dry-run de la disciplina evalúa, reporta castigos/refuerzos que
    APLICARÍA, y no escribe: ni tabla temporal, ni Juez, ni pesos."""
    from sentinel_omega.infrastructure.pipeline import entrenamiento as ent

    base_feats = {
        "bz_min": -5.0, "kp_max": 4.0, "kp_mean": 3.0,
        "schumann_mean": 7.8, "fase_lunar": 0.5, "viento_avg": 400.0,
    }
    eventos = [(1789000000, 19.4, -99.1, 3.8), (1789003600, 19.5, -99.0, 4.1)]

    class _JuezStub:
        instancias = []

        def __init__(self, conn):
            self.llamadas = []
            _JuezStub.instancias.append(self)

        def registrar_prediccion(self, **kw):
            self.llamadas.append(("prediccion", kw))

        def evaluar_pendientes(self, **kw):
            self.llamadas.append(("evaluar", kw))

    class _MemStub:
        def __init__(self, conn):
            pass

        def consolidadas(self, bot):
            keys = ent.BOT_FEATURES[bot]
            if keys is None:
                return [{"id_nodo": 1, "features": dict(base_feats)}]
            sub = {k: base_feats[k] for k in keys if k in base_feats}
            if len(sub) < 4:  # MIN_DIMENSIONES_COMPARABLES: firma no comparable
                return []
            return [{"id_nodo": 1, "features": sub}]

    castigos, refuerzos = [], []
    _JuezStub.instancias = []
    monkeypatch.setattr(ent, "Juez", _JuezStub)
    monkeypatch.setattr(ent, "FirmaMemoria", _MemStub)
    monkeypatch.setattr(ent, "_fetch_sismos_menores", lambda *a, **k: eventos)
    monkeypatch.setattr(
        ent, "extraer_features_ventana",
        # Evento 1 idéntico a las firmas (acierto); evento 2 desviado (fallo)
        lambda conn, ts, nodo: dict(base_feats) if ts == eventos[0][0]
        else {k: v * 10 for k, v in base_feats.items()},
    )
    monkeypatch.setattr(
        "sentinel_omega.core.shared.geometria_uvg.nodo_mas_cercano",
        lambda lat, lon: {"id": 1},
    )
    monkeypatch.setattr(
        "sentinel_omega.core.juez.pesos.castigar",
        lambda conn, bot, es_padre=False, gravedad=1.0: castigos.append(bot),
    )
    monkeypatch.setattr(
        "sentinel_omega.core.juez.pesos.reforzar",
        lambda conn, bot: refuerzos.append(bot),
    )

    def _db():
        db = tmp_path / f"disciplina_{len(list(tmp_path.iterdir()))}.db"
        c = sqlite3.connect(db)
        c.executescript(
            "CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT);"
            "INSERT INTO tbl_clima_espacial_raw VALUES ('2026-08-01 00:00');"
        )
        c.commit()
        c.close()
        return db

    # ── En seco: no escribe nada ──
    db = _db()
    antes = sqlite3.connect(db).execute(
        "SELECT type, name FROM sqlite_master ORDER BY name").fetchall()
    res = ent.disciplina_trasfondo(str(db), dry_run=True)
    c = sqlite3.connect(db)
    despues = c.execute(
        "SELECT type, name FROM sqlite_master ORDER BY name").fetchall()
    c.close()

    assert res["dry_run"] is True
    assert antes == despues, "la disciplina en seco creó/borró objetos"
    assert castigos == [] and refuerzos == []
    assert all(j.llamadas == [] for j in _JuezStub.instancias), \
        "la disciplina en seco registró veredictos ante el Juez"
    # La evaluación SÍ corrió (si no, lo de arriba pasaría por vacío):
    assert res["ajustes"], "no evaluó ningún bot"
    algun_castigo = any(a["castigos"] > 0 for a in res["ajustes"].values())
    assert algun_castigo, "el arnés no produce fallos: el gate de castigo no se prueba"

    # ── En vivo (control): el MISMO arnés sí escribe y castiga ──
    db2 = _db()
    res2 = ent.disciplina_trasfondo(str(db2), dry_run=False)
    c = sqlite3.connect(db2)
    firmas_menores = c.execute(
        "SELECT COUNT(*) FROM tbl_firmas_menores").fetchone()[0]
    c.close()
    assert firmas_menores > 0, "el control en vivo no escribió firmas menores"
    assert castigos, "el control en vivo no aplicó castigos"
    assert refuerzos
    assert any(j.llamadas for j in _JuezStub.instancias), \
        "el control en vivo no registró veredictos"
    assert res2["dry_run"] is False


def test_importar_el_launcher_no_revienta_si_el_log_no_es_escribible():
    """Un módulo no debe abrir archivos por el hecho de importarse.

    `logging.basicConfig` con un `RotatingFileHandler` corre al importar, así que
    un log no escribible hacía estallar `import launcher` con PermissionError ---
    y con él cualquier prueba o herramienta que lo importe.

    Medido el 2026-09-27: el servicio corre como root (`User=` vacío en unidad de
    sistema) y al ROTAR el log creó el archivo nuevo como root. Desde ese instante
    tres pruebas que habían pasado una hora antes fallaron sin que el código
    cambiara. Se repite en cada rotación mientras el servicio sea root.
    """
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher)
    i = fuente.index("RotatingFileHandler(\n")
    antes = fuente[max(0, i - 400): i]
    assert "try:" in antes, (
        "el handler de archivo volvió a construirse sin protección: un log no "
        "escribible impide importar el módulo")
    despues = fuente[i: i + 700]
    assert "except OSError" in despues, "no captura permisos/disco lleno"
    assert "StreamHandler" in fuente[max(0, i - 600): i], (
        "se perdió el handler de stdout, que es lo que captura el journal")
