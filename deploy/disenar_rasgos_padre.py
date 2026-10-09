"""Diseña por MEDICIÓN el conjunto de rasgos del padre.

El padre no declara rasgos (`BOT_FEATURES["padre"] = None`), así que su firma
lleva el vector completo --- 42 claves --- y al promediar tantas dimensiones la
varianza se encoge: casi nada cruza `SIMILARITY_ALERT = 0,80`. Medido:

    dims  pe       pc       lift
    42    0,0059   0,0011   1,77x      <- hoy
    21    0,0723   0,0097   5,26x      <- sonda con la lista de beta1
    10    0,2025   0,2107   0,96x      <- demasiado pocas: todo se parece

Hay punto óptimo. Este script lo busca con un criterio en la MONEDA QUE USA LA
SIMILITUD (`1 - media|Δz|/2`): por rasgo, cuánto más cerca está de una ventana
de evento que de una de calma. Un rasgo con |Δz| igual en las dos solo añade
ruido al promedio y aplana la distribución.

Uso:  .venv/bin/python <este script>
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import random
import statistics as st
import sys

sys.path.insert(0, "/home/deamon/workspaces")

from sentinel_omega.core.firmas.signature_engine import (  # noqa: E402
    SIMILARITY_ALERT, extraer_features_ventana, similitud,
)
from sentinel_omega.core.shared.geometria_uvg import MATRIZ_UVG_125  # noqa: E402
from sentinel_omega.infrastructure.pipeline.mantenimiento import (  # noqa: E402
    conexion_de_lote,
)

DB = "/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db"
HORIZONTE_H = 190
N_VENT = 250
N_FIRMAS = 120
SEMILLA = 23


def muestras(conn):
    ev = conn.execute(
        "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= 4.5 ORDER BY timestamp_blk").fetchall()
    por_nodo: dict[int, list[str]] = {}
    for ts, nd in ev:
        por_nodo.setdefault(int(nd), []).append(str(ts))
    horas = [r[0] for r in conn.execute(
        "SELECT timestamp_blk FROM tbl_clima_espacial_raw ORDER BY timestamp_blk")]
    reales = [int(n["id"]) for n in MATRIZ_UVG_125 if n["tipo"] == "real"]
    rng = random.Random(SEMILLA)

    paso = max(1, len(ev) // N_VENT)
    v_ev = []
    for ts, nd in ev[::paso][:N_VENT]:
        f = extraer_features_ventana(conn, str(ts), int(nd))
        if f:
            v_ev.append(f)

    v_ca = []
    intentos = 0
    while len(v_ca) < N_VENT and intentos < 20 * N_VENT:
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
                tope = (t + dt.timedelta(hours=HORIZONTE_H)
                        ).strftime("%Y-%m-%d %H:%M")
                if lista[i] <= tope:
                    continue
        f = extraer_features_ventana(conn, str(ts), nodo)
        if f:
            v_ca.append(f)
    return v_ev, v_ca


def main():
    conn = conexion_de_lote(DB)
    v_ev, v_ca = muestras(conn)
    firmas = [json.loads(r[0]) for r in conn.execute(
        "SELECT features_json FROM TBL_FIRMAS WHERE bot_name='padre' "
        "AND estado='consolidada' ORDER BY RANDOM() LIMIT ?", (N_FIRMAS,))]
    print(f"evento={len(v_ev)} calma={len(v_ca)} firmas={len(firmas)}")

    num = lambda x: isinstance(x, (int, float)) and x == x  # noqa: E731
    claves = sorted({k for f in v_ev + v_ca for k, v in f.items() if num(v)})

    # Escala por rasgo: la desviación sobre TODAS las ventanas, que es lo que
    # hace comparable un |Δ| de Bz con uno de conteo sísmico.
    sd = {}
    for k in claves:
        vals = [f[k] for f in v_ev + v_ca if num(f.get(k))]
        sd[k] = (st.pstdev(vals) if len(vals) > 1 else 0.0) or 1.0

    # Por rasgo: media |Δz| firma-vs-evento y firma-vs-calma.
    print("\n=== poder discriminante por rasgo (|Δz| calma − |Δz| evento) ===")
    poder = {}
    for k in claves:
        de, dc = [], []
        for fi in firmas:
            if not num(fi.get(k)):
                continue
            for v, acc in ((v_ev, de), (v_ca, dc)):
                for w in v:
                    if num(w.get(k)):
                        acc.append(abs(fi[k] - w[k]) / sd[k])
        if len(de) < 50 or len(dc) < 50:
            continue
        poder[k] = st.mean(dc) - st.mean(de)

    orden = sorted(poder.items(), key=lambda kv: -kv[1])
    for k, p in orden:
        print(f"  {p:+.4f}  {k}")

    # El conjunto: los K mejores, y se mide el lift que da cada K.
    print("\n=== lift del conjunto segun K (los K mejores rasgos) ===")
    print(f"  {'K':>3} {'pe':>8} {'pc':>8} {'LIFT':>8}")
    mejor = None
    for K in (8, 12, 16, 20, 24, 28, 34):
        keys = {k for k, _ in orden[:K]}
        he = hc = te = tc = 0
        for fi in firmas:
            sf = {k: v for k, v in fi.items() if k in keys}
            if len(sf) < 4:
                continue
            for w in v_ev:
                sw = {k: x for k, x in w.items() if k in keys}
                te += 1
                he += similitud(sw, sf) >= SIMILARITY_ALERT
            for w in v_ca:
                sw = {k: x for k, x in w.items() if k in keys}
                tc += 1
                hc += similitud(sw, sf) >= SIMILARITY_ALERT
        if not te or not tc:
            continue
        pe, pc = he / te, hc / tc
        lift = (pe + 1 / len(v_ev)) / (pc + 1 / len(v_ca))
        marca = ""
        if mejor is None or lift > mejor[1]:
            mejor, marca = (K, lift), "  <-- mejor"
        print(f"  {K:3} {pe:8.4f} {pc:8.4f} {lift:7.2f}x{marca}")

    if mejor:
        K = mejor[0]
        print(f"\n=== los {K} elegidos ===")
        for k, p in orden[:K]:
            print(f'    "{k}",   # {p:+.4f}')


if __name__ == "__main__":
    main()
