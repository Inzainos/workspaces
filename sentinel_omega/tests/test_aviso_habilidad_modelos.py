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


def test_falta_de_MUESTRA_no_se_confunde_con_metadato_VIEJO(models_dir):
    """Dos razones distintas para no tener AUC, y las confundí yo mismo.

    Escrito el 2026-10-08 por la mañana, la nota del digesto decía de alfa2 y
    jupiter «son anteriores a la compuerta de habilidad». Dos horas después, el
    reentrenamiento corrió de verdad y los midió: el metadato pasó a ser **de
    hoy** y los dos seguían sin AUC, pero por una razón medida y distinta ---
    38 y 53 muestras, por debajo de los mínimos. La nota los seguía culpando
    de ser viejos.

    Falta de evidencia no es una mala nota, y tampoco es un metadato rancio.
    """
    _onnx(models_dir, "alfa2")
    _onnx(models_dir, "jupiter")
    _onnx(models_dir, "loki")        # este no aparece en el metadato
    (models_dir / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-08T19:30:19Z",
        "bots": {
            # alfa2: la compuerta ni lo evaluó --- su razón vive en `source`,
            # NO en `habilidad`, que no existe. Leer solo `motivo` la perdía.
            "alfa2": {"n": 0, "reentrenado": False,
                      "source": "NO se reentrena: 38 muestras reales (<50)"},
            # jupiter: entró en `medir_habilidad` y salió sin AUC con motivo.
            "jupiter": {"n": 53, "source": "db-only (53)", "habilidad": {
                "auc": None, "aprueba": False,
                "motivo": "solo 53 muestras; por debajo de 60 el AUC es ruido"}},
        },
    }))

    txt = cv.get_model_status("/no/existe.db")

    # Cada uno con SU razón, no con una genérica
    assert "38 muestras" in txt, "se perdió la razón que vive en `source`"
    assert "por debajo de 60 el AUC es ruido" in txt
    assert "sin habilidad medible" in txt
    # loki no está en el metadato: ESE sí es el caso «anterior a la compuerta»
    assert "LOKI" in txt and "habilidad sin medir" in txt
    assert "anteriores a la compuerta" in txt
    # …y no se le echa a alfa2/jupiter, que pasaron por ella
    assert "falta de evidencia, no una mala nota" in txt


def test_un_bot_aprobado_no_hereda_el_source_como_motivo(models_dir):
    """`source` es «db-only (7000)» en todos: no es un motivo de nada.

    El respaldo a `source` solo vale cuando NO hay AUC. Sin acotarlo, un bot
    aprobado mostraría «db-only (7000)» en la columna Motivo del tablero como
    si la compuerta hubiera objetado algo.
    """
    from sentinel_omega.infrastructure.dashboard import api

    _onnx(models_dir, "beta1")
    (models_dir / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-09T03:00:00Z",
        "bots": {"beta1": {"n": 7000, "source": "db-only (7000)",
                           "habilidad": {"auc": 0.61, "aprueba": True,
                                         "ganancia_sobre_nulo": 0.05}}},
    }))
    fila = next(f for f in api.modelos()["modelos"] if f["bot"] == "beta1")
    assert fila["aprueba"] is True
    assert fila["motivo"] is None, f"heredó un motivo falso: {fila['motivo']}"


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


def test_el_bloque_del_LAG_dice_que_son_solo_las_especificas(tmp_path, models_dir):
    """La QUINTA superficie del cambio de significado, y la encontró el vecino.

    El 2026-10-08 `tbl_lag_anticipacion` pasó a promediar solo las firmas
    específicas --- las que no emparejan en ventanas de calma de su propio
    nodo. Barrí cuatro superficies (`/api/lag`, los tres reportes) y declaré el
    trabajo hecho; el bloque «Lag de anticipación» del digesto seguía
    imprimiendo las horas como si fueran el promedio de todas. Dos de cada tres
    firmas dan ese número también en calma.

    Lo encontró la sesión del Concilio leyendo mi propio cambio. Declarar «las
    cuatro superficies» sin haber hecho el `grep` era la suposición, otra vez.
    """
    _onnx(models_dir, "beta1")
    (models_dir / "models_meta.json").write_text(json.dumps({"bots": {}}))

    db = tmp_path / "lag.db"
    c = sqlite3.connect(db)
    c.executescript(
        "CREATE TABLE tbl_lag_anticipacion ("
        "  event_class TEXT PRIMARY KEY, lag_promedio_h REAL);"
        "CREATE TABLE TBL_FIRMAS ("
        "  firma_id INTEGER PRIMARY KEY, estado TEXT, exigible INTEGER,"
        "  lag_promedio_h REAL, lag_n INTEGER DEFAULT 0,"
        "  lag_calma_h REAL, lag_calma_n INTEGER, lag_medido_at TEXT);"
    )
    c.execute("INSERT INTO tbl_lag_anticipacion VALUES ('SISMO_M4', 201.0)")
    # dos específicas y tres que persisten: 40 % anticipan
    filas = [(i, "consolidada", 1, 100.0, 3, None, 0, "2026-10-08") for i in range(2)]
    filas += [(i + 2, "consolidada", 1, 100.0, 3, 180.0, 2, "2026-10-08") for i in range(3)]
    c.executemany("INSERT INTO TBL_FIRMAS VALUES (?,?,?,?,?,?,?,?)", filas)
    c.commit()
    c.close()

    txt = cv.get_model_status(str(db))

    assert "SISMO_M4: ~201h" in txt, "se perdió el bloque del lag"
    assert "Solo firmas que ANTICIPAN" in txt, (
        "el bloque del lag volvió a dar las horas por anticipación sin decir "
        "que son solo las específicas")
    assert "2 de 5" in txt and "40.0 %" in txt
    assert "no cuánto avisa" in txt


def test_el_bloque_del_LAG_pasa_el_saneador_de_telegram(tmp_path, models_dir):
    """La lección del `(<50)`: que aparezca no basta, tiene que PARSEAR.

    Un test que solo comprobara el texto habría pasado el 2026-10-08 mientras
    Telegram rechazaba el mensaje entero y se perdían 17 avisos.
    """
    from sentinel_omega.infrastructure.api.telegram import sanear_html_telegram

    _onnx(models_dir, "beta1")
    (models_dir / "models_meta.json").write_text(json.dumps({
        "bots": {"beta1": {"n": 0, "source": "NO se reentrena: 38 (<50) y sin prior"}},
    }))
    db = tmp_path / "vacia.db"
    sqlite3.connect(db).close()

    txt = cv.get_model_status(str(db))
    assert "(&lt;50)" in txt or "&lt;50" in txt, (
        "el `(<50)` volvió sin escapar: Telegram rechaza el mensaje COMPLETO")
    assert sanear_html_telegram(txt) == txt, (
        "el saneador tuvo que corregir la salida, o sea que iba mal formada")
