"""
Sección de aciertos: debe consultar el esquema REAL de TBL_JUEZ_AUDITORIA.

Regresión que cubren estos tests: el módulo estaba escrito contra columnas
inexistentes (`veredicto`, `timestamp_evento`, `event_class`, `magnitude`,
`location`). Las tres funciones lanzaban OperationalError y los tres reportes
que las consumen se tragaban el error en silencio — la sección nunca salía.
"""

import importlib.util
import time
from pathlib import Path

import pytest

from sentinel_omega.infrastructure.database.schema import get_connection

ROOT = Path(__file__).resolve().parents[2]


def _load_aciertos():
    spec = importlib.util.spec_from_file_location(
        "aciertos_reporte", ROOT / "deploy" / "aciertos_reporte.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _insert(conn, **kw):
    """Inserta una fila de auditoría con los campos que el Juez escribe."""
    fila = {
        "timestamp": time.time(),
        "bot_name": "padre",
        "prediccion": "alert",
        "confianza": 0.8,
        "ventana_h": 72,
        "verdad": "",
        "resultado": "PENDIENTE",
        "severidad": 0.0,
        "reincidencia": 0,
        "detalles_json": "{}",
        "resuelto_at": None,
        "fase": "viva",
    }
    fila.update(kw)
    conn.execute(
        "INSERT INTO TBL_JUEZ_AUDITORIA "
        "(timestamp, bot_name, prediccion, confianza, ventana_h, verdad, "
        " resultado, severidad, reincidencia, detalles_json, resuelto_at, fase) "
        "VALUES (:timestamp,:bot_name,:prediccion,:confianza,:ventana_h,:verdad,"
        " :resultado,:severidad,:reincidencia,:detalles_json,:resuelto_at,:fase)",
        fila,
    )


@pytest.fixture
def db_con_veredictos(tmp_path):
    """DB real con un veredicto de cada clase."""
    db = str(tmp_path / "aciertos.db")
    conn = get_connection(db)
    _insert(
        conn, bot_name="padre", resultado="ACIERTO", confianza=0.91, ventana_h=72,
        verdad="3 eventos en ventana de 72h (máx M5.2, nodos de la predicción)",
        resuelto_at="2026-09-10 12:00:00",
    )
    _insert(conn, bot_name="alfa1", resultado="FALLO", confianza=0.4, ventana_h=48,
            verdad="1 eventos en ventana de 48h (máx M4.8, zonas monitoreadas)")
    _insert(conn, bot_name="beta1", resultado="FALSO_POSITIVO", confianza=0.6, ventana_h=24)
    _insert(conn, bot_name="delta", resultado="PENDIENTE", confianza=0.3, ventana_h=2)
    conn.commit()
    conn.close()
    return db


# ── Las consultas corren contra el esquema real ──────────────────────────

def test_las_tres_funciones_corren_contra_el_esquema_real(db_con_veredictos):
    """Guardia de regresión: ninguna debe lanzar OperationalError."""
    ar = _load_aciertos()
    ar.obtener_estadisticas_aciertos(db_con_veredictos)
    ar.obtener_aciertos_recientes(db_con_veredictos)
    ar.seccion_aciertos_markdown(db_con_veredictos)


def test_estadisticas_cuentan_cada_veredicto(db_con_veredictos):
    ar = _load_aciertos()
    stats = ar.obtener_estadisticas_aciertos(db_con_veredictos)
    assert stats["aciertos_totales"] == 1
    assert stats["fallos_totales"] == 1
    assert stats["falsos_positivos_totales"] == 1
    assert stats["pendientes_totales"] == 1


def test_la_tasa_excluye_pendientes(db_con_veredictos):
    """Una predicción con la ventana aún abierta no puede contar como fallo."""
    ar = _load_aciertos()
    stats = ar.obtener_estadisticas_aciertos(db_con_veredictos)
    # 3 resueltas (ACIERTO+FALLO+FALSO_POSITIVO), la PENDIENTE fuera.
    assert stats["total_predicciones"] == 3
    assert stats["total_filas"] == 4
    assert stats["tasa_acierto_global"] == pytest.approx(1 / 3)


def test_por_bot_excluye_pendientes(db_con_veredictos):
    ar = _load_aciertos()
    por_bot = ar.obtener_estadisticas_aciertos(db_con_veredictos)["por_bot"]
    assert "delta" not in por_bot, "el bot solo con PENDIENTE no debe puntuar"
    assert por_bot["padre"]["aciertos"] == 1
    assert por_bot["padre"]["tasa_acierto"] == pytest.approx(1.0)
    assert por_bot["padre"]["ventana_h_promedio"] == pytest.approx(72.0)


# ── Lectura de los aciertos ──────────────────────────────────────────────

def test_acierto_extrae_magnitud_y_ambito_de_la_verdad(db_con_veredictos):
    ar = _load_aciertos()
    aciertos = ar.obtener_aciertos_recientes(db_con_veredictos)
    assert len(aciertos) == 1
    a = aciertos[0]
    assert a["bot"] == "padre"
    assert a["magnitude"] == pytest.approx(5.2)
    assert a["ambito"] == "nodos de la predicción"
    assert a["ventana_h"] == 72
    assert a["resuelto_at"] == "2026-09-10 12:00:00"


def test_sin_magnitud_en_la_verdad_queda_none(tmp_path):
    """Cero datos sintéticos: si el texto no trae magnitud, no se inventa."""
    ar = _load_aciertos()
    db = str(tmp_path / "sin_mag.db")
    conn = get_connection(db)
    _insert(conn, resultado="ACIERTO", verdad="sin eventos en ventana de 72h (global)")
    conn.commit()
    conn.close()
    a = ar.obtener_aciertos_recientes(db)[0]
    assert a["magnitude"] is None
    assert a["ambito"] == "global"


# ── La sección se renderiza de verdad ────────────────────────────────────

def test_la_seccion_muestra_el_acierto(db_con_veredictos):
    ar = _load_aciertos()
    md = ar.seccion_aciertos_markdown(db_con_veredictos)
    assert "## ✅ Aciertos y Predicciones Correctas" in md
    assert "PADRE" in md
    assert "M5.2" in md
    assert "nodos de la predicción" in md


def test_la_seccion_llega_al_reporte_general(db_con_veredictos, tmp_path):
    """Punta a punta: generar_reporte.py debe INCLUIR la sección, no tragársela."""
    spec = importlib.util.spec_from_file_location(
        "generar_reporte", ROOT / "deploy" / "generar_reporte.py"
    )
    gr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gr)

    out = str(tmp_path / "REPORTE.md")
    gr.generar(db_con_veredictos, out)
    texto = Path(out).read_text()
    assert "## ✅ Aciertos y Predicciones Correctas" in texto
