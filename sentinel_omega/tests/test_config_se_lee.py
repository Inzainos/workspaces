"""El fichero de configuración tiene que leerse de verdad.

Origen (2026-09-25): se encendió `juez.peso_por_merito: true` en sentinel.yaml,
se reinició el servicio, y el arranque siguió diciendo «paseo multiplicativo».
El lanzador construía `SentinelOmegaConfig()` --- los valores por defecto del
código --- y NUNCA llamaba a `load_config()`, que es quien lee el yaml. El
fichero de configuración llevaba quién sabe cuánto siendo decorativo.
"""
import inspect

from sentinel_omega.config.sentinel_config import SentinelOmegaConfig, load_config


def test_load_config_lee_el_yaml(tmp_path):
    yaml = tmp_path / "prueba.yaml"
    yaml.write_text("juez:\n  peso_por_merito: true\n  minimo_ventanas: 7\n")
    cfg = load_config(str(yaml))
    assert cfg.juez.peso_por_merito is True
    assert cfg.juez.minimo_ventanas == 7


def test_los_defaults_no_traen_el_yaml():
    # La diferencia que hace que importe cuál se use.
    assert SentinelOmegaConfig().juez.peso_por_merito is False


def test_un_yaml_sin_la_seccion_no_revienta(tmp_path):
    yaml = tmp_path / "sin_juez.yaml"
    yaml.write_text("database:\n  geodynamic_db: 'data/X.db'\n")
    cfg = load_config(str(yaml))
    assert cfg.juez.peso_por_merito is False
    assert cfg.databases.geodynamic_db == "data/X.db"


def test_una_clave_desconocida_se_ignora(tmp_path):
    yaml = tmp_path / "raro.yaml"
    yaml.write_text("juez:\n  peso_por_merito: true\n  inventada: 9\n")
    cfg = load_config(str(yaml))
    assert cfg.juez.peso_por_merito is True
    assert not hasattr(cfg.juez, "inventada")


def test_el_lanzador_del_servicio_usa_load_config():
    # La regresión exacta: construir la config con los defaults y creer que se
    # leyó el fichero.
    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher)
    assert "config = load_config()" in fuente
    assert "config = SentinelOmegaConfig()" not in fuente


def test_el_lanzador_hermano_tambien():
    from sentinel_omega import launcher_fixed
    fuente = inspect.getsource(launcher_fixed)
    assert "config = load_config()" in fuente
    assert "config = SentinelOmegaConfig()" not in fuente


def test_el_peso_por_merito_llega_hasta_cargar_pesos():
    """De la config al peso, sin saltarse un paso."""
    import sqlite3

    from sentinel_omega.core.juez.pesos import cargar_pesos

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE TBL_PESOS_BOTS (bot_name TEXT PRIMARY KEY, "
                 "peso REAL, aciertos INTEGER, fallos INTEGER, updated_at TEXT)")
    conn.execute("INSERT INTO TBL_PESOS_BOTS VALUES ('b', 1.0, 0, 0, '')")
    conn.execute("CREATE TABLE TBL_JUEZ_AUDITORIA (bot_name TEXT, verdad TEXT, "
                 "resultado TEXT, fase TEXT)")
    # 90 calmas acertadas y 10 eventos perdidos: un bot mudo, mérito 1.0…
    conn.executemany("INSERT INTO TBL_JUEZ_AUDITORIA VALUES ('b',?,?,'viva')",
                     [("sin eventos en ventana", "ACIERTO")] * 90
                     + [("M5.0", "FALLO")] * 10)
    # …y otro que grita: su mérito tiene que BAJAR del 1.0 almacenado.
    conn.execute("INSERT INTO TBL_PESOS_BOTS VALUES ('g', 1.0, 0, 0, '')")
    conn.executemany("INSERT INTO TBL_JUEZ_AUDITORIA VALUES ('g',?,?,'viva')",
                     [("sin eventos en ventana", "FALSO_POSITIVO")] * 60
                     + [("M5.0", "FALLO")] * 10
                     + [("sin eventos en ventana", "ACIERTO")] * 30)
    conn.commit()
    assert cargar_pesos(conn)["g"] == 1.0                       # el almacenado
    assert cargar_pesos(conn, por_merito=True)["g"] < 1.0       # el medido
