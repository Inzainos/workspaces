import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { TabIntro, Caption } from "@/components/TabIntro";
import { LineSpark } from "@/components/charts/Sparkline";
import { Kpi } from "@/components/Kpi";
import { EmptyState } from "@/components/EmptyState";
import { fmtNum } from "@/lib/utils";

export function SenalesTab() {
  const sch = usePoll(useCallback(() => api.schumannVivo(120), []), 30000);
  const clima = usePoll(useCallback(() => api.climaEspacial(80), []), 30000);
  const delta = usePoll(useCallback(() => api.delta(80), []), 30000);
  const ci = usePoll(useCallback(() => api.cimatica(50), []), 40000);
  const ca = usePoll(useCallback(() => api.cimaticaAhora(), []), 40000);

  const schSpark = (sch.data?.items || []).map((r, i) => ({ i, hz: Number(r.schumann_hz ?? 0) }));
  const climaItems = clima.data?.items || [];
  const bzSpark = climaItems.map((r, i) => ({ i, bz: Number(r.bz_promedio ?? 0) }));
  const kpSpark = climaItems.map((r, i) => ({ i, kp: Number(r.kp_promedio ?? r.kp ?? 0) }));
  const deltaSpark = (delta.data?.delta || []).map((r, i) => ({ i, score: Number(r.composite_score ?? 0) }));

  const schLatest = sch.data?.latest as Record<string, unknown> | undefined;
  const caData = (ca.data || {}) as Record<string, unknown>;
  const topPatrones = useMemo(
    () =>
      [...((ci.data?.items || []) as Record<string, unknown>[])]
        .sort((a, b) => Number(b.frecuencia) - Number(a.frecuencia))
        .slice(0, 5),
    [ci.data],
  );
  const maxFreq = Number(topPatrones[0]?.frecuencia ?? 1) || 1;

  return (
    <div className="space-y-6">
      <TabIntro title="Señales — la telemetría cruda que alimenta a los bots">
        <p>
          Todo lo que el sistema mide en vivo, por familia. Fuentes reales (NOAA, USGS, Tomsk, IERS, ESA, Yahoo Finance);
          cuando una fuente cae, el valor queda <b>NULL</b> o se rellena con el último real (LOCF) — nunca se inventa.
        </p>
      </TabIntro>

      {/* Schumann */}
      <div className="rounded-lg border border-border bg-card p-5" style={{ borderColor: "rgba(94,106,210,0.25)" }}>
        <div className="mb-3 flex items-baseline justify-between">
          <div>
            <span className="text-sm font-semibold">Beta-1 · Resonancia Schumann</span>{" "}
            <span className="text-[11px] text-accent">♥ el latido — todo correlaciona contra él</span>
          </div>
          <span className="mono text-[11px] text-muted">fuente: Tomsk · ref 7.83 Hz</span>
        </div>
        <div className="grid items-center gap-5 md:grid-cols-[3fr_1fr]">
          {schSpark.length ? <LineSpark data={schSpark} xKey="i" yKey="hz" height={90} color="#7c86dc" /> : <Caption>Sin serie Schumann viva.</Caption>}
          <div>
            <div className="mono text-2xl">{fmtNum(schLatest?.schumann_hz)} <span className="text-xs text-muted">Hz</span></div>
            <div className="text-[11.5px] text-warning">excitación {fmtNum(schLatest?.schumann_activity, 0)}%</div>
          </div>
        </div>
        <Caption>Excitación &gt;15% suma confianza; &gt;30% con espectro Kp plano dispara WATCH.</Caption>
      </div>

      {/* Space weather + delta */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-3 text-sm font-semibold">Alfa · Clima espacial</div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="mono text-[10px] uppercase text-muted">Bz (GSM)</div>
              {bzSpark.length ? <LineSpark data={bzSpark} xKey="i" yKey="bz" height={52} color="#10b981" /> : null}
            </div>
            <div className="space-y-1.5">
              <div className="mono text-[10px] uppercase text-muted">Kp</div>
              {kpSpark.length ? <LineSpark data={kpSpark} xKey="i" yKey="kp" height={52} color="#ffc107" /> : null}
            </div>
          </div>
          <Caption>Bz negativo (sur) abre la magnetósfera; Kp mide la tormenta geomagnética. Alfa-2 lo valida desde satélite.</Caption>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-3 text-sm font-semibold">Delta · Humor financiero</div>
          <div className="space-y-1.5">
            <div className="mono text-[10px] uppercase text-muted">Cross-coupling (composite)</div>
            {deltaSpark.length ? <LineSpark data={deltaSpark} xKey="i" yKey="score" height={70} color="#7c86dc" /> : <Caption>Sin serie delta.</Caption>}
          </div>
          <Caption>BTC, cripto, VIX y tendencias como una señal precursora más. ALERT si el combinado supera 0.6.</Caption>
        </div>
      </div>

      {/* Cimática */}
      <section className="space-y-2">
        <h4 className="text-sm font-medium">Cimática — las formas del sistema</h4>
        <Caption>
          Cada ciclo toma una "foto" del estado y la convierte en un patrón. Nuevo → se guarda completo; repetido → +1 a su
          frecuencia. Si antecede a un evento real, se etiqueta con su clase.
        </Caption>
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="grid grid-cols-3 gap-3 lg:col-span-2">
            <Kpi label="Patrones (DB)" value={ci.data?.total != null ? Number(ci.data.total).toLocaleString("es-MX") : "—"} hint="tbl_cimatica_patrones" />
            <Kpi label="Biblioteca" value={String(caData.biblioteca_n ?? "—")} hint="figuras históricas" />
            <Kpi label="Hits live" value={String((caData.library as Record<string, unknown> | undefined)?.n_hits ?? caData.hits ?? "—")} hint="similitud" />
            <div className="col-span-3 rounded-lg border border-border bg-card p-4">
              <div className="mb-2 text-[13px] font-semibold">Clave cimática actual</div>
              <div className="mono break-all text-[11px] text-muted">{String(caData.current_clave || "—")}</div>
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="mb-2 flex items-baseline justify-between">
              <span className="text-[13px] font-semibold">Patrones más vistos</span>
              <span className="mono text-[10px] uppercase text-muted">frecuencia</span>
            </div>
            {topPatrones.length ? (
              <div className="space-y-2">
                {topPatrones.map((p, i) => (
                  <div key={i} className="grid grid-cols-[1fr_60px_36px] items-center gap-2">
                    <span className="mono truncate text-[11px]">
                      {String(p.id_nodo ? `n${p.id_nodo}` : "gen")} · {String(p.event_class || "—")}
                    </span>
                    <div className="h-1.5 overflow-hidden rounded-full bg-[#232427]">
                      <div className="h-full bg-accent" style={{ width: `${(Number(p.frecuencia) / maxFreq) * 100}%` }} />
                    </div>
                    <span className="mono text-right text-[10.5px]">{String(p.frecuencia)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Caption>Sin patrones cimáticos aún.</Caption>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
