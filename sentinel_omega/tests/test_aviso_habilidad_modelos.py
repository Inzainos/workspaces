"""El ✅ del digesto era «el archivo existe». Que no vuelva.

Medido el 2026-10-08 leyendo lo que de verdad llega al teléfono del operador:
el reporte horario de Telegram cerraba con

    🤖 Modelos ONNX activos:
    ✅ ALFA1 (791KB)
    ✅ BETA1 (964KB)
    …

y la única comprobación detrás de cada paloma era `os.path.exists`. El estado
real de esos archivos ese día:

    ocho .onnx escritos del 30-sep al 4-oct    la compuerta se escribió el 7-oct
    models_meta.json SIN clave «habilidad» ni «compuerta»

O sea: ninguno había pasado por `medir_habilidad`, y el aviso los presentaba
como ocho modelos funcionando. Es el vicio central del proyecto en la
superficie que más se lee --- un indicador que no mide lo que su nombre
promete --- y además el inverso del que arreglamos en los reportes: allí un ✅
verde iba sobre la memorización; aquí iba sobre la existencia de un archivo.

La otra mitad del arreglo: el digesto no llevaba NINGUNA de las dos varas del
Juez. `CLAUDE.md` pide que la asertividad nunca viaje sola, y el reporte
horario era la última superficie donde no aparecía ni ella ni la ganancia.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from sentinel_omega.infrastructure.messaging import consenso_vigilante as cv


@pytest.fixture()
def models_dir(tmp_path, monkeypatch):
    """Un directorio de modelos propio: nunca se lee el de producción."""
    d = tmp_path / "models"
    d.mkdir()
    monkeypatch.setattr(cv, "MODELS_DIR", d)
    return d


def _onnx(d, bot, kib=4):
    (d / cv.NOMBRES_ONNX[bot]).write_bytes(b"\0" * (kib * 1024))


def test_un_onnx_sin_habilidad_medida_NO_lleva_paloma(models_dir):
    """El caso exacto de producción: archivo en disco, metadato sin medir."""
    _onnx(models_dir, "alfa1")
    (models_dir / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-04T18:44:39Z",
        "bots": {"alfa1": {"n": 1420, "reentrenado": True}},   # sin «habilidad»
    }))

    txt = cv.get_model_status("/no/existe.db")
    assert "✅ ALFA1" not in txt, "volvió la paloma por existir el archivo"
    assert "ALFA1" in txt
    assert "sin medir" in txt
    # y se dice POR QUÉ, con la fecha del metadato, no un encogimiento de hombros
    assert "2026-10-04" in txt
    assert "anteriores a la compuerta" in txt


def test_un_onnx_aprobado_SI_lleva_paloma_y_su_AUC(models_dir):
    """El arreglo no puede volverlo mudo: una habilidad medida se enseña."""
    _onnx(models_dir, "beta1")
    (models_dir / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-09T03:00:00Z",
        "bots": {"beta1": {"n": 7000, "habilidad": {
            "auc": 0.612, "auc_inferior": 0.571,
            "ganancia_sobre_nulo": 0.058, "aprueba": True}}},
    }))

    txt = cv.get_model_status("/no/existe.db")
    assert "✅ BETA1" in txt
    assert "0.612" in txt
    assert "+0.058" in txt, "la ganancia sobre el modelo nulo tiene que viajar"
    assert "sin medir" not in txt


def test_un_onnx_NEGADO_por_la_compuerta_se_distingue_del_aprobado(models_dir):
    """Tres estados, no dos: aprobado, negado y sin medir."""
    _onnx(models_dir, "delta")
    (models_dir / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-09T03:00:00Z",
        "bots": {"delta": {"n": 7000, "habilidad": {
            "auc": 0.998, "aprueba": False,
            "motivo": "AUC 0.998 por encima del techo creible: eso es una fuga"}}},
    }))

    txt = cv.get_model_status("/no/existe.db")
    assert "✅ DELTA" not in txt
    assert "⚠️ DELTA" in txt
    assert "fuga" in txt, "el motivo de la negativa es la información útil"
    assert "se usa el anterior" in txt


def test_sin_archivo_en_disco_se_dice_que_no_hay_modelo(models_dir):
    (models_dir / "models_meta.json").write_text(json.dumps({"bots": {}}))
    txt = cv.get_model_status("/no/existe.db")
    assert "❌ OMEGA" in txt
    assert "sin modelo en disco" in txt


def test_sin_metadato_no_se_cae_ni_inventa(models_dir):
    """`models_meta.json` ausente: ocho «sin medir», no una excepción."""
    _onnx(models_dir, "loki")
    txt = cv.get_model_status("/no/existe.db")
    assert "error" not in txt.lower()
    assert "sin medir" in txt


# ─── La vara del Juez en el digesto ──────────────────────────────────────────

_VIVA_DDL = """
CREATE TABLE viva_real (
  verdad TEXT, resultado TEXT, en_vivo INTEGER DEFAULT 1, timestamp REAL
);
"""


def _db_con_veredictos(tmp_path, filas, en_vivo=1):
    p = tmp_path / "juez.db"
    c = sqlite3.connect(p)
    c.executescript(_VIVA_DDL)
    c.executemany(
        "INSERT INTO viva_real (verdad, resultado, en_vivo, timestamp) "
        "VALUES (?,?,?,0)", [(v, r, en_vivo) for v, r in filas])
    c.commit()
    c.close()
    return str(p)


def test_la_vara_lleva_la_asertividad_JUNTO_a_la_ganancia(tmp_path):
    """Nunca una sin la otra: es la regla del tablero, aquí en el aviso."""
    filas = ([("sin eventos", "ACIERTO")] * 90
             + [("SISMO_M4.6", "ACIERTO")] * 5
             + [("sin eventos", "FALSO_POSITIVO")] * 5)
    txt = cv.get_vara_juez(_db_con_veredictos(tmp_path, filas))
    assert "ganancia" in txt.lower()
    assert "asertividad" in txt.lower()
    assert "nunca" in txt and "alarma" in txt, (
        "falta el comparador: contra qué se mide la asertividad")


def test_una_asertividad_POR_DEBAJO_del_silencio_se_puede_leer(tmp_path):
    """El estado medido en producción el 2026-10-08: 35,3 % contra 97,1 %.

    Un bot que nunca alarma habría sacado casi el triple. Si el aviso enseñara
    la asertividad sola, ese 35 % parecería un sistema malo; y si enseñara solo
    la ganancia, el 1,17× parecería bueno. Hacen falta las dos.
    """
    filas = ([("sin eventos", "ACIERTO")] * 100
             + [("sin eventos", "FALSO_POSITIVO")] * 197
             + [("SISMO_M4.6", "ACIERTO")] * 6
             + [("SISMO_M4.6", "FALLO")] * 3)
    txt = cv.get_vara_juez(_db_con_veredictos(tmp_path, filas))
    assert "306 ventanas" in txt
    assert "9 con evento" in txt
    # 6 detectadas + 197 falsas alarmas: las alarmas se cuentan donde el Juez
    # las vio, no sumando los eventos (tres de los nueve fueron FALLO).
    assert "203 alarmas" in txt


def test_la_vara_filtra_en_vivo(tmp_path):
    """`viva_real` NO filtra `en_vivo`: arrastra los duplicados del 27-sep."""
    filas = [("sin eventos", "ACIERTO")] * 50
    db = _db_con_veredictos(tmp_path, filas, en_vivo=0)
    txt = cv.get_vara_juez(db)
    assert "sin veredictos cerrados" in txt, (
        "entraron filas con en_vivo=0 a la vara de asertividad")


def test_sin_veredictos_lo_dice_en_vez_de_un_cero(tmp_path):
    txt = cv.get_vara_juez(_db_con_veredictos(tmp_path, []))
    assert "sin veredictos cerrados" in txt
    assert "0.00" not in txt, "un cero fabricado donde no hubo medición"


def test_el_digesto_LLEVA_las_dos_cosas(tmp_path, models_dir):
    """Punta a punta: que el HTML que se enviaría las contenga de verdad.

    Las dos funciones podían estar perfectas y no estar llamadas desde
    `_build_digest` --- es exactamente el fallo que la regla cero persigue.
    """
    _onnx(models_dir, "alfa1")
    filas = ([("sin eventos", "ACIERTO")] * 90
             + [("SISMO_M4.6", "ACIERTO")] * 5
             + [("sin eventos", "FALSO_POSITIVO")] * 5)
    db = _db_con_veredictos(tmp_path, filas)

    vig = cv.ConsensoVigilante(db_path=db, dry_run=True)
    html, _subject = vig._build_digest({"fantasma": 2.1, "muro_n": 1}, [])

    assert "Vara del Juez" in html
    assert "Modelos ONNX" in html
    assert "habilidad" in html.lower()
    assert "✅ ALFA1" not in html
