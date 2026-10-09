"""¿El LATIDO cambia antes de un sismo? La medicion que nunca se pudo hacer.

Por que no se pudo antes
------------------------
La resonancia Schumann es el eje del proyecto y hasta el 2026-10-09 no estaba
medida: `schumann_hz` era `7,83 + actividad x 0,02` ---una recta sobre un conteo
de pixeles--- con la misma actividad en 564 de 743 filas. De 4.000 firmas solo
86 (2,2 %) llevaban el rasgo, con un recorrido de **0,03 Hz**. No habia señal
que medir.

Con la estacion ELF de Sierra Nevada (UGR) hay 2013-03 a 2017-02 de parametros
lorentzianos cada 10 minutos: **SR1 recorre 1,04 Hz en un solo dia**.

Lo que mide esto, y los controles
---------------------------------
Para cada sismo M4.5+ en el periodo con Schumann, la ventana de 336 h ANTERIOR;
y para cada una, una ventana de CALMA **emparejada por epoca** (a menos de 180
dias, otro nodo, sin evento en el horizonte). Los controles son los que me
costaron tres intentos en la medicion de figuras:

  * EPOCA emparejada: sin esto, evento y calma caen en periodos distintos y la
    diferencia puede ser ciclo solar o cambio de instrumento.
  * Canales SIN la familia sismica: el historial del nodo es Omori, no
    precursor, y ya se midio que da 30-75x por si solo.
  * Luna y LOD fuera: periodicos -> aliasing de calendario. Y medido sobre los
    184.330 eventos del catalogo, la fase lunar se reparte 9,8-10,1 % por
    decil, igual que todas las horas: no hay agrupamiento lunar.

Se miden DOS cosas distintas, porque no son la misma pregunta:

  1. NIVEL: ¿la frecuencia/amplitud/Q media de la ventana difiere?
  2. FORMA: ¿la curva de 336 h se parece mas entre eventos que contra calma?

Uso:  .venv/bin/python deploy/medir_schumann_precursor.py <db> [<db_schumann>]
"""
from __future__ import annotations

import bisect
import datetime as dt
import random
import sqlite3
import statistics as st
import sys

import numpy as np

sys.path.insert(0, "/home/deamon/workspaces")

from sentinel_omega.infrastructure.api.schumann_granada import TABLA  # noqa: E402

VENTANA_H = 336
HORIZONTE_H = 190
EPOCA_D = 180
N_BINS = 48
SEP_H = 672
CANALES = ("sr1_hz", "sr2_hz", "sr3_hz", "sr1_amp", "sr1_q")


def _znorm(c):
    m, s = np.nanmean(c), np.nanstd(c)
    if not np.isfinite(m) or not np.isfinite(s) or s < 1e-12:
        return np.full_like(c, np.nan)
    return (c - m) / s


def serie(conn_s, ts_fin: str):
    """{canal: (curva z-normalizada, media cruda)} de la ventana, o None."""
    ini = (dt.datetime.strptime(ts_fin[:16], "%Y-%m-%d %H:%M")
           - dt.timedelta(hours=VENTANA_H)).strftime("%Y-%m-%d %H:%M")
    cols = ", ".join(CANALES)
    filas = conn_s.execute(
        f"SELECT ts, {cols} FROM {TABLA} WHERE ts >= ? AND ts < ? "
        "ORDER BY ts", (ini, ts_fin[:16])).fetchall()
    if len(filas) < N_BINS:            # menos de un punto por bin: no hay curva
        return None
    t0 = dt.datetime.strptime(ini, "%Y-%m-%d %H:%M")
    ancho = VENTANA_H / N_BINS
    out = {}
    for j, canal in enumerate(CANALES, start=1):
        acc = [[] for _ in range(N_BINS)]
        for r in filas:
            v = r[j]
            if v is None:
                continue
            h = (dt.datetime.strptime(str(r[0])[:16], "%Y-%m-%d %H:%M")
                 - t0).total_seconds() / 3600.0
            i = int(h / ancho)
            if 0 <= i < N_BINS:
                acc[i].append(float(v))
        curva = np.array([(sum(a) / len(a)) if a else np.nan for a in acc])
        if np.sum(np.isfinite(curva)) < N_BINS // 2:
            continue                   # mas de la mitad sin dato: se omite
        out[canal] = (_znorm(curva), float(np.nanmean(curva)))
    return out or None


def parecido(a, b):
    rs = []
    for canal in set(a) & set(b):
        x, y = a[canal][0], b[canal][0]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < N_BINS // 3:
            continue
        xv, yv = x[m], y[m]
        if np.std(xv) < 1e-12 or np.std(yv) < 1e-12:
            continue
        r = float(np.corrcoef(xv, yv)[0, 1])
        if np.isfinite(r):
            rs.append(r)
    return float(np.mean(rs)) if rs else None


