"""La figura, con muestreo EMPAREJADO POR EPOCA. Tercer intento, y el bueno.

Historial de confounds que esto corrige, todos mios:
  v1: ventanas de evento = las primeras que cumplian separacion -> 1994-2003,
      y compartian calendario entre ellas. Dio un 5x falso por fase lunar.
  v2: `usados` compartido -> evento 1994-2008 y calma 2008-2026, EPOCAS
      DISJUNTAS. Cualquier diferencia podia ser ciclo solar, no precursor.
  v3 (esto): cada ventana de evento se EMPAREJA con una de calma a menos de
      180 dias, en otro nodo. Misma epoca, mismo ciclo solar, misma cobertura
      instrumental. Lo unico que cambia es si venia un sismo o no.

Canales: solo clima espacial. Luna y LOD fuera (periodicos -> aliasing); la
familia sismica fuera (Omori); Schumann no existe (880 filas, 76 % iguales).
"""
import sys, sqlite3, random, bisect, datetime as dt, statistics as st
sys.path.insert(0,"/home/deamon/workspaces")
sys.path.insert(0,"/home/deamon/workspaces")
import numpy as np
from sentinel_omega.core.firmas import figura as F
F.CANALES_ASTRO = ()
from sentinel_omega.core.firmas.figura import figura, parecido

DB=sys.argv[1]; SEP_H=672; N=140; HOR=190; EPOCA_D=180
c=sqlite3.connect(f"file:{DB}?mode=ro",uri=True,timeout=30)
ev=c.execute("SELECT timestamp_blk,id_nodo FROM tbl_historico_sismico_raw WHERE sismo_max_mag>=4.5 ORDER BY timestamp_blk").fetchall()
pn={}
for ts,nd in ev: pn.setdefault(int(nd),[]).append(str(ts))
horas=[r[0] for r in c.execute("SELECT timestamp_blk FROM tbl_clima_espacial_raw ORDER BY timestamp_blk")]
hset=[dt.datetime.strptime(str(h)[:16],"%Y-%m-%d %H:%M") for h in horas]
reales=sorted(pn); rng=random.Random(97)

def es_calma(ts_s, nodo, t):
    L=pn.get(nodo)
    if not L: return True
    i=bisect.bisect_right(L, ts_s)
    return not (i<len(L) and L[i] <= (t+dt.timedelta(hours=HOR)).strftime("%Y-%m-%d %H:%M"))

paso=max(1,len(ev)//(N*8))
usados=[]; pares_sel=[]
for ts,nd in ev[::paso]:
    if len(pares_sel)>=N: break
    try: t=dt.datetime.strptime(str(ts)[:16],"%Y-%m-%d %H:%M")
    except ValueError: continue
    if any(abs((t-u).total_seconds())/3600.0<SEP_H for u in usados): continue
    f_ev=figura(c,str(ts),int(nd))
    if sum(1 for v in f_ev.values() if np.any(np.isfinite(v)))<3: continue
    # su pareja de CALMA: misma epoca (+-180 d), otro nodo, sin evento cerca
    pareja=None
    for _ in range(400):
        delta=rng.randint(-EPOCA_D,EPOCA_D)*24 + rng.randint(0,23)
        tt=t+dt.timedelta(hours=delta)
        j=bisect.bisect_left(hset,tt)
        if j>=len(hset): continue
        ts2=str(horas[j]); t2=hset[j]
        nodo2=reales[rng.randrange(len(reales))]
        if nodo2==int(nd): continue
        if abs((t2-t).total_seconds())/3600.0 < SEP_H: continue
        if any(abs((t2-u).total_seconds())/3600.0<SEP_H for u in usados): continue
        if not es_calma(ts2,nodo2,t2): continue
        f_ca=figura(c,ts2,nodo2)
        if sum(1 for v in f_ca.values() if np.any(np.isfinite(v)))<3: continue
        pareja=(t2,f_ca); break
    if pareja is None: continue
    pares_sel.append((t,f_ev,pareja[0],pareja[1]))
    usados += [t, pareja[0]]

te=[p[0] for p in pares_sel]; tc=[p[2] for p in pares_sel]
print(f"parejas emparejadas por epoca: {len(pares_sel)}")
print(f"  EVENTO: {min(te).date()} -> {max(te).date()}")
print(f"  CALMA : {min(tc).date()} -> {max(tc).date()}")
dif=[abs((p[0]-p[2]).days) for p in pares_sel]
print(f"  separacion media dentro de la pareja: {st.mean(dif):.0f} dias (max {max(dif)})")
print(f"  canales: {sorted(pares_sel[0][1])}\n")

EV=[p[1] for p in pares_sel]; CA=[p[3] for p in pares_sel]
def pares(A,B,mismo=False):
    o=[]
    for i,fa in enumerate(A):
        for j,fb in enumerate(B):
            if mismo and j<=i: continue
            p=parecido(fa,fb)
            if p is not None: o.append(p)
    return o
ee=pares(EV,EV,True); ec=pares(EV,CA); cc=pares(CA,CA,True)
def res(v,et):
    s=sorted(v); p=lambda q:s[int(q*(len(s)-1))]
    print(f"  {et:26} n={len(v):6} media={st.mean(v):+.4f} mediana={p(.5):+.4f} p99={p(.99):+.4f}")
    return st.mean(v)
print("=== PARECIDO DE FORMA --- epocas emparejadas, solo clima espacial ===")
a=res(ee,"EVENTO vs EVENTO"); b=res(ec,"evento vs CALMA (nulo)"); d=res(cc,"calma vs calma")
print(f"\n  ev-ev menos ev-calma: {a-b:+.4f}")
print(f"  ev-ev menos ca-ca  : {a-d:+.4f}")
print(f"\n  {'umbral':>7} {'ev-ev':>9} {'ev-calma':>9} {'lift':>8}")
for u in (0.3,0.5,0.7):
    pe=sum(1 for x in ee if x>=u)/len(ee); pc=sum(1 for x in ec if x>=u)/len(ec)
    print(f"  {u:7.2f} {pe:9.4f} {pc:9.4f} {(pe+1e-4)/(pc+1e-4):7.2f}x")
