"""`TG_DIGEST_MINUTES` era un mando muerto en la ruta que despacha de verdad.

Qué pasó (2026-10-07)
---------------------
El operador recibía cuatro reportes por hora teniendo `TG_DIGEST_MINUTES=60`
declarado en `AGENTS.md`, `CLAUDE.md` y el `CHANGELOG`. Medido en el journal:

    digestos despachados en un día: 54   ->  4 por hora, de 00h a 13h

La cadena completa, y hacen falta los cuatro eslabones para entenderla:

1. `sentinel-omega-rutinas.timer` corre cada 15 min (`OnUnitActiveSec=15min`).
2. `deploy/rutinas_locales.sh` pone compuerta de minuto (`$M -lt 15`) a TODOS
   sus bloques **menos al último**, que es `enviar_correos.py`.
3. `enviar_correos.py` llamaba `flush_digest(force=True)`, y `force` salta el
   temporizador --- lo dice su propio docstring: «force ignores the timer».
4. Y debajo de todo, el eslabón que hacía inútil arreglar solo el 3:
   `last_digest_ts` nacía en `0.0` en el `__init__` y **no se guardaba en
   ninguna parte**. El servicio es `Type=oneshot`: cada corrida es un proceso
   nuevo, así que la compuerta de `maybe_flush` no podía cerrarse nunca.

El `launcher.py` no sufría el bicho porque es un proceso largo y
`get_vigilante()` le devuelve un único objeto: ahí la marca en memoria
funcionaba. Por eso el defecto solo se veía en el teléfono, no en el código.

Es la tercera vez que aparece la misma familia: el `days` de `fetch_kp_index`
y el `confidence_threshold` de los ocho ONNX también estaban declarados y
leídos por nadie. La variante de aquí es más fina --- el mando SÍ se leía, pero
el estado contra el que se comparaba moría con el proceso.

Lo que fija esta prueba es la frase que importa: **una instancia nueva no
vuelve a mandar el digesto dentro de la ventana.** Si alguien revierte la
persistencia, aquí se ve.
"""
from __future__ import annotations

import inspect
import json
import logging
from pathlib import Path

import pytest

from sentinel_omega.infrastructure.messaging.consenso_vigilante import (
    ConsensoVigilante,
    reset_vigilante,
)

SNAP = {"fantasma": 2.0, "nivel": "bajo", "muro_n": 0, "loop_alive": True}


@pytest.fixture(autouse=True)
def _sin_red_ni_estado_de_produccion(monkeypatch, tmp_path):
    """Nada de red y, sobre todo, nada de leer o escribir la marca real: un
    test que la escribiera dejaría al operador una hora sin reporte."""
    monkeypatch.setenv("TG_DIGEST_STATE", str(tmp_path / "estado_digesto.json"))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(ConsensoVigilante, "_send", lambda *a, **k: True)
    reset_vigilante()
    yield
    reset_vigilante()


def _proceso_nuevo(reloj, minutos=60):
    """Una instancia recién construida = la siguiente corrida del oneshot."""
    return ConsensoVigilante(
        dry_run=False, digest_minutes_override=minutos, now_fn=lambda: reloj["t"])


# ─── el bicho, exactamente ────────────────────────────────────────────────────

def test_un_proceso_nuevo_NO_repite_el_digesto_dentro_de_la_ventana():
    """El corazón del arreglo. Antes del 2026-10-07 esto mandaba las cuatro."""
    reloj = {"t": 1_000_000.0}
    primero = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert primero is not None and primero.sent

    enviados = 0
    for _ in range(3):                      # las tres corridas siguientes de 15 min
        reloj["t"] += 15 * 60
        rec = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
        if rec is not None:
            enviados += 1
    assert enviados == 0, (
        f"{enviados} digestos de más en la hora: la marca no sobrevivió al "
        "proceso, que es justo el bicho de los 54 despachos al día")


def test_cumplida_la_hora_el_siguiente_proceso_SI_manda():
    """La política 1 del módulo es no saltarse la hora: el arreglo no puede
    convertirse en un silencio."""
    reloj = {"t": 2_000_000.0}
    assert _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP) is not None
    reloj["t"] += 60 * 60 + 1
    rec = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert rec is not None and rec.sent


def test_la_marca_queda_escrita_con_el_sello_del_envio(tmp_path):
    reloj = {"t": 3_000_000.0}
    rec = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    guardado = json.loads(
        (tmp_path / "estado_digesto.json").read_text(encoding="utf-8"))
    assert guardado["last_digest_ts"] == pytest.approx(rec.ts)


# ─── que el arreglo no se vuelva un silencio nuevo ───────────────────────────