def main():
    db = sys.argv[1]
    db_s = sys.argv[2] if len(sys.argv) > 2 else db
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
    cs = sqlite3.connect(f"file:{db_s}?mode=ro", uri=True, timeout=30)

    rango = cs.execute(f"SELECT MIN(ts), MAX(ts), COUNT(*) FROM {TABLA}").fetchone()
    if not rango or not rango[0]:
        print("sin datos de Schumann: nada que medir")
        return 1
    print(f"Schumann: {rango[2]:,} intervalos, {rango[0][:10]} -> {rango[1][:10]}")

    ev = c.execute(
        "SELECT timestamp_blk, id_nodo FROM tbl_historico_sismico_raw "
        "WHERE sismo_max_mag >= 4.5 AND timestamp_blk >= ? AND timestamp_blk <= ? "
        "ORDER BY timestamp_blk", (rango[0][:16], rango[1][:16])).fetchall()
    print(f"eventos M4.5+ dentro del periodo: {len(ev):,}")
    if not ev:
        print("sin eventos en el periodo con Schumann")
        return 1

    por_nodo = {}
    for ts, nd in ev:
        por_nodo.setdefault(int(nd), []).append(str(ts))
    horas = [r[0] for r in c.execute(
        "SELECT timestamp_blk FROM tbl_clima_espacial_raw WHERE "
        "timestamp_blk >= ? AND timestamp_blk <= ? ORDER BY timestamp_blk",
        (rango[0][:16], rango[1][:16]))]
    reales = sorted(por_nodo)
    rng = random.Random(53)

    def es_calma(ts_s, nodo, t):
        L = por_nodo.get(nodo)
        if not L:
            return True
        i = bisect.bisect_right(L, ts_s)
        return not (i < len(L) and L[i] <= (t + dt.timedelta(hours=HORIZONTE_H)
                                            ).strftime("%Y-%m-%d %H:%M"))

    usados, parejas = [], []
    paso = max(1, len(ev) // 600)
    for ts, nd in ev[::paso]:
        try:
            t = dt.datetime.strptime(str(ts)[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if any(abs((t - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
            continue
        f_ev = serie(cs, str(ts))
        if f_ev is None:
            continue
        pareja = None
        for _ in range(500):
            tt = t + dt.timedelta(hours=rng.randint(-EPOCA_D, EPOCA_D) * 24)
            j = bisect.bisect_left(horas, tt.strftime("%Y-%m-%d %H:%M"))
            if j >= len(horas):
                continue
            ts2, nodo2 = str(horas[j]), reales[rng.randrange(len(reales))]
            t2 = dt.datetime.strptime(ts2[:16], "%Y-%m-%d %H:%M")
            if nodo2 == int(nd) or abs((t2 - t).total_seconds()) / 3600.0 < SEP_H:
                continue
            if any(abs((t2 - u).total_seconds()) / 3600.0 < SEP_H for u in usados):
                continue
            if not es_calma(ts2, nodo2, t2):
                continue
            f_ca = serie(cs, ts2)
            if f_ca is None:
                continue
            pareja = (t2, f_ca)
            break
        if pareja is None:
            continue
        parejas.append((t, f_ev, pareja[0], pareja[1]))
        usados += [t, pareja[0]]

    if len(parejas) < 10:
        print(f"\nsolo {len(parejas)} parejas con Schumann en ambas ventanas: "
              f"muestra insuficiente para concluir. No se inventa un veredicto.")
        return 1

    te = [p[0] for p in parejas]
    print(f"\nparejas emparejadas por epoca: {len(parejas)} "
          f"({min(te).date()} -> {max(te).date()})")
    print(f"canales con curva: {sorted(parejas[0][1])}")

    # ── 1. NIVEL ────────────────────────────────────────────────────────────
    print("\n=== 1. NIVEL: la media de la ventana difiere? ===")
    print(f"  {'canal':10} {'evento':>12} {'calma':>12} {'dif':>10} {'dif/sd':>8}")
    for canal in CANALES:
        a = [p[1][canal][1] for p in parejas if canal in p[1]]
        b = [p[3][canal][1] for p in parejas if canal in p[3]]
        if len(a) < 10 or len(b) < 10:
            print(f"  {canal:10} muestra insuficiente ({len(a)}/{len(b)})")
            continue
        d = st.mean(a) - st.mean(b)
        sd = st.pstdev(a + b) or 1e-12
        print(f"  {canal:10} {st.mean(a):12.4f} {st.mean(b):12.4f} "
              f"{d:+10.4f} {d / sd:+8.3f}")
    print("  (dif/sd es el tamano del efecto: |0,2| chico, |0,5| medio)")

    # ── 2. FORMA ────────────────────────────────────────────────────────────
    EV = [p[1] for p in parejas]
    CA = [p[3] for p in parejas]

    def pares(A, B, mismo=False):
        o = []
        for i, fa in enumerate(A):
            for j, fb in enumerate(B):
                if mismo and j <= i:
                    continue
                p = parecido(fa, fb)
                if p is not None:
                    o.append(p)
        return o

    ee, ec, cc = pares(EV, EV, True), pares(EV, CA), pares(CA, CA, True)
    print("\n=== 2. FORMA: la curva se repite entre eventos? ===")
    for v, et in ((ee, "EVENTO vs EVENTO"), (ec, "evento vs CALMA (nulo)"),
                  (cc, "calma  vs calma")):
        if not v:
            print(f"  {et}: sin pares")
            continue
        s = sorted(v)
        print(f"  {et:26} n={len(v):6} media={st.mean(v):+.4f} "
              f"mediana={s[len(s) // 2]:+.4f} p99={s[int(.99 * (len(s) - 1))]:+.4f}")
    if ee and ec:
        print(f"\n  ev-ev menos ev-calma: {st.mean(ee) - st.mean(ec):+.4f}")
        print(f"  {'umbral':>7} {'ev-ev':>9} {'ev-calma':>9} {'lift':>8}")
        for u in (0.3, 0.5, 0.7):
            pe = sum(1 for x in ee if x >= u) / len(ee)
            pc = sum(1 for x in ec if x >= u) / len(ec)
            print(f"  {u:7.2f} {pe:9.4f} {pc:9.4f} "
                  f"{(pe + 1e-4) / (pc + 1e-4):7.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
