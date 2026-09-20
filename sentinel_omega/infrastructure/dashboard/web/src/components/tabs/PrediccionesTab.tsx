import { useCallback, useMemo } from "react";
import { api, type Overview } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { TabIntro, Caption } from "@/components/TabIntro";
import { SimpleBars } from "@/components/charts/Sparkline";
import { EmptyState } from "@/components/EmptyState";
import { fmtNum } from "@/lib/utils";

const MUROS: { nombre: string; tipos: string[] }[] = [
  { nombre: "Geofísico", tipos: ["Seismic Cluster", "Volcánico", "Fantasma"] },
  { nombre: "Atmosférico", tipos: ["Blue Jet", "Sprite Rojo", "Niebla Tule"] },
  { nombre: "Oceánico", tipos: ["Tsunami", "Huracán"] },
  { nombre: "Solar / Geomag.", tipos: ["Silent Trigger", "Tormenta Solar", "Schumann", "GRB"] },
  { nombre: "Financiero", tipos: ["Correlación fin."] },
];
const SCANNER = [
  "Seismic Cluster", "Silent Trigger", "Volcánico", "Tormenta Solar", "Perturbación geomag.",
  "Anomalía Schumann", "Blue Jet", "Sprite Rojo", "Niebla Tule", "Tsunami", "Huracán",
  "GRB", "NEO (asteroides)", "Correlación fin.", "Fantasma alto",
];

