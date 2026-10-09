"""El umbral se defiende MIDIENDO, no copiándolo en un `assert`.

Escrito el 2026-10-09 después de que el operador señalara el patrón exacto:
«todas son mediciones tuyas y todo está documentado por ti, y tú mismo estás
encontrando los mismos defectos que tú mismo dejaste documentados».

Tenía razón, y el caso concreto fue éste. En `mantenimiento.py` vivía una
medición del 26-sep que concluía **«no hay umbral que separe»**, con las
medianas de similitud en 0,877-0,965 para la calma. Se leía como un hecho
vigente. Vuelta a medir el 9-oct, después del rebuild y con la fuga de
procedencia cerrada:

    bot      med EVENTO   med CALMA   p95 calma      (26-sep: calma 0,877-0,965)
    beta1       0,618       0,510       0,691
    padre       0,644       0,603       0,710
    alfa1       0,733       0,733       0,840

Las distribuciones bajaron 0,25-0,35 y **beta1 y el padre sí separan**. La
conclusión de septiembre era verdad sobre SUS datos y dejó de serlo cuando el
rebuild los movió --- y nada avisó, porque era un comentario.

Y el test que supuestamente protegía el umbral era `assert SIMILARITY_ALERT ==
0.8`: una tautología que repite la constante, no detecta nada, y solo se pone
roja cuando alguien la cambia a propósito.

Esto es el reemplazo: **vuelve a medir contra la base de producción** y falla
si el umbral se ha ido del óptimo de lift. Se salta solo cuando no hay base
---CI limpio, `data/` está en `.gitignore` (regla 3)--- en vez de inventar un
veredicto.
"""

from __future__ import annotations

import json
import os
import random
import statistics as st

import pytest

from sentinel_omega.core.firmas.signature_engine import (
    SIMILARITY_ALERT,
    similitud,
)

DB = "sentinel_omega/data/SENTINEL_OMEGA_PRO.db"
N_VENT = 150         # suficiente para la forma de la distribucion
N_FIRMAS = 250      # converge cerca del 4,58x de la poblacion; 25 daba 0,81x
# Candidatos alrededor del vigente. No se buscan todos: se comprueba que
# ninguno de los vecinos sea CLARAMENTE mejor.
VECINOS = (0.65, 0.70, 0.75, 0.80, 0.85)
MARGEN = 1.25        # un vecino tiene que superar al vigente en >25 % de lift


