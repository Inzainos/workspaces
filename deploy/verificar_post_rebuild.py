"""Verificación del estado tras un rebuild, SOBRE POBLACIONES COMPLETAS.

Existe por una razón concreta y nombrada por el operador el 2026-10-09: el
patrón de fallo no era «no mide», era **medir sobre la primera muestra que sale
y no cruzar dos mediciones de lo mismo**. El caso que lo destapó: un test con
`ORDER BY firma_id LIMIT 25` daba lift 0,81x mientras la calibración daba 6,11x,
y la población entera (3.159 firmas) decía 4,58x.

Así que aquí NO hay muestreo. Todo son conteos sobre el total, y donde hay un
cociente va su denominador al lado. Si un número no se puede sacar del total, se
dice que falta en vez de estimarlo.

Uso:  .venv/bin/python deploy/verificar_post_rebuild.py
"""
from __future__ import annotations

import sqlite3
import sys

DB = "/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db"


def seccion(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main() -> int:
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    except sqlite3.Error as exc:
        print(f"no se pudo abrir la base: {exc}")
        return 1
    c.row_factory = sqlite3.Row

    def q(sql, p=()):
        try:
            return c.execute(sql, p).fetchall()
        except sqlite3.Error as exc:
            print(f"  (consulta falló: {exc})")
            return []

    seccion("1. FIRMAS por bot --- TODAS las filas, con denominador")
    print(f"  {'bot':8} {'total':>7} {'consolid.':>10} {'EXIGIBLES':>10} "
          f"{'% de consol.':>13} {'lift medio':>11}")
    for r in q("""SELECT bot_name,
            COUNT(*) tot,
            SUM(estado='consolidada') cons,
            SUM(estado='consolidada' AND COALESCE(exigible,0)=1) exig,
            ROUND(AVG(CASE WHEN COALESCE(exigible,0)=1
                           THEN discrimina_lift END), 2) lift
          FROM TBL_FIRMAS GROUP BY bot_name ORDER BY tot DESC"""):
        pct = (100.0 * r["exig"] / r["cons"]) if r["cons"] else None
        pct_s = f"{pct:12.1f}%" if pct is not None else "           —"
        print(f"  {r['bot_name']:8} {r['tot']:7} {r['cons']:10} {r['exig']:10} "
              f"{pct_s} {str(r['lift'] or '—'):>11}")
    t = q("SELECT COUNT(*) n, SUM(estado='consolidada') c, "
          "SUM(estado='consolidada' AND COALESCE(exigible,0)=1) e FROM TBL_FIRMAS")
    if t:
        print(f"  {'TOTAL':8} {t[0]['n']:7} {t[0]['c']:10} {t[0]['e']:10}")

    seccion("2. SESGO --- la ganancia, y por qué un n=0 es n=0")
    print(f"  {'bot':8} {'n':>5} {'causal':>8} {'falsa_al':>9} {'GANANCIA':>9} "
          f"{'consol. sin exigir':>19}")
    for r in q("SELECT bot, n, recon_causal, falsa_alarma, ganancia, "
               "consolidadas_sin_exigir FROM tbl_sesgo_aprendizaje ORDER BY bot"):
        f = lambda v, d=3: (f"{v:.{d}f}" if isinstance(v, (int, float)) else "—")  # noqa: E731
        print(f"  {r['bot']:8} {r['n'] or 0:5} {f(r['recon_causal']):>8} "
              f"{f(r['falsa_alarma']):>9} {f(r['ganancia']):>9} "
              f"{str(r['consolidadas_sin_exigir'] if r['consolidadas_sin_exigir'] is not None else '—'):>19}")

    seccion("3. LAG --- cobertura y el nulo, sobre las exigibles")
    sys.path.insert(0, "/home/deamon/workspaces")
    try:
        from sentinel_omega.core.firmas.signature_engine import resumen_nulo_lag
        nl = resumen_nulo_lag(c)
    except Exception as exc:
        nl = None
        print(f"  (no se pudo resumir: {exc})")
    if nl:
        print(f"  exigibles                {nl['exigibles']:7}")
        print(f"  con lag                  {nl['con_lag']:7}")
        print(f"  ESPECÍFICAS (anticipan)  {nl['especificas']:7}   "
              f"{nl['pct_especificas']} % de las que tienen lag")
        print(f"  solo persisten           {nl['persisten']:7}")
        print(f"  sin nulo medido          {nl['sin_nulo']:7}")
        print(f"  medidas y sin lag        {nl['medidas_sin_lag']:7}")
    elif nl is None:
        print("  esta base no tiene medido el comparador contra calma")

    seccion("4. VARA DEL JUEZ --- asertividad JUNTO a su ganancia")
    try:
        from sentinel_omega.core.precursor.baseline import evaluar_veredictos
        filas = q("SELECT verdad, resultado FROM viva_real "
                  "WHERE resultado != 'PENDIENTE' AND COALESCE(en_vivo,1)=1")
        m = evaluar_veredictos([(r[0] or "", r[1] or "") for r in filas]) if filas else None
        if m is None:
            print("  sin veredictos cerrados: no hay con qué medir")
        else:
            print(f"  ventanas {m.ventanas} · con evento {m.con_evento} · "
                  f"alarmas {m.alarmas}")
            print(f"  asertividad {m.asertividad * 100:.1f} %  contra  "
                  f"{m.asertividad_muda * 100:.1f} % de un bot MUDO")
            print(f"  GANANCIA {m.ganancia}x  ->  {m.veredicto}")
    except Exception as exc:
        print(f"  (no se pudo evaluar: {exc})")

    seccion("5. MODELOS ONNX --- habilidad medida, no existencia")
    try:
        import json
        from pathlib import Path
        meta = json.loads(
            (Path("/home/deamon/workspaces/sentinel_omega/models")
             / "models_meta.json").read_text())
        comp = meta.get("compuerta") or {}
        print(f"  metadato de {str(meta.get('retrained_at'))[:19]}")
        print(f"  aprueban: {comp.get('aprueban') or 'ninguno'}")
        print(f"  niega:    {comp.get('niega') or '—'}")
        for b, d in (meta.get("bots") or {}).items():
            h = d.get("habilidad") or {}
            auc = h.get("auc")
            print(f"    {b:8} AUC={str(round(auc, 3) if auc else '—'):>6} "
                  f"nulo_nodo={str(round(h['auc_nulo_por_nodo'], 3) if h.get('auc_nulo_por_nodo') else '—'):>6} "
                  f"ganancia={str(round(h['ganancia_sobre_nulo'], 3) if h.get('ganancia_sobre_nulo') is not None else '—'):>7}")
    except Exception as exc:
        print(f"  (sin metadato legible: {exc})")

    seccion("6. INTEGRIDAD y lo que el rebuild debía CONSERVAR")
    print(f"  quick_check: {q('PRAGMA quick_check')[0][0]}")
    for et, sql in (
        ("Juez fase viva (append-only, NO se borra)",
         "SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA WHERE fase='viva'"),
        ("catálogo sísmico (backcast)",
         "SELECT COUNT(*) FROM tbl_historico_sismico_raw"),
        ("clima espacial (backcast)",
         "SELECT COUNT(*) FROM tbl_clima_espacial_raw"),
    ):
        r = q(sql)
        print(f"  {et:45} {r[0][0] if r else '—':>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
