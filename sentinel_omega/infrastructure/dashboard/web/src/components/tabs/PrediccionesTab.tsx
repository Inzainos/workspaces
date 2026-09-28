import { useCallback, useMemo } from "react";
import { api, type Overview } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { SimpleBars } from "@/components/charts/Sparkline";
import { Panel, SinDatos, SegmentosMuro, colorNivel } from "@/components/ui/data";
import { fmtNum } from "@/lib/utils";

/**
 * PREDICCIONES — superficie MONITOR.
 *
 * Tres capas que se leen juntas: qué precursores hay (Scanner), si coinciden
 * dominios distintos (Muro de 5) y cuánto falta (ventana temporal).
 *
 * Nota de diseño: el naranja de "activo" aquí SÍ es riesgo — un precursor
 * encendido es exactamente eso — así que respeta la regla de color. Lo que se
 * quitó fueron los `box-shadow` de neón sobre cada punto, que hacían que 15
 * indicadores apagados compitieran visualmente con los 2 encendidos.
 */
const MUROS: { nombre: string; dominio: string; tipos: string[] }[] = [
  { nombre: "Geofísico", dominio: "corteza", tipos: ["Seismic Cluster", "Volcánico", "Fantasma"] },
  { nombre: "Atmosférico", dominio: "aire", tipos: ["Blue Jet", "Sprite Rojo", "Niebla Tule"] },
  { nombre: "Oceánico", dominio: "agua", tipos: ["Tsunami", "Huracán"] },
  { nombre: "Solar / Geomag.", dominio: "espacio", tipos: ["Silent Trigger", "Tormenta Solar", "Schumann", "GRB"] },
  { nombre: "Financiero", dominio: "humano", tipos: ["Correlación fin."] },
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

  const activos = useMemo(() => {
    const set = new Set<string>();
    for (const p of prec.data || []) {
      const r = p as Record<string, unknown>;
      const t = String(r.tipo || r.precursor_type || "").toUpperCase();
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
  const breach = muroActivos >= 3;
  const mlActivo = ml.data?.activo;
  const rest = ml.data?.dias_restantes;
  const nActivos = SCANNER.filter(isActive).length;

  return (
    <div className="space-y-5">
      {/* ---------- Ventana temporal ---------- */}
      <Panel
        titulo="Ventana temporal · muro de lags"
        meta={mlActivo ? "convergencia activa" : "sin convergencia"}
        acento={mlActivo ? "HIGH" : undefined}
        nota="La ventana se fija en el momento de detectarla y su cuenta baja cada ciclo mientras la señal persista. Se activa cuando 3 o más firmas apuntan a las mismas fechas."
      >
        <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <div>
            <div className="etiqueta">Faltan</div>
            <div
              className="mt-1 text-[length:var(--text-hero-num)] font-bold leading-none tracking-tight tnum"
              style={{ color: mlActivo ? "var(--color-aviso)" : "var(--color-base-600)" }}
            >
              {mlActivo && rest ? `${rest[0]}–${rest[1]}` : "—"}
              <span className="ml-2 text-[0.32em] font-semibold text-faint">días</span>
            </div>
            <p className="mt-2 text-meta leading-snug text-muted">
              {mlActivo
                ? `Persistente hace ${ml.data?.dias_transcurridos ?? 0} días.`
                : "Aparecerá cuando el launcher registre una convergencia persistente."}
            </p>
          </div>

          {mlActivo && ml.data?.fecha_inicio ? (
            <div>
              <div className="relative h-16">
                <div className="absolute inset-x-0 top-8 h-px bg-border-strong" />
                <div
                  className="absolute top-[26px] h-2.5 rounded"
                  style={{
                    left: "38%",
                    width: "52%",
                    background: "var(--color-aviso-dim)",
                    border: "1px solid color-mix(in oklch, var(--color-aviso) 50%, transparent)",
                  }}
                />
                <div className="absolute top-5 h-6 w-0.5 bg-foreground" style={{ left: "22%" }} />
                <div className="absolute top-0 text-micro font-semibold text-foreground" style={{ left: "calc(22% - 10px)" }}>
                  hoy
                </div>
                <div className="mono absolute top-[46px] text-micro" style={{ left: "36%", color: "var(--color-aviso)" }}>
                  {ml.data.fecha_inicio.slice(5)}
                </div>
                <div className="mono absolute top-[46px] text-micro" style={{ left: "82%", color: "var(--color-aviso)" }}>
                  {ml.data.fecha_fin?.slice(5)}
                </div>
              </div>
              <div className="mono mt-2 text-micro" style={{ color: "var(--color-aviso)" }}>
                {(ml.data.clases || []).join(" · ")}
              </div>
            </div>
          ) : (
            <div className="rounded border border-dashed border-border px-4 py-6 text-center text-meta text-faint">
              Sin ventana activa
            </div>
          )}
        </div>
      </Panel>

      {/* ---------- Muro de los 5 ---------- */}
      <Panel
        titulo="Muro de los 5 Eventos"
        meta={`${muroActivos} de 5 · ${breach ? "roto" : "íntegro"}`}
        acento={breach ? "CRITICAL" : muroActivos > 0 ? "MODERATE" : undefined}
        nota="Cinco frentes de dominios físicos distintos. La rotura exige 3 o más a la vez: coincidencia entre dominios que normalmente no se mueven juntos."
      >
        <div className="mb-4">
          <SegmentosMuro activos={muroActivos} total={5} breach={breach} />
        </div>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
          {MUROS.map((m, i) => {
            const active = i < muroActivos;
            return (
              <div
                key={m.nombre}
                className="rounded-lg border bg-surface-sunken/50 p-3.5"
                style={{
                  borderColor: active
                    ? `color-mix(in oklch, ${colorNivel(breach ? "CRITICAL" : "MODERATE")} 45%, transparent)`
                    : "var(--color-border)",
                }}
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-body font-semibold text-foreground">{m.nombre}</div>
                    <div className="etiqueta">{m.dominio}</div>
                  </div>
                  <span
                    className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
                    style={{
                      background: active ? colorNivel(breach ? "CRITICAL" : "MODERATE") : "var(--color-base-700)",
                    }}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  {m.tipos.map((t) => {
                    const on = isActive(t);
                    return (
                      <span
                        key={t}
                        className="mono rounded px-1.5 py-0.5 text-micro"
                        style={{
                          background: on ? "var(--color-aviso-dim)" : "transparent",
                          color: on ? "var(--color-aviso)" : "var(--color-faint)",
                        }}
                      >
                        {t}
                      </span>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* ---------- Scanner ---------- */}
      <Panel
        titulo="Scanner de precursores"
        meta={`${nActivos} activos de ${SCANNER.length}`}
        nota="Un precursor activo no es una predicción: es una condición presente que históricamente apareció antes de eventos fuertes. El consenso lo decide el Padre."
      >
        <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {SCANNER.map((t) => {
            const on = isActive(t);
            return (
              <div
                key={t}
                className="flex items-center gap-2.5 rounded-md border px-3 py-2"
                style={{
                  borderColor: on
                    ? "color-mix(in oklch, var(--color-aviso) 45%, transparent)"
                    : "var(--color-border)",
                  background: on ? "var(--color-aviso-dim)" : "transparent",
                }}
              >
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: on ? "var(--color-aviso)" : "var(--color-base-700)" }}
                />
                <span
                  className="truncate text-meta"
                  style={{
                    color: on ? "var(--color-aviso)" : "var(--color-muted)",
                    fontWeight: on ? 600 : 400,
                  }}
                >
                  {t}
                </span>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* ---------- Anticipación ---------- */}
      <Panel
        titulo="Anticipación — con cuánto tiempo suele avisar"
        meta="medido sobre 32 años"
        nota="Cuántos días antes del evento su firma ya era reconocible. Los eventos mayores avisan con más margen; esto es estadística histórica, no una promesa sobre el próximo."
      >
        {antBars.length ? (
          <>
            <SimpleBars data={antBars} xKey="clase" yKey="dias" color="var(--color-serie-1)" height={190} mostrarX />
            <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 md:grid-cols-3">
              {antBars.map((b) => (
                <li key={b.clase} className="flex items-baseline justify-between gap-2 text-meta">
                  <span className="mono truncate text-muted">{b.clase}</span>
                  <span className="mono shrink-0 tabular-nums text-body">{fmtNum(b.dias, 1)} d</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <SinDatos
            titulo="Sin tbl_lag_anticipacion"
            detalle="Se puebla al entrenar (calcular_lags_anticipacion)."
          />
        )}
      </Panel>
    </div>
  );
}
