"""Schumann WPC: una imagen congelada no es una lectura en vivo.

Medido el 2026-09-27: `shm.jpg` de Tomsk responde HTTP 200 con
``Last-Modified: Mon, 01 Sep 2025 04:20:00 GMT``. Esa misma imagen da
actividad 21,46 % → 7,83 + 21,46 × 0,02 = 8,26 Hz, y desde las 19:45 CST se
guardó en PREC y en `tbl_schumann_vivo` como si fuera en vivo (en_vivo=1,
atraso 0). El commit 27f072a solo cubría el caso «sin lectura» (None → NULL);
una descarga que SÍ responde, con un valor viejo, pasaba como lectura.

Regla original: la lectura WPC solo es viva si la imagen trae su propia hora
(Last-Modified), esa hora es reciente y el valor no repite exacto la última
lectura viva guardada de una hora anterior. Y el LOCF de la base es historia,
nunca «la lectura actual».

2026-09-30 — sos70.ru (sucesor de sosrff, que quedó obsoleto) NO manda
Last-Modified. La prueba de frescura para ese caso es el SHA256 de la imagen
contra el de la última imagen ingestada (`tbl_schumann_img_estado`):
sha igual = no hay dato nuevo = no-signal; sha nueva + valor que se movió =
lectura viva. La regla «valor que repite exacto no aporta» se conserva.
"""
import hashlib
import sqlite3
from datetime import datetime, timezone

import pytest

from sentinel_omega.core import schumann_vivo as sv
from sentinel_omega.core.delta_enriched import fetchers
from sentinel_omega.infrastructure.api import schumann as sch

H = 3600.0
T0 = 1790560000.0  # 2026-09-28 01:46 UTC, la noche del hallazgo
CONGELADA = datetime(2025, 9, 1, 4, 20, tzinfo=timezone.utc)
FRESCA = datetime.fromtimestamp(T0 - 1800, tz=timezone.utc)  # media hora antes


@pytest.fixture()
def wpc(monkeypatch, tmp_path):
    """Simula la descarga (con su Last-Modified y bytes) y el WPC, sin red ni opencv."""
    estado = {"last_modified": CONGELADA, "valor": (8.26, 21.46), "bytes": b"x"}
    img = tmp_path / "shm.jpg"

    def _fetch(save_dir=None):
        img.write_bytes(estado["bytes"])
        return str(img)

    monkeypatch.setattr(sch, "fetch_schumann_spectrogram", _fetch)
    monkeypatch.setattr(sch, "last_modified_de", lambda path: estado["last_modified"])
    monkeypatch.setattr(sch, "analyze_spectrogram", lambda p: estado["valor"])
    return estado