export function PrediccionesTab() {
  const ov = usePoll<Overview>(useCallback(() => api.overview(), []), 20000);
  const ml = usePoll(useCallback(() => api.muroLags(), []), 20000);
  const lag = usePoll(useCallback(() => api.lag(), []), 60000);
  const prec = usePoll(useCallback(() => api.precursores(40), []), 20000);

  // precursores activos del ciclo (para encender scanner/muros)
  const activos = useMemo(() => {
    const set = new Set<string>();
    for (const p of prec.data || []) {
      const t = String((p as Record<string, unknown>).tipo || (p as Record<string, unknown>).precursor_type || "").toUpperCase();
      if (t) set.add(t);
    }
    return set;
  }, [prec.data]);
  const isActive = (label: string) => {
    const key = label.toUpperCase().replace(/[^A-Z]/g, "");
    for (const a of activos) if (a.replace(/[^A-Z]/g, "").includes(key.slice(0, 6))) return true;
    return false;
  };

  const anticip = (lag.data?.anticipacion || []) as Record<string, unknown>[];
  const antBars = anticip
    .filter((r) => Number(r.lag_promedio_h) > 0)
    .slice(0, 6)
    .map((r) => ({ clase: String(r.event_class), dias: Number(r.lag_promedio_h) / 24 }));

  const muroActivos = Number(ov.data?.muro?.walls_active ?? 0);
  const mlActivo = ml.data?.activo;
  const rest = ml.data?.dias_restantes;

  return (
    <div className="space-y-6">
      <TabIntro title="Predicciones — de los precursores al evento">
        <p>
          El corazón del sistema. Sentinel <b>no anuncia epicentros</b>: reconoce cuando el estado físico se parece a los
          días previos a un evento fuerte y estima <b>cuándo</b> podría ocurrir. Se leen juntas tres capas — el{" "}
          <b>Scanner</b> (¿qué precursores hay?), el <b>Muro de los 5</b> (¿coinciden dominios?) y la{" "}
          <b>Ventana temporal</b> (¿cuánto falta?).
        </p>
      </TabIntro>

      {/* Ventana temporal / countdown */}
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="flex items-start justify-between border-b border-white/5 px-6 py-5">
          <div className="flex items-center gap-3.5">
            <div className="grid h-10 w-10 place-items-center rounded-lg" style={{ background: "rgba(94,106,210,0.16)" }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c86dc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[15px] font-semibold">Ventana temporal activa · muro de lags</span>
              <span className="text-[12.5px] text-muted">
                {mlActivo
                  ? `Firmas convergen en las mismas fechas · persistente hace ${ml.data?.dias_transcurridos ?? 0} días`
                  : "Sin convergencia activa ahora — se activa cuando ≥3 firmas apuntan a las mismas fechas"}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="mono text-[11px] uppercase tracking-wide text-muted">faltan</div>
            <div className="text-[32px] font-bold leading-none text-accent">
              {mlActivo && rest ? `${rest[0]}–${rest[1]}` : "—"}{" "}
              <span className="text-base font-semibold text-muted">días</span>
            </div>
          </div>
        </div>
        {mlActivo && ml.data?.fecha_inicio ? (
          <div className="px-6 py-4">
            <div className="relative mx-2 h-14">
              <div className="absolute left-0 right-0 top-7 h-[3px] rounded bg-[#232427]" />
              <div className="absolute top-6 h-2.5 rounded-md" style={{ left: "38%", width: "52%", background: "linear-gradient(90deg, rgba(124,134,220,0.5), rgba(124,134,220,0.15))", border: "1px solid rgba(124,134,220,0.5)" }} />
              <div className="absolute top-5 h-6 w-[2px] bg-foreground" style={{ left: "22%" }} />
              <div className="absolute top-0 text-[11px] font-semibold" style={{ left: "calc(22% - 8px)" }}>hoy</div>
              <div className="mono absolute top-11 text-[10.5px] text-accent" style={{ left: "36%" }}>{ml.data.fecha_inicio.slice(5)}</div>
              <div className="mono absolute top-11 text-[10.5px] text-accent" style={{ left: "84%" }}>{ml.data.fecha_fin?.slice(5)}</div>
            </div>
            <div className="mt-2 flex justify-between text-xs text-muted">
              <span>La ventana se <b className="text-[#c7cbd1]">fijó al detectarla</b> y baja cada ciclo mientras la señal persiste.</span>
              <span className="mono text-accent">{(ml.data.clases || []).join(" · ")}</span>
            </div>
          </div>
        ) : (
          <div className="px-6 py-5">
            <Caption>La ventana temporal aparecerá aquí cuando el launcher registre una convergencia persistente.</Caption>
          </div>
        )}
      </div>

      {/* Muro de los 5 */}
      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h4 className="text-sm font-medium">Muro de los 5 Eventos</h4>
          <span className="text-[12.5px] font-semibold" style={{ color: muroActivos >= 3 ? "#ff1744" : "#ff9100" }}>
            {muroActivos} / 5 activos {muroActivos >= 3 ? "· BREACH" : "· sin rotura"}
          </span>
        </div>
        <Caption>Cinco frentes de dominios físicos distintos. Rotura cuando 3 o más se activan a la vez.</Caption>
        <div className="grid gap-3 md:grid-cols-5">
          {MUROS.map((m, i) => {
            const active = i < muroActivos;
            return (
              <div key={m.nombre} className="rounded-lg border bg-card p-3.5" style={{ borderColor: active ? "rgba(255,145,0,0.35)" : "rgba(255,255,255,0.08)" }}>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[12.5px] font-semibold">{m.nombre}</span>
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: active ? "#ff9100" : "#2f3033", boxShadow: active ? "0 0 8px #ff9100" : "none" }} />
                </div>
                <div className="flex flex-col gap-1">
                  {m.tipos.map((t) => (
                    <span key={t} className="mono rounded px-1.5 py-0.5 text-[10px]" style={{ background: isActive(t) ? "rgba(255,145,0,0.14)" : "rgba(255,255,255,0.05)", color: isActive(t) ? "#ff9100" : "#8a8f98" }}>{t}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Scanner */}
      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h4 className="text-sm font-medium">Scanner de precursores</h4>
          <span className="mono text-[11px] uppercase text-muted">15 tipos vigilados</span>
        </div>
        <div className="grid gap-2.5 md:grid-cols-5">
          {SCANNER.map((t) => {
            const on = isActive(t);
            return (
              <div key={t} className="flex items-center gap-2.5 rounded-lg border bg-card px-3 py-2.5" style={{ borderColor: on ? "rgba(255,145,0,0.35)" : "rgba(255,255,255,0.08)" }}>
                <span className="h-2 w-2 rounded-full" style={{ background: on ? "#ff9100" : "#2f3033", boxShadow: on ? "0 0 6px #ff9100" : "none" }} />
                <span className="text-xs" style={{ color: on ? "#f7f8f8" : "#8a8f98", fontWeight: on ? 500 : 400 }}>{t}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Anticipación */}
      <section className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h4 className="text-sm font-medium">Anticipación — con cuánto tiempo suele avisar</h4>
          <span className="mono text-[11px] uppercase text-muted">medido sobre 32 años</span>
        </div>
        <Caption>
          ¿Cuántos días <b>antes</b> del evento ya era reconocible su firma? Los eventos más grandes avisan con más tiempo.
        </Caption>
        {antBars.length ? (
          <div className="rounded-lg border border-border bg-card p-4">
            <SimpleBars data={antBars} xKey="clase" yKey="dias" color="#5e6ad2" height={180} />
            <div className="mt-2 grid grid-cols-2 gap-1 md:grid-cols-3">
              {antBars.map((b) => (
                <span key={b.clase} className="mono text-[11px] text-muted">
                  {b.clase}: <span className="text-foreground">{fmtNum(b.dias, 1)} d</span>
                </span>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState title="Sin tbl_lag_anticipacion" detail="Se puebla al entrenar (calcular_lags_anticipacion)." />
        )}
      </section>
    </div>
  );
}
