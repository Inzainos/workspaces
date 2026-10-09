import sys, json, statistics as st
sys.path.insert(0,"/home/deamon/workspaces")
sys.path.insert(0, "/home/deamon/workspaces/deploy")
from disenar_rasgos_padre import muestras, DB, N_FIRMAS, SIMILARITY_ALERT
from sentinel_omega.core.firmas.signature_engine import similitud
from sentinel_omega.infrastructure.pipeline.mantenimiento import conexion_de_lote
conn=conexion_de_lote(DB)
v_ev,v_ca=muestras(conn)
num=lambda x: isinstance(x,(int,float)) and x==x
print("=== ¿cuánta sismicidad PREVIA hay en una ventana de evento? (Omori) ===")
for k in ("sismo_max_mag_win","sismo_count_win","sismo_felt_sum_win","sismo_count_72h"):
    e=[f[k] for f in v_ev if num(f.get(k))]; c=[f[k] for f in v_ca if num(f.get(k))]
    if e and c:
        print(f"  {k:22} evento={st.mean(e):9.3f}  calma={st.mean(c):9.3f}  "
              f"razon={st.mean(e)/(st.mean(c) or 1e-9):6.1f}x")
firmas=[json.loads(r[0]) for r in conn.execute(
  "SELECT features_json FROM TBL_FIRMAS WHERE bot_name='padre' AND estado='consolidada' "
  "ORDER BY RANDOM() LIMIT ?", (N_FIRMAS,))]
# los no-sismicos con poder positivo, medidos antes
CAND=["bz_min","kp_max","lod","densidad_prot_mean","marea_rango_24h","fase_lunar",
      "bz_deriv_std","vix","es_sicigia","bz_mean_72h","marea_deriv","kp_max_72h"]
print("\n=== lift SIN la familia sismo_*_win (solo precursores de verdad) ===")
print(f"  {'K':>3} {'pe':>8} {'pc':>8} {'LIFT':>8}")
for K in (4,6,8,10,12):
    keys=set(CAND[:K]); he=hc=te=tc=0
    for fi in firmas:
        sf={k:v for k,v in fi.items() if k in keys}
        if len(sf)<4: continue
        for w in v_ev:
            te+=1; he += similitud({k:x for k,x in w.items() if k in keys}, sf)>=SIMILARITY_ALERT
        for w in v_ca:
            tc+=1; hc += similitud({k:x for k,x in w.items() if k in keys}, sf)>=SIMILARITY_ALERT
    if not te or not tc: continue
    pe,pc=he/te,hc/tc
    print(f"  {K:3} {pe:8.4f} {pc:8.4f} {(pe+1/len(v_ev))/(pc+1/len(v_ca)):7.2f}x")
