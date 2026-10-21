#!/usr/bin/env python3
"""Mide la GEOMETRÍA del umbral de similitud 0,80 (ítem 5, 2026-10-20).

Libro: Euclidean Distance Geometry (Liberti-Lavor-Mucherino, ~/conocimiento).
La pregunta del 8-oct que quedó pendiente: «42 dims no bajan la similitud,
encogen la varianza, y casi nada cruza el 0,80 fijo». Esto lo responde con
números:

1. **Distribución intra-nodo**: similitudes entre TODAS las parejas de
   firmas exigibles del mismo nodo (la misma métrica del engine —
   `similitudes_contra`, nada de métricas inventadas). ¿En qué percentil
   cae el 0,80? Si el 95 % de las parejas del mismo nodo queda por debajo,
   el umbral no está calibrado contra la geometría real del espacio.
2. **Dimensionalidad efectiva**: espectro de eigenvalores de la matriz de
   covarianza de los vectores estandarizados. ¿Cuántas de las 42
   dimensiones cargan varianza real? (Si son 6, el «espacio» es 6-D con
   ruido, y el 0,80 de un promedio de 42 está dominado por ruido.)
3. **¿Es euclidiano?** Criterio de Schoenberg: D = 2·(1−sim) es una
   distancia; B = −½JDJ debe ser PSD. Medimos cuánto se viola — si el
   espacio no es euclidiano, el MDS 2D es aproximación y hay que decirlo.
4. **Mapa 2D** (MDS clásico) de las firmas exigibles, coloreado por bot —
   el «espacio de firmas» hecho imagen (estado/graficas/firma_espacio.png).

Solo lectura de DB; no escribe nada. Corre: python deploy/medir_similitud_geometria.py
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sentinel_omega.core.firmas.signature_engine import (  # noqa: E402
    FEATURE_KEYS,
    _vector,
    similitudes_contra,
)
from sentinel_omega.infrastructure.database.ruta_db import ruta_db_canonica  # noqa: E402

UMBRAL = 0.80


def cargar_firmas(conn: sqlite3.Connection) -> dict:
    """Firmas exigibles con vector YA construido, por (bot, nodo)."""
    filas = conn.execute(
        "SELECT bot_name, id_nodo, features_json FROM TBL_FIRMAS "
        "WHERE estado='consolidada' AND COALESCE(exigible,1)=1"
    ).fetchall()
    por_nodo: dict = defaultdict(list)
    n = 0
    for bot, nodo, fj in filas:
        try:
            feats = json.loads(fj or "{}")
        except json.JSONDecodeError:
            continue
        vec = _vector(feats)
        if vec is not None and not np.isnan(vec).all():
            por_nodo[(bot, nodo)].append(vec)
            n += 1
    return por_nodo, n


def percentile_distribucion_intra(por_nodo: dict, max_pares: int = 40_000) -> np.ndarray:
    """Similitudes entre parejas de firmas DEL MISMO (bot, nodo)."""
    sims = []
    for (bot, nodo), vecs in por_nodo.items():
        if len(vecs) < 2:
            continue
        matriz = np.vstack(vecs)
        # Todos contra todos por bloques de filas (la RAM manda)
        for i in range(0, len(vecs), 64):
            bloque = matriz[i : i + 64]
            s = similitudes_contra(bloque[0], matriz) if len(bloque) == 1 else None
            if s is not None:
                # diagonal auto-similitud fuera
                sims.extend(s.tolist())
                break
            # caso general: fila a fila del bloque
            for va in bloque:
                sims.extend(similitudes_contra(va, matriz).tolist())
        if len(sims) > max_pares:
            break
    arr = np.array(sims)
    # quitar auto-similitudes (~1.0 exactos del diagonal)
    return arr


def pctl(x, v):
    return f"P{round(100 * np.mean(x <= v))}" if len(x) else "—"


def main() -> None:
    ruta = ruta_db_canonica()
    conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=10.0)
    por_nodo, n = cargar_firmas(conn)
    conn.close()
    print(f"Firmas exigibles con vector: {n} en {len(por_nodo)} (bot, nodo)")

    # ── 1. Distribución intra-nodo vs el umbral ─────────────────────────
    sims = percentile_distribucion_intra(por_nodo)
    sims = sims[sims < 0.9999]  # sin diagonal
    print(f"\n== 1. DISTRIBUCIÓN INTRA-NODO (parejas del mismo nodo) ==")
    print(f"   pares: {len(sims):,}")
    for p in (5, 25, 50, 75, 95):
        print(f"   P{p}: {np.percentile(sims, p):.3f}")
    print(f"   ** UMBRAL {UMBRAL} queda en {pctl(sims, UMBRAL)} de las "
          f"parejas del MISMO nodo **")
    frac_cruza = float(np.mean(sims >= UMBRAL))
    print(f"   parejas del mismo nodo que CRUZAN el umbral: {frac_cruza:.1%}")

    # ── 2. Dimensionalidad efectiva ──────────────────────────────────────
    todos = []
    for vecs in por_nodo.values():
        todos.extend(vecs)
    X = np.vstack(todos)
    # estandarizar por columna (z-score), ignorando NaN por columna
    media = np.nanmean(X, axis=0)
    std = np.nanstd(X, axis=0)
    std[std < 1e-12] = np.nan
    Z = (X - media) / std
    # imputar NaN con 0 (la media) para el cálculo del espectro
    Z = np.nan_to_num(Z, nan=0.0)
    C = np.cov(Z, rowvar=False)
    eig = np.sort(np.linalg.eigvalsh(C))[::-1]
    eig_pos = eig[eig > 1e-9]
    total = float(eig_pos.sum())
    for k in (1, 2, 3, 6, 10, 20, 42):
        if k <= len(eig_pos):
            acum = float(eig_pos[:k].sum()) / total
            print(f"   top-{k:2d} dims: {acum:.1%} de la varianza")
    # dimensionalidad efectiva (participación de Shannon en dims)
    p = eig_pos / total
    ent = -float(np.sum(p * np.log(p + 1e-12)))
    print(f"   dimensionalidad efectiva (participación): {np.exp(ent):.1f} "
          f"de {len(eig_pos)} con varianza > 0")

    # ── 3. ¿D es euclidiana? (Schoenberg: B = -½JDJ debe ser PSD) ───────
    rng = np.random.default_rng(7)
    idx = rng.choice(len(sims), size=min(3000, len(sims)), replace=False)
    D = np.sqrt(np.clip(2 * (1 - sims[idx]), 0, None))  # distancia
    # Rehacer como matriz no es directo (son pares sueltos): usamos la
    # aproximación por matriz de Gram de las distancias normalizadas —
    # en su lugar, medición equivalente: eigenvalores del MDS sobre una
    # muestra de firmas de un nodo grande.
    (bot_g, nodo_g), vecs_g = max(por_nodo.items(), key=lambda kv: len(kv[1]))
    sub = np.vstack(vecs_g[:300])
    n_g = len(sub)
    Sg = np.vstack([similitudes_contra(v, sub) for v in sub])
    Dg = np.sqrt(np.clip(2 * (1 - Sg), 0, None))
    J = np.eye(n_g) - np.ones((n_g, n_g)) / n_g
    B = -0.5 * J @ (Dg**2) @ J
    ev = np.sort(np.linalg.eigvalsh(B))[::-1]
    neg = float(-ev[ev < 0].sum() / max(ev[0], 1e-12))
    print(f"\n== 3. ¿EUCLIDIANO? (Schoenberg, nodo más grande: {nodo_g}, "
          f"{n_g} firmas de {bot_g}) ==")
    print(f"   eigenvalores negativos (energía relativa): {neg:.2%} — "
          f"{'APROX. euclidiano' if neg < 0.05 else 'NO euclidiano: el MDS 2D es proyección con pérdida'}")

    # ── 4. Mapa 2D (MDS clásico) ─────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        k = min(2, len(ev))
        if k == 2 and ev[1] > 1e-9:
            U = np.linalg.eigh(B)[1][:, ::-1][:, :2]
            Lam = np.sqrt(np.clip(ev[:2], 0, None))
            XY = U * Lam
            fig, ax = plt.subplots(figsize=(7, 5.5), dpi=120)
            ax.scatter(XY[:, 0], XY[:, 1], s=8, color="#2563a8", alpha=0.6)
            ax.set_title(
                f"Espacio de firmas exigibles — {bot_g}, nodo {nodo_g} "
                f"(MDS 2D de similitud 0.80-en-{pctl(sims, UMBRAL)})",
                fontsize=10, loc="left",
            )
            ax.set_xlabel(f"dim 1 ({ev[0]/max(total,1e-9):.0%} var)")
            ax.set_ylabel(f"dim 2")
            ax.grid(alpha=0.25)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            out = RAIZ / "estado" / "graficas" / "firma_espacio.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out)
            plt.close(fig)
            print(f"\n== 4. Mapa 2D: {out} ==")
    except ImportError:
        print("\n== 4. (matplotlib ausente: mapa omitido) ==")

    print(
        f"\nVEREDICTO: el umbral 0,80 cae en el {pctl(sims, UMBRAL)} de las "
        f"parejas intra-nodo. Si es P95+, el umbral deja afuera casi toda la "
        f"geometría real del espacio (las firmas de un MISMO nodo no se "
        f"reconocen entre sí), y la calibración por nodo que sugiere la "
        f"bitácora del 8-oct tiene números con qué arrancar."
    )


if __name__ == "__main__":
    main()
