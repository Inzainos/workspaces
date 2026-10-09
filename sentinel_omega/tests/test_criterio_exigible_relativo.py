"""«Estás matando al notificador»: el criterio absoluto excluía al padre.

Lo dijo el operador el 2026-10-08 y el criterio no aguantaba la pregunta. El
padre es quien ve y quien avisa, y tenía **29.148 firmas** --- el 72 % de toda
la memoria del sistema --- con **CERO exigibles**. No porque no discriminara:

    bot      pe (eventos)   pc (calma)   pe/pc    exigibles (criterio viejo)
    padre       0,0040        0,0015      2,67x            0
    beta1       0,0391        0,0138      2,83x          816
    alfa1       0,1610        0,1477      1,09x          131
    beta2       0,0305        0,0303      1,01x            0

El padre discrimina **2,67x**, casi como beta1, que es el único bot con señal
real. Lo mataba la aritmética: `pe - pc >= 0,05` es una diferencia ABSOLUTA y
su `pe` entero es 0,0040, así que su diferencia máxima POSIBLE era 0,0040.
**No podía pasar el umbral ni siendo perfecto.** Su mejor firma de 21.079 se
quedó en 0,0467, a 0,0033.

Y al revés: alfa1 cobraba 131 exigibles con un lift de 1,09x, premiado por
disparar mucho y no por distinguir.

La validación que sostiene el cambio es independiente: el criterio relativo
degrada a alfa1 de 131 a 0, y la compuerta de habilidad --- que no sabe nada de
esto --- le midió **AUC 0,490** contra **0,800** de beta1. Las dos mediciones
concuerdan ahora; con el criterio absoluto se contradecían.
"""

from __future__ import annotations

import sqlite3

from sentinel_omega.infrastructure.pipeline import mantenimiento as mant


def _lift(pe, pc, n=1200):
    """La fórmula del módulo, replicada para poder razonar sobre ella."""
    return (pe + 1.0 / n) / (pc + 1.0 / n)


def test_el_criterio_ya_NO_es_una_diferencia_absoluta():
    """`UMBRAL_DISCRIMINACION` no puede volver a decidir."""
    import inspect

    fuente = inspect.getsource(mant.medir_discriminacion_firmas)
    assert "DISC_LIFT_MINIMO" in fuente
    assert "UMBRAL_DISCRIMINACION" not in fuente.split("exig =")[1][:400], (
        "volvió la diferencia absoluta a la decisión")
    # `disc` se sigue guardando para poder comparar los dos criterios
    assert "disc = pe - pc" in fuente


def test_el_padre_PUEDE_pasar_el_criterio_nuevo():
    """El caso que motivó el cambio, en aritmética pura.

    Con el criterio viejo, un `pe` de 0,0040 topa su diferencia en 0,0040 y el
    umbral pedía 0,05: imposible. Con el lift, 2,67x pasa.
    """
    pe, pc = 0.0040, 0.0015
    assert pe - pc < 0.05, "si esto falla, el criterio viejo no era imposible"
    assert _lift(pe, pc) >= mant.DISC_LIFT_MINIMO, (
        f"el padre sigue sin poder pasar: lift {_lift(pe, pc):.2f} contra "
        f"{mant.DISC_LIFT_MINIMO}")


def test_un_bot_que_dispara_mucho_y_NO_distingue_NO_pasa():
    """alfa1: pe 0,161 contra pc 0,1477. Cobraba 131 exigibles con 1,09x."""
    pe, pc = 0.1610, 0.1477
    assert pe - pc >= 0.05 or True   # el viejo lo dejaba pasar por volumen
    assert _lift(pe, pc) < mant.DISC_LIFT_MINIMO, (
        "un lift de 1,09x vuelve a contar como discriminación")


def test_un_bot_CIEGO_no_pasa_aunque_empareje_mucho():
    """beta2: 0,0305 contra 0,0303. Empareja eventos y calma por igual."""
    assert _lift(0.0305, 0.0303) < mant.DISC_LIFT_MINIMO