def test_si_telegram_FALLA_la_marca_no_se_mueve(monkeypatch):
    """Si el envío no salió, la corrida de los 15 min siguientes REINTENTA en
    vez de callarse una hora. Un fallo no puede comprar silencio."""
    monkeypatch.setattr(ConsensoVigilante, "_send", lambda *a, **k: False)
    reloj = {"t": 4_000_000.0}
    primero = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert primero is not None and primero.sent is False

    reloj["t"] += 15 * 60
    segundo = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert segundo is not None, (
        "tras un fallo de Telegram la marca se movió igual: el sistema se "
        "quedaría una hora sin reporte por un error de red")


def test_una_marca_en_el_futuro_no_silencia_el_digesto(tmp_path, caplog):
    """Un reloj que salta --- o un archivo copiado de otra máquina --- dejaría
    el digesto mudo durante horas sin que nada lo delate (regla 7)."""
    ruta = tmp_path / "estado_digesto.json"
    reloj = {"t": 5_000_000.0}
    ruta.write_text(json.dumps({"last_digest_ts": reloj["t"] + 86_400}),
                    encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        rec = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert rec is not None and rec.sent
    assert "futuro" in caplog.text


@pytest.mark.parametrize("contenido", ["", "{", "{}", '{"last_digest_ts": "ayer"}'])
def test_una_marca_ilegible_manda_digesto_y_lo_dice(tmp_path, caplog, contenido):
    """Ante la duda se envía --- pero el motivo queda en el log, porque un
    descarte silencioso esconde el fallo indefinidamente (regla 10)."""
    (tmp_path / "estado_digesto.json").write_text(contenido, encoding="utf-8")
    reloj = {"t": 6_000_000.0}
    with caplog.at_level(logging.WARNING):
        rec = _proceso_nuevo(reloj).maybe_flush(snapshot=SNAP)
    assert rec is not None and rec.sent
    if contenido != "":                      # un archivo vacío ya es json inválido
        assert "ilegible" in caplog.text


def test_sin_marca_previa_manda(tmp_path):
    """Primera corrida de la vida: no hay archivo y eso no es un fallo."""
    assert not (tmp_path / "estado_digesto.json").exists()
    rec = _proceso_nuevo({"t": 7_000_000.0}).maybe_flush(snapshot=SNAP)
    assert rec is not None and rec.sent


# ─── que nadie vuelva a saltarse el temporizador ─────────────────────────────

def test_el_despachador_NO_vuelve_a_forzar_el_digesto():
    """`force=True` en `enviar_correos.py` fue la causa visible. Que el
    regreso sea un test rojo y no 96 mensajes al día."""
    fuente = Path("deploy/enviar_correos.py").read_text(encoding="utf-8")
    assert "flush_digest(force=False)" in fuente, (
        "deploy/enviar_correos.py ya no honra la cadencia")
    assert "flush_digest(force=True)" not in fuente


def test_el_dry_run_no_toca_el_estado_de_produccion(monkeypatch, tmp_path):
    """Sin esto, una prueba o una corrida de prácticas podía escribir la marca
    real y dejar al operador una hora sin reporte."""
    monkeypatch.delenv("TG_DIGEST_STATE", raising=False)
    v = ConsensoVigilante(dry_run=True, digest_minutes_override=60)
    assert v._digest_state_path() is None
    v.flush_digest(force=True, snapshot=SNAP)   # no debe escribir nada


def test_la_compuerta_sigue_leyendo_el_mando_declarado():
    """Que `TG_DIGEST_MINUTES` siga siendo el que manda, y no una constante
    escondida en el script del timer."""
    from sentinel_omega.infrastructure.messaging import consenso_vigilante as cv

    assert "TG_DIGEST_MINUTES" in inspect.getsource(cv.digest_minutes)
    reloj = {"t": 8_000_000.0}
    assert _proceso_nuevo(reloj, minutos=30).maybe_flush(snapshot=SNAP) is not None
    reloj["t"] += 31 * 60
    assert _proceso_nuevo(reloj, minutos=30).maybe_flush(snapshot=SNAP) is not None


# ─── modo TORMENTA ACTIVA (2026-10-12): la tormenta del 10-oct fue invisible ──

def _proceso_con_tormenta(reloj, tormenta, minutos=60, minutos_tormenta=15):
    """Vigilante con la señal de tormenta INYECTADA: sin DB, sin red."""
    return ConsensoVigilante(
        dry_run=False, digest_minutes_override=minutos,
        digest_minutes_tormenta_override=minutos_tormenta,
        tormenta_fn=lambda: tormenta, now_fn=lambda: reloj["t"])


def test_con_tormenta_la_cadencia_baja_a_la_de_tormenta():
    """Kp>=5 en la ventana: el digesto sale cada 15 min, no cada 60. Es la
    tormenta del 10-oct de nuevo: esta vez el operador la ve en tiempo
    casi real (la cadencia del oneshot de rutinas)."""
    tormenta = {"activa": True, "kp_max": 7.0, "kp_min_umbral": 5.0}
    reloj = {"t": 9_000_000.0}
    recs = []
    for _ in range(4):                      # 4 corridas del oneshot: 0, 15, 30, 45 min
        rec = _proceso_con_tormenta(reloj, tormenta).maybe_flush(snapshot=SNAP)
        recs.append(rec)
        reloj["t"] += 15 * 60
    assert all(r is not None and r.sent for r in recs), (
        "con tormenta activa cada corrida de 15 min debe mandar el digesto")


def test_kp_debajo_del_umbral_NO_es_tormenta():
    """Kp 3 en la ventana: cadencia de calma. El 5 es la definición G1 de
    NOAA y el mismo umbral medido del scanner (regla 8), no un número
    puesto a mano."""
    tormenta = {"activa": False, "kp_max": 3.0, "kp_min_umbral": 5.0}
    reloj = {"t": 10_000_000.0}
    assert _proceso_con_tormenta(reloj, tormenta).maybe_flush(snapshot=SNAP) is not None
    reloj["t"] += 15 * 60
    assert _proceso_con_tormenta(reloj, tormenta).maybe_flush(snapshot=SNAP) is None, (
        "sin tormenta, 15 min NO puede vencer la ventana de 60")


def test_sin_dato_de_kp_no_hay_modo_tormenta():
    """Sin lectura en la tabla horaria: None, no cero (regla 7). La cadencia
    se queda en calma aunque el mundo esté en llamas --- lo honesto es
    decir que no se midió."""
    reloj = {"t": 11_000_000.0}
    assert _proceso_con_tormenta(reloj, None).maybe_flush(snapshot=SNAP) is not None
    reloj["t"] += 15 * 60
    assert _proceso_con_tormenta(reloj, None).maybe_flush(snapshot=SNAP) is None


def test_el_digesto_lleva_el_banner_y_el_sello_de_tormenta():
    """Lo primero que el operador lee en el parte durante una tormenta es
    QUE HAY TORMENTA, con su Kp y la cadencia nueva. Y el subject lo
    lleva, para verlo sin abrir el mensaje."""
    v = ConsensoVigilante(
        dry_run=True, digest_minutes_override=60,
        digest_minutes_tormenta_override=15,
        tormenta_fn=lambda: {"activa": True, "kp_max": 6.7, "kp_min_umbral": 5.0})
    html, subject = v._build_digest(
        {"fantasma": 12.0, "nivel": "MODERATE", "muro_n": 2}, [],
        tormenta=v._tormenta_activa())
    assert "MODO TORMENTA ACTIVA" in html
    assert "6.7" in html          # el Kp medido, no una plantilla
    assert "15" in html           # la cadencia nueva, declarada
    assert "TORMENTA" in subject


def test_la_tormenta_se_mide_contra_la_tabla_horaria_real(tmp_path):
    """La señal de producción no es una simulación: MAX(kp_max) de las
    últimas 2 h de `tbl_clima_espacial_raw` (regla 9: contra el dato, no
    contra el manual). Con DB explícita --- el conftest aísla la de prod."""
    import sqlite3
    from datetime import datetime, timedelta, timezone

    db = tmp_path / "tormenta.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE tbl_clima_espacial_raw (timestamp_blk TEXT, kp_max REAL)")
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    vieja = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M")
    conn.execute("INSERT INTO tbl_clima_espacial_raw VALUES (?, ?)", (vieja, 8.0))  # fuera de ventana
    conn.execute("INSERT INTO tbl_clima_espacial_raw VALUES (?, ?)", (ahora, 6.2))  # dentro
    conn.commit(); conn.close()

    v = ConsensoVigilante(dry_run=True, db_path=str(db))
    t = v._tormenta_activa()
    assert t is not None and t["activa"] is True
    assert t["kp_max"] == 6.2, "el Kp 8 de hace 5 h NO cuenta: la ventana es de 3 h"

    # y sin la tabla: None, no un falso negativo disfrazado de calma
    db2 = tmp_path / "vacia.db"
    sqlite3.connect(db2).close()
    v2 = ConsensoVigilante(dry_run=True, db_path=str(db2))
    assert v2._tormenta_activa() is None