def test_la_descarga_guarda_su_last_modified(monkeypatch, tmp_path):
    """El Last-Modified de la respuesta HTTP llega a la comprobación."""
    class _Resp:
        content = b"jpg"
        headers = {"Last-Modified": "Mon, 01 Sep 2025 04:20:00 GMT"}

        def raise_for_status(self):
            pass

    class _Sesion:
        def get(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(sch, "get_session", lambda: _Sesion())
    path = sch.fetch_schumann_spectrogram(save_dir=str(tmp_path))
    assert sch.last_modified_de(path) == CONGELADA
    assert sch.last_modified_de(path) is None  # se consume una sola vez


def test_imagen_congelada_de_2025_no_es_lectura(wpc):
    assert sch.fetch_schumann_resonance(cleanup=False, previa=None, ahora=T0) is None


def test_imagen_sin_last_modified_no_es_lectura(wpc, tmp_path):
    """El caso sos70: sin Last-Modified, la prueba de frescura es el sha256.

    La primera imagen entra (no hay estado previo ni valor previo); la MISMA
    imagen otra vez ya no: no hay dato nuevo, no se inventa la lectura."""
    wpc["last_modified"] = None
    wpc["bytes"] = b"imagen-A"
    db = tmp_path / "estado_sha.db"
    r = sch.fetch_schumann_resonance(
        cleanup=False, previa=None, ahora=T0, db_path=db)
    assert r == (8.26, 21.46)
    assert sch.sha_ingestado(db) == hashlib.sha256(b"imagen-A").hexdigest()
    # La misma imagen de nuevo → no-signal, aunque no haya valor previo.
    assert sch.fetch_schumann_resonance(
        cleanup=False, previa=None, ahora=T0, db_path=db) is None


def test_imagen_nueva_con_valor_nuevo_si_es_lectura(wpc, tmp_path):
    wpc["last_modified"] = None
    wpc["bytes"] = b"imagen-A"
    db = tmp_path / "estado_sha.db"
    assert sch.fetch_schumann_resonance(
        cleanup=False, previa=None, ahora=T0, db_path=db) == (8.26, 21.46)
    # Rota la imagen (sha nueva) y el valor se mueve → lectura viva.
    wpc["bytes"] = b"imagen-B"
    wpc["valor"] = (8.31, 24.0)
    assert sch.fetch_schumann_resonance(
        cleanup=False, previa=(8.26, 21.46), ahora=T0, db_path=db) == (8.31, 24.0)
    assert sch.sha_ingestado(db) == hashlib.sha256(b"imagen-B").hexdigest()


def test_imagen_nueva_con_valor_identico_no_es_lectura(wpc, tmp_path):
    """Regla del 27-sep conservada: un valor que repite exacto la última
    lectura viva no aporta información, aunque la imagen sí haya cambiado.
    El sha de esa imagen rechazada NO se guarda."""
    wpc["last_modified"] = None
    wpc["bytes"] = b"imagen-A"
    db = tmp_path / "estado_sha.db"
    assert sch.fetch_schumann_resonance(
        cleanup=False, previa=None, ahora=T0, db_path=db) is not None
    wpc["bytes"] = b"imagen-B"  # imagen nueva…
    # …pero el valor repite la lectura viva previa → no-signal.
    assert sch.fetch_schumann_resonance(
        cleanup=False, previa=(8.26, 21.46), ahora=T0, db_path=db) is None
    assert sch.sha_ingestado(db) == hashlib.sha256(b"imagen-A").hexdigest()


def test_imagen_fresca_con_valor_nuevo_si_es_lectura(wpc):
    wpc["last_modified"] = FRESCA
    wpc["valor"] = (8.31, 24.0)
    r = sch.fetch_schumann_resonance(cleanup=False, previa=(8.26, 21.46), ahora=T0)
    assert r == (8.31, 24.0)


def test_valor_identico_a_la_lectura_previa_no_es_lectura(wpc):
    wpc["last_modified"] = FRESCA
    assert sch.fetch_schumann_resonance(cleanup=False, previa=(8.26, 21.46), ahora=T0) is None


def test_edad_limite():
    viejo = datetime.fromtimestamp(T0 - (sch.MAX_EDAD_IMAGEN_HORAS + 0.1) * H, tz=timezone.utc)
    assert "old" in sch.motivo_lectura_no_viva(8.3, 23.5, viejo, None, ahora=T0)
    assert sch.motivo_lectura_no_viva(8.3, 23.5, FRESCA, None, ahora=T0) is None


def test_parse_last_modified():
    assert sch._parse_last_modified("Mon, 01 Sep 2025 04:20:00 GMT") == CONGELADA
    assert sch._parse_last_modified(None) is None
    assert sch._parse_last_modified("no es una fecha") is None


def _db_vivo(tmp_path, filas):
    db = tmp_path / "vivo.db"
    c = sqlite3.connect(db)
    sv.asegurar_tabla(c)
    c.executemany(
        "INSERT INTO tbl_schumann_vivo (timestamp_blk, schumann_hz, schumann_activity, "
        "en_vivo, ultimo_vivo_ts, atraso_horas) VALUES (?,?,?,?,?,?)", filas)
    c.commit()
    c.close()
    return db


def test_ultima_lectura_viva_ignora_arrastres_y_la_hora_actual(tmp_path):
    db = _db_vivo(tmp_path, [
        ("2026-09-28 00:00", 8.30, 23.0, 1, "2026-09-28 00:00", 0),
        ("2026-09-28 01:00", 8.26, 21.46, 0, "2026-09-28 00:00", 1),   # arrastre
        ("2026-09-28 02:00", 8.40, 28.0, 1, "2026-09-28 02:00", 0),    # hora futura
    ])
    assert sch.ultima_lectura_viva(db, ahora=T0) == (8.30, 23.0)


def test_sin_lectura_viva_no_se_escribe_fila_en_vivo_con_atraso_cero(wpc):
    """Lo que el launcher hace con el None: nunca una fila en_vivo=1 / atraso 0."""
    c = sqlite3.connect(":memory:")
    r = sch.fetch_schumann_resonance(cleanup=False, previa=None, ahora=T0)
    est = sv.registrar(c, *(r or (None, None)), ahora=T0)
    assert est["estado"] == "desconocido"
    assert c.execute("SELECT count(*) FROM tbl_schumann_vivo "
                     "WHERE en_vivo=1 AND atraso_horas=0").fetchone()[0] == 0
    c.close()


def test_locf_de_la_base_va_marcado(tmp_path):
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = _db_vivo(tmp_path, [(f"{hoy} 00:00", 8.30, 23.0, 1, f"{hoy} 00:00", 0)])
    s = fetchers._schumann_from_db(30, db_path=db)
    assert s is not None and s.es_locf is True


def test_wpc_en_vivo_no_va_marcado_como_locf(wpc):
    wpc["last_modified"] = datetime.now(timezone.utc)
    wpc["valor"] = (8.31, 24.0)
    import unittest.mock as um
    with um.patch.object(sch, "ultima_lectura_viva", return_value=None):
        s = fetchers._schumann_from_wpc()
    assert s is not None and s.es_locf is False