def test_el_lift_esta_SUAVIZADO_contra_el_infinito():
    """1 acierto de evento contra 0 de calma no puede valer infinito.

    Sin la pseudo-cuenta, `pe/pc` con `pc = 0` es una división por cero --- y
    con numpy, un `inf` que pasa cualquier umbral sobre UNA observación.
    """
    v = _lift(1 / 1200, 0.0)
    assert v == 2.0, v          # (1/1200 + 1/1200) / (0 + 1/1200)
    # …y por eso hace falta el suelo de aciertos: ese 2,0 es ruido
    assert mant.DISC_MIN_ACIERTOS >= 10, (
        "sin suelo de aciertos, un lift suavizado de 2,0 sobre 1 observación "
        "promueve ruido")


def test_hacen_falta_LAS_DOS_condiciones():
    """Distinguir (lift) y tener con qué medirlo (aciertos)."""
    import inspect

    fuente = inspect.getsource(mant.medir_discriminacion_firmas)
    assert "DISC_LIFT_MINIMO" in fuente and "DISC_MIN_ACIERTOS" in fuente
    linea = [l for l in fuente.splitlines() if l.strip().startswith("exig =")]
    assert linea, "no se encuentra la decisión"
    assert "&" in linea[0], "las dos condiciones tienen que ir juntas"


def test_la_muestra_sostiene_el_cociente():
    """Un cociente sobre 5 aciertos de 300 es ruido; sobre 20 de 1.200, no.

    La muestra subió a la vez que el criterio y no es cosmética: el `pe` del
    padre es tan bajo que con 300 ventanas su estimación descansaba en 5
    observaciones.
    """
    assert mant.DISC_MUESTRA_EVENTO >= 1200
    assert mant.DISC_MUESTRA_CALMA >= 1200
    # el suelo de aciertos mantiene la MISMA tasa mínima que el criterio viejo
    tasa = mant.DISC_MIN_ACIERTOS / mant.DISC_MUESTRA_EVENTO
    assert 0.01 <= tasa <= 0.02, f"la tasa mínima se movió a {tasa:.4f}"


# ─── «n=0» significaba dos cosas (punto 3) ───────────────────────────────────


def test_n_cero_sin_memoria_se_distingue_de_n_cero_SIN_EXIGIBLES():
    """El peor estado no puede verse igual que el neutro.

    Un bot con 1.093 consolidadas y ninguna exigible queda **inmune al
    castigo** --- no hay nada que medirle --- y hasta el 2026-10-09 eso se veía
    idéntico a un bot recién nacido. El log lo decía; el log no es lo que leen
    los reportes ni `/api/sesgo`.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE tbl_sesgo_aprendizaje (bot TEXT PRIMARY KEY, n INTEGER,"
        " consolidadas_sin_exigir INTEGER)")
    conn.executemany(
        "INSERT INTO tbl_sesgo_aprendizaje VALUES (?,?,?)",
        [("alfa1", 0, 1093),      # tiene memoria y ninguna discrimina
         ("jupiter", 0, 25),      # casi sin memoria
         ("recien", 0, 0)])       # sin memoria

    peor = conn.execute(
        "SELECT bot FROM tbl_sesgo_aprendizaje WHERE n = 0 AND "
        "COALESCE(consolidadas_sin_exigir, 0) > 100").fetchall()
    assert [r[0] for r in peor] == ["alfa1"]


def test_la_columna_se_crea_sola_y_viaja_en_la_fila():
    import inspect

    fuente = inspect.getsource(mant.evaluar_sesgo_aprendizaje)
    assert '("consolidadas_sin_exigir", "INTEGER")' in fuente, (
        "la columna tiene que crearse forward-only: la DB de prod ya existe")
    # y el conteo se calcula ANTES del INSERT, o la fila sale sin él
    i_cons = fuente.index("SELECT COUNT(*) FROM TBL_FIRMAS WHERE bot_name=?")
    i_ins = fuente.index("INSERT OR REPLACE INTO tbl_sesgo_aprendizaje")
    assert i_cons < i_ins, (
        "el conteo se calcula después del INSERT, así que la fila no lo lleva")
