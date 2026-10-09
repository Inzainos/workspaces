"""Calibra `SIMILARITY_ALERT` por DIMENSIONALIDAD.

`similitud = 1 - media|Δz|/2` es un PROMEDIO: al crecer las dimensiones el
promedio se concentra (ley de los grandes números) y la distribución de
similitud se angosta alrededor de su centro. Un corte FIJO de 0,80 captura
entonces una cola que se desvanece conforme crecen las dimensiones --- y por eso
el padre, con 42 rasgos, empareja el 0,59 % de las ventanas de evento mientras
beta1, con 21, empareja el 3,9 %.

0,80 sobre 10 dimensiones y 0,80 sobre 42 NO son la misma prueba.

Esto barre el umbral por bot y se queda con el que MAXIMIZA EL LIFT, no el que
empareja más: emparejar más sin discriminar más es alarmismo.

Uso:  .venv/bin/python deploy/calibrar_umbral_similitud.py
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/home/deamon/workspaces")
sys.path.insert(0, "/home/deamon/workspaces/deploy")

from disenar_rasgos_padre import DB, muestras  # noqa: E402

from sentinel_omega.core.firmas.signature_engine import similitud  # noqa: E402
from sentinel_omega.infrastructure.pipeline.entrenamiento import (  # noqa: E402
    BOT_FEATURES,
)
from sentinel_omega.infrastructure.pipeline.mantenimiento import (  # noqa: E402
    conexion_de_lote,
)

UMBRALES = (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)
N_FIRMAS = 120


def main():
    conn = conexion_de_lote(DB)
    v_ev, v_ca = muestras(conn)
    print(f"evento={len(v_ev)} calma={len(v_ca)}")

    for bot in ("padre", "beta1", "alfa1"):
        keys = BOT_FEATURES.get(bot)
        firmas = [json.loads(r[0]) for r in conn.execute(
            "SELECT features_json FROM TBL_FIRMAS WHERE bot_name=? AND "
            "estado='consolidada' ORDER BY RANDOM() LIMIT ?", (bot, N_FIRMAS))]
        if not firmas:
            continue

        # Las similitudes se calculan UNA vez; el barrido es sobre ellas.
        sims_ev, sims_ca = [], []
        dims = 0
        for fi in firmas:
            sf = fi if keys is None else {k: v for k, v in fi.items() if k in keys}
            if len(sf) < 4:
                continue
            dims = max(dims, len(sf))
            for v, acc in ((v_ev, sims_ev), (v_ca, sims_ca)):
                for w in v:
                    sw = w if keys is None else {
                        k: x for k, x in w.items() if k in keys}
                    acc.append(similitud(sw, sf))
        if not sims_ev or not sims_ca:
            continue

        print(f"\n=== {bot} · {dims} dimensiones · {len(firmas)} firmas ===")
        print(f"  {'umbral':>7} {'pe':>8} {'pc':>8} {'LIFT':>8}")
        mejor = None
        for u in UMBRALES:
            pe = sum(1 for s in sims_ev if s >= u) / len(sims_ev)
            pc = sum(1 for s in sims_ca if s >= u) / len(sims_ca)
            lift = (pe + 1 / len(v_ev)) / (pc + 1 / len(v_ca))
            marca = ""
            # Un umbral que no deja NADA no sirve, aunque su lift sea alto.
            if pe >= 0.01 and (mejor is None or lift > mejor[1]):
                mejor, marca = (u, lift), "  <-- mejor con pe>=1%"
            print(f"  {u:7.2f} {pe:8.4f} {pc:8.4f} {lift:7.2f}x{marca}")
        if mejor:
            print(f"  -> {bot}: umbral {mejor[0]:.2f} da lift {mejor[1]:.2f}x")


if __name__ == "__main__":
    main()
