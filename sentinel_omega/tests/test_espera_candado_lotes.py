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


def test_el_dry_run_del_drop_in_no_protege_nada():
    """`--dry-run` SOLO quita las variables de Telegram (launcher.py:205-208), y
    su propia ayuda lo dice. El drop-in de la unidad de mantenimiento dice
    «Harden 2026-09-13: default dry-run», lo que se lee como «no cambia nada»;
    pero `--disciplina --barrido` escriben en la base --- aplican castigos y
    refuerzos a los pesos --- con o sin el flag.

    Esta prueba fija el hecho para que nadie vuelva a leer seguridad donde no la
    hay. Si algún día `--dry-run` SÍ propaga a los lotes, se cambia aquí con la
    medición que lo respalde.
    """
    import inspect

    from sentinel_omega import launcher

    fuente = inspect.getsource(launcher.main) if hasattr(launcher, "main") \
        else inspect.getsource(launcher)
    i = fuente.index("if args.dry_run:")
    bloque = fuente[i: i + 260]
    assert "TELEGRAM" in bloque, "cambió lo que hace --dry-run; revisar el drop-in"
    # No pasa dry_run a los lotes: si algún día lo hace, esta aserción cae y hay
    # que actualizar el comentario de la unidad de systemd.
    assert "disciplina_trasfondo(str(db_path))" in fuente
    assert "barrido_diario(str(db_path))" in fuente


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