def _muestras(conn, n):
    """Ventanas de evento y de calma del mismo nodo, como en producción."""
    import bisect
    import datetime as dt

    from sentinel_omega.core.firmas.signature_engine import (
        extraer_features_ventana,
    )
    from sentinel_omega.core.shared.geometria_uvg import MATRIZ_UVG_125

    ev = conn.execute(
        "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= 4.5 ORDER BY timestamp_blk").fetchall()
    if not ev:
        return [], []
    por_nodo: dict[int, list] = {}
    for ts, nd in ev:
        por_nodo.setdefault(int(nd), []).append(str(ts))
    horas = [r[0] for r in conn.execute(
        "SELECT timestamp_blk FROM tbl_clima_espacial_raw ORDER BY timestamp_blk")]
    reales = [int(x["id"]) for x in MATRIZ_UVG_125 if x["tipo"] == "real"]
    if not horas or not reales:
        return [], []
    rng = random.Random(29)

    paso = max(1, len(ev) // n)
    v_ev = [f for ts, nd in ev[::paso][:n]
            if (f := extraer_features_ventana(conn, str(ts), int(nd)))]
    v_ca, intentos = [], 0
    while len(v_ca) < n and intentos < 30 * n:
        intentos += 1
        ts = horas[rng.randrange(len(horas))]
        nodo = reales[rng.randrange(len(reales))]
        lista = por_nodo.get(nodo)
        if lista:
            i = bisect.bisect_right(lista, str(ts))
            if i < len(lista):
                try:
                    t = dt.datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                if lista[i] <= (t + dt.timedelta(hours=190)
                                ).strftime("%Y-%m-%d %H:%M"):
                    continue
        f = extraer_features_ventana(conn, str(ts), nodo)
        if f:
            v_ca.append(f)
    return v_ev, v_ca


@pytest.fixture(scope="module")
def similitudes():
    """(sims_evento, sims_calma) del bot con señal, o `skip`."""
    if not os.path.exists(DB):
        pytest.skip(f"sin base de producción en {DB} (regla 3: data/ gitignored)")
    from sentinel_omega.infrastructure.pipeline.mantenimiento import (
        conexion_de_lote,
    )
    from sentinel_omega.infrastructure.pipeline.entrenamiento import BOT_FEATURES

    conn = conexion_de_lote(DB)
    v_ev, v_ca = _muestras(conn, N_VENT)
    if len(v_ev) < 20 or len(v_ca) < 20:
        pytest.skip(f"muestra insuficiente: {len(v_ev)} eventos, {len(v_ca)} calmas")

    # beta1 es el bot con señal medida (AUC 0,800 contra 0,49 del resto): si el
    # umbral se descalibra, se nota aquí primero.
    #
    # ⚠ LA MUESTRA DE FIRMAS NO PUEDE SER «LAS PRIMERAS POR id». La primera
    # versión de este test usaba `ORDER BY firma_id LIMIT 25` y daba lift 0,81x
    # a 0,75, contradiciendo la calibración. Medido las tres formas sobre las
    # MISMAS 250+250 ventanas:
    #
    #     muestra                      n      0,70    0,75    0,80
    #     25 primeras por firma_id     25     1,03x   0,81x   0,52x   <- MENTÍA
    #     120 al azar                 120     4,79x   6,11x   5,04x
    #     TODAS las consolidadas    3.159     4,35x   4,58x   3,17x   <- verdad
    #
    # Las primeras por id son las más viejas del backcast y no representan
    # nada. Se muestrea AL AZAR con semilla fija ---reproducible--- y con n
    # suficiente para converger a la población.
    keys = BOT_FEATURES.get("beta1")
    firmas = [json.loads(r[0]) for r in conn.execute(
        "SELECT features_json FROM TBL_FIRMAS WHERE bot_name='beta1' AND "
        "estado='consolidada' ORDER BY (firma_id * 2654435761) % 1000003 "
        "LIMIT ?", (N_FIRMAS,))]
    if len(firmas) < 100:
        pytest.skip(f"muestra de firmas insuficiente para converger: {len(firmas)}")

    se, sc = [], []
    for fi in firmas:
        sf = fi if keys is None else {k: v for k, v in fi.items() if k in keys}
        if len(sf) < 4:
            continue
        for ventanas, acc in ((v_ev, se), (v_ca, sc)):
            for w in ventanas:
                sw = w if keys is None else {
                    k: x for k, x in w.items() if k in keys}
                acc.append(similitud(sw, sf))
    if not se or not sc:
        pytest.skip("no se pudieron calcular similitudes")
    return se, sc


def _lift(se, sc, u):
    pe = sum(1 for s in se if s >= u) / len(se)
    pc = sum(1 for s in sc if s >= u) / len(sc)
    return (pe + 1 / len(se)) / (pc + 1 / len(sc)), pe, pc


def test_el_umbral_vigente_no_esta_en_la_cola_muerta(similitudes):
    """Que dispare algo. 0,80 dejaba al padre en pe = 0,0049."""
    se, sc = similitudes
    _, pe, _ = _lift(se, sc, SIMILARITY_ALERT)
    assert pe >= 0.02, (
        f"con el umbral en {SIMILARITY_ALERT} solo empareja el {pe:.2%} de las "
        f"ventanas de EVENTO: está en la cola, y una memoria que no se activa "
        f"no puede discriminar. Vuelve a calibrar con "
        f"`deploy/calibrar_umbral_similitud.py`.")


def test_ningun_vecino_es_claramente_mejor(similitudes):
    """El guardia que sustituye al `assert == 0.8`.

    No exige que el vigente sea el óptimo exacto --- la muestra es pequeña y el
    lift se mueve ---, sino que NINGÚN vecino lo supere por más del margen. Si
    esto se pone rojo, los datos se movieron y hay que recalibrar: es la señal
    que faltaba en septiembre, cuando la conclusión «no hay umbral que separe»
    envejeció en un comentario sin que nada avisara.
    """
    se, sc = similitudes
    vigente, _, _ = _lift(se, sc, SIMILARITY_ALERT)
    mejores = []
    for u in VECINOS:
        if abs(u - SIMILARITY_ALERT) < 1e-9:
            continue
        l, pe, _ = _lift(se, sc, u)
        if pe >= 0.02 and l > vigente * MARGEN:
            mejores.append((u, l))
    assert not mejores, (
        f"el umbral vigente ({SIMILARITY_ALERT}) da lift {vigente:.2f}x y hay "
        f"vecinos mejores por más de {MARGEN:.0%}: {mejores}. Los datos se "
        f"movieron --- recalibra con `deploy/calibrar_umbral_similitud.py` y "
        f"actualiza la constante Y su comentario.")


def test_la_distribucion_de_calma_sigue_separada_de_la_de_evento(similitudes):
    """Lo que el comentario del 26-sep daba por imposible.

    Entonces las dos medianas coincidían (0,877-0,965 en calma) y se concluyó
    que ningún umbral separaba. Tras el rebuild, beta1 separa: 0,618 contra
    0,510. Si esto se invierte, la memoria volvió a responder a la calma y el
    umbral es el último de los problemas.
    """
    se, sc = similitudes
    med_ev, med_ca = st.median(se), st.median(sc)
    assert med_ev > med_ca, (
        f"la mediana de similitud en CALMA ({med_ca:.3f}) alcanzó a la de "
        f"EVENTO ({med_ev:.3f}): la memoria responde igual a las dos y "
        f"recalibrar el umbral no lo arregla.")
