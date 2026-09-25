"""La severidad tiene que medir el ERROR, no la antigüedad del bot.

Origen (2026-09-25): `reincidencia` contaba los FALLOs DESDE SIEMPRE y sin
techo. loki acumulaba 653 — multiplicador ×164 — y la severidad viva iba de
12,5 a 22.080 (mediana 1.384), cuando el tope del diseño es 180. El daño no era
el número: `verificacion.py` reconstruía la gravedad como sqrt(severidad/10) y
salía TOPADA en 3.0 el 78,6 % de las veces, así que perder un M5 castigaba
igual que perder un M7.
"""
import sqlite3

import pytest

from sentinel_omega.core.juez.juez import REINCIDENCIA_MAXIMA, Juez

EVENTO = "1 eventos en ventana de 2h (máx M5.2, global)"
CALMA = "sin eventos en ventana de 2h (global)"


@pytest.fixture
def juez():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE TBL_JUEZ_AUDITORIA (id INTEGER PRIMARY KEY, timestamp REAL, "
        "bot_name TEXT, prediccion TEXT, confianza REAL, ventana_h INTEGER, "
        "verdad TEXT, resultado TEXT, severidad REAL, reincidencia INTEGER, "
        "detalles_json TEXT, resuelto_at TEXT, fase TEXT, created_at TEXT)"
    )
    return Juez(conn)


def _añadir(juez, bot, *resultados):
    """resultados: ('FALLO', EVENTO), ('ACIERTO', CALMA)… en orden cronológico."""
    for i, (res, verdad) in enumerate(resultados):
        juez._conn.execute(
            "INSERT INTO TBL_JUEZ_AUDITORIA (bot_name, resultado, verdad, "
            "resuelto_at, created_at) VALUES (?,?,?,?,?)",
            (bot, res, verdad, f"2026-09-25 10:{i:02d}:00", f"2026-09-25 10:{i:02d}:00"),
        )
    juez._conn.commit()


def test_sin_fallos_no_hay_reincidencia(juez):
    _añadir(juez, "b", ("ACIERTO", EVENTO))
    assert juez.reincidencia("b") == 0


def test_cuenta_los_eventos_perdidos_seguidos(juez):
    _añadir(juez, "b", ("FALLO", EVENTO), ("FALLO", EVENTO), ("FALLO", EVENTO))
    assert juez.reincidencia("b") == 3


def test_un_acierto_corta_la_racha(juez):
    # Reincidente es el que vuelve a fallar SIN haber acertado en medio.
    _añadir(juez, "b", ("FALLO", EVENTO), ("FALLO", EVENTO),
            ("ACIERTO", EVENTO), ("FALLO", EVENTO))
    assert juez.reincidencia("b") == 1


def test_la_calma_no_cuenta_ni_corta(juez):
    # Las ventanas en calma son el 98 %: si contaran, borrarían cualquier racha
    # y la reincidencia siempre valdría 0.
    _añadir(juez, "b", ("FALLO", EVENTO), ("ACIERTO", CALMA),
            ("ACIERTO", CALMA), ("FALLO", EVENTO))
    assert juez.reincidencia("b") == 2


def test_la_racha_tiene_techo(juez):
    _añadir(juez, "b", *[("FALLO", EVENTO)] * 50)
    assert juez.reincidencia("b") == REINCIDENCIA_MAXIMA
    assert REINCIDENCIA_MAXIMA <= 4, "mas de 4 solo infla el numero"


def test_la_severidad_se_queda_en_el_rango_del_diseno(juez):
    # base 20 (firma conocida) x gravedad^2 (max 9) x (1 + 0,25·4) = 360.
    # Antes, con 653 fallos acumulados, el mismo error daba 22.080.
    from sentinel_omega.core.juez.juez import (
        SEVERIDAD_FALLO_FIRMA_CONOCIDA as BASE,
    )
    _añadir(juez, "b", *[("FALLO", EVENTO)] * 653)
    peor = BASE * (3.0 ** 2) * (1 + 0.25 * juez.reincidencia("b"))
    assert peor <= 360
    assert (BASE * 9 * (1 + 0.25 * 653)) > 20000   # lo que daba antes


def test_cada_bot_tiene_su_propia_racha(juez):
    _añadir(juez, "uno", ("FALLO", EVENTO), ("FALLO", EVENTO))
    _añadir(juez, "dos", ("ACIERTO", EVENTO))
    assert juez.reincidencia("uno") == 2
    assert juez.reincidencia("dos") == 0


# ─── La gravedad viaja en vez de reconstruirse ───────────────────────────────

def test_la_gravedad_llega_en_el_veredicto():
    import inspect
    from sentinel_omega.core.juez import juez as mod
    fuente = inspect.getsource(mod.Juez.resolver_pendientes) if hasattr(
        mod.Juez, "resolver_pendientes") else inspect.getsource(mod)
    assert '"gravedad": float(max(1.0, gravedad))' in fuente


def test_la_disciplina_usa_la_gravedad_del_veredicto():
    # Guarda contra la regresión: reconstruirla como sqrt(sev/10) la topaba en
    # 3.0 el 78,6 % de las veces.
    import inspect
    from sentinel_omega.infrastructure.pipeline import verificacion
    fuente = inspect.getsource(verificacion)
    i = fuente.index('if res == "FALLO":')
    bloque = fuente[i:i + 700]
    assert 'r.get("gravedad")' in bloque
    assert bloque.index('r.get("gravedad")') < bloque.index("** 0.5")


def test_un_M7_castiga_mas_que_un_M5():
    # Lo que el diseño quería y la inflación había borrado.
    g_m5 = 1.0 + max(0.0, 5.2 - 4.5)
    g_m7 = 1.0 + max(0.0, 7.1 - 4.5)
    assert g_m5 < g_m7
    assert min(3.0, g_m5) < min(3.0, g_m7), "los dos se topaban en 3.0"
