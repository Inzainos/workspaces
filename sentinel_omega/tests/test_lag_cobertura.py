"""El lag no se perdía al calcularse: se perdía porque no se calculaba.

Encontrado el 2026-10-08, con el operador preguntando «en qué momento se está
perdiendo ese tiempo». La huella estaba a la vista en los datos, y es del
revés de lo que haría un muestreo honesto:

    bot/clase              exigibles   con lag
    beta1 SISMO_M4              417         9   <- cubo GRANDE, casi vacío
    beta1 SISMO_M5              260        12   <- cubo GRANDE, casi vacío
    beta1 SISMO_M4_obs           20        20   <- cubo PEQUEÑO, completo
    beta1 SISMO_M7               19        19   <- cubo PEQUEÑO, completo

Los cubos pequeños con cobertura total y los grandes vacíos no es física: es
presupuesto. Dos defectos en el mismo bucle de `calcular_lags_anticipacion`:

1. **El tope se contaba en SONDEOS DE EVENTO, no en firmas**, y cada firma
   gasta hasta 3 (`LIMIT 3`). Así que `LAG_MUESTRA_POR_CLASE = 150` eran **50
   firmas** por (bot, clase), y las 367 restantes de beta1/SISMO_M4 se
   saltaban con un `continue` **sin log** --- regla dura 10. Medido a mano
   sobre 40 de esas saltadas: entre el 33 % y el 80 % SÍ dan lag según el
   offset. No es que no anticiparan; es que nadie las miró.

2. **La rejilla paraba en 24 h.** Y el porcentaje que empareja no se derrumba
   al acercarse al evento, SUBE: 33 % a 336 h, 58 % a 24 h, 80 % a 0 h. Todo
   lo que anticipa menos de un día se reportaba como `None`.

Resultado del arreglo, medido en producción: 159/982 exigibles con lag -> 978.
"""

from __future__ import annotations

import sqlite3

from sentinel_omega.infrastructure.pipeline import entrenamiento as ent


def test_el_tope_se_cuenta_en_FIRMAS_no_en_sondeos():
    """El contador sube UNA vez por firma, pase lo que pase con sus eventos.

    Con el incremento dentro del bucle de eventos, una firma con tres eventos
    gastaba el triple que una con uno, y el «tope de 150» valía 50.
    """
    import inspect

    fuente = inspect.getsource(ent.calcular_lags_anticipacion)
    # El incremento vive FUERA del `for ref in eventos`
    antes, _, despues = fuente.partition("for ref in eventos")
    assert "evaluados[cupo] = evaluados.get(cupo, 0) + 1" in antes, (
        "el presupuesto volvió a gastarse por evento sondeado")
    assert "evaluados[cupo] = evaluados.get(cupo, 0) + 1" not in despues


def test_un_salto_por_TOPE_deja_rastro():
    """Regla dura 10: el `continue` que descarta trabajo lleva cuenta y log."""
    import inspect

    fuente = inspect.getsource(ent.calcular_lags_anticipacion)
    assert "saltadas[cupo]" in fuente, (
        "volvió el `continue` silencioso que esconde 367 firmas sin medir")
    assert "SALTADAS por tope" in fuente
    assert "MORDIÓ" in fuente, "el aviso de tope agotado tiene que gritar"


def test_la_rejilla_mira_POR_DEBAJO_de_24_h():
    """Medido: a 12 h empareja el 65 % y a 1 h el 80 %. Antes se tiraba."""
    assert min(ent.LAG_OFFSETS_H) < 24, (
        f"la rejilla vuelve a parar en {min(ent.LAG_OFFSETS_H)} h: todo lo que "
        "anticipa menos de un día se reporta como «sin anticipación»")
    assert 1 in ent.LAG_OFFSETS_H
    assert 336 in ent.LAG_OFFSETS_H, "se perdió el extremo lejano"
    # y sigue ordenada de lejos a cerca, que es lo que hace que gane el offset
    # MÁS TEMPRANO (el primer emparejamiento)
    assert ent.LAG_OFFSETS_H == sorted(ent.LAG_OFFSETS_H, reverse=True)


def test_el_tope_ya_no_muerde_al_conjunto_exigible():
    """982 exigibles el 8-oct, y el cubo mayor tenía 417.

    El tope existe como malla de seguridad, no como muestreo: si vuelve a
    quedar por debajo del cubo más grande, las firmas que alertan se quedan
    otra vez sin poder decir cuánto anticipan.
    """
    assert ent.LAG_MUESTRA_POR_CLASE >= 1000, (
        f"con {ent.LAG_MUESTRA_POR_CLASE} el tope vuelve a morder")


# ─── MEDIDA SIN ANTICIPACIÓN no es SIN MEDIR ─────────────────────────────────


def test_lag_n_cero_NO_puede_ser_la_marca_de_medido():
    """`lag_n INTEGER DEFAULT 0`: 39.094 filas lo tienen sin haberse medido.

    Lo escribí primero como `lag_n = 0` y no distinguía nada. La marca tiene
    que ser una columna propia, y se añade forward-only (regla 5).
    """
    import inspect

    fuente = inspect.getsource(ent.calcular_lags_anticipacion)
    assert "lag_medido_at" in fuente
    assert "ADD COLUMN lag_medido_at" in fuente, (
        "la columna tiene que crearse sola: la DB de producción ya existe")
    # las dos ramas la escriben: con y sin anticipación
    assert fuente.count("lag_medido_at = datetime('now')") >= 2


def test_los_tres_estados_se_distinguen_en_la_tabla():
    """El contrato de dato, sobre una DB de juguete con el esquema real."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE TBL_FIRMAS (firma_id INTEGER PRIMARY KEY, "
        "lag_promedio_h REAL, lag_n INTEGER DEFAULT 0, lag_medido_at TEXT)")
    conn.executemany(
        "INSERT INTO TBL_FIRMAS (firma_id, lag_promedio_h, lag_n, lag_medido_at)"
        " VALUES (?,?,?,?)",
        [
            (1, 148.7, 3, "2026-10-08 14:23"),   # medida, anticipa
            (2, None, 0, "2026-10-08 14:23"),    # medida, NO anticipa
            (3, None, 0, None),                  # nunca medida
        ])

    def n(where):
        return conn.execute(f"SELECT COUNT(*) FROM TBL_FIRMAS WHERE {where}").fetchone()[0]

    assert n("lag_medido_at IS NOT NULL AND lag_promedio_h IS NOT NULL") == 1
    assert n("lag_medido_at IS NOT NULL AND lag_promedio_h IS NULL") == 1
    assert n("lag_medido_at IS NULL") == 1
    # y la trampa: `lag_n = 0` NO separa la 2 de la 3
    assert n("lag_n = 0") == 2, (
        "si esto cambia, alguien volvió a creer que lag_n distingue")
