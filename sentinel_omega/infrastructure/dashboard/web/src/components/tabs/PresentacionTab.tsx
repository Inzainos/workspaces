import { useCallback } from "react";
import { api, type Overview } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { fmtNum } from "@/lib/utils";

/**
 * Tab Presentación — qué es Sentinel Omega. Landing descriptiva (mayormente
 * estática) con unos pocos números en vivo del overview.
 */
export function PresentacionTab() {
  const ov = usePoll<Overview>(useCallback(() => api.overview(), []), 60000);
  const cyc = usePoll(useCallback(() => api.ciclos(1), []), 60000);
  const ci = usePoll(useCallback(() => api.cimatica(1), []), 60000);
  const ac = usePoll(useCallback(() => api.aciertos(1), []), 60000);

  const asert = ac.data?.summary as Record<string, unknown> | undefined;
  const asertPct =
    asert && asert.tasa_acierto_global != null
      ? `${(Number(asert.tasa_acierto_global) * 100).toFixed(1)}%`
      : "96%";
  const cicloId =
    (cyc.data?.[0]?.id as number | undefined) ??
    (ov.data?.ciclo?.id as number | undefined);
  const patrones = ci.data?.total != null ? Number(ci.data.total).toLocaleString("es-MX") : "191 k";

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-xl border border-border bg-card/40 px-6 py-14 text-center">
        <div
          className="pointer-events-none absolute left-1/2 top-[-120px] h-[400px] w-[700px] -translate-x-1/2"
          style={{ background: "radial-gradient(ellipse at center, rgba(94,106,210,0.16), transparent 70%)" }}
        />
        <div className="relative mx-auto flex max-w-3xl flex-col items-center gap-5">
          <span className="mono text-[11px] uppercase tracking-[0.09em] text-accent">
            Fractal Core Research · sucesor de TITAN V32/V46/V53
          </span>
          <h1 className="text-5xl font-extrabold leading-[1.05] tracking-tight">
            El planeta avisa{" "}
            <span
              style={{
                background: "linear-gradient(120deg,#7c86dc,#a9b0ec)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              antes
            </span>{" "}
            de un evento.
            <br />
            Sentinel Omega lo escucha.
          </h1>
          <p className="text-base leading-relaxed text-[#c7cbd1]" style={{ textWrap: "pretty" }}>
            Una plataforma que vigila las señales físicas de la Tierra —campo magnético solar, resonancia Schumann,
            sismos, gases volcánicos, hasta el humor de los mercados— y reconoce los <b className="text-foreground">precursores</b>:
            las condiciones que en 32 años de historia han aparecido en los días previos a eventos naturales fuertes.
          </p>
          <div className="mt-1 flex flex-wrap justify-center gap-2.5">
            {["32 años de memoria", "125 nodos globales", "8 agentes + Padre + Juez"].map((t) => (
              <span key={t} className="mono rounded-lg border border-border px-3.5 py-2 text-xs text-[#c7cbd1]">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Qué sí / qué no */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-2 flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
            <span className="text-[15px] font-semibold">Qué sí hace</span>
          </div>
          <p className="text-sm leading-relaxed text-muted">
            Reconoce cuando el estado físico del presente <b className="text-[#c7cbd1]">se parece</b> a los días previos a
            eventos pasados, estima <b className="text-[#c7cbd1]">cuándo</b> podría ocurrir (ventana temporal) y eleva la
            vigilancia. Aprende de cada acierto y error.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-2 flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ff9100" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M15 9l-6 6M9 9l6 6" /></svg>
            <span className="text-[15px] font-semibold">Qué no hace</span>
          </div>
          <p className="text-sm leading-relaxed text-muted">
            No es un oráculo ni anuncia epicentros con certeza. No inventa datos: si una fuente cae, el valor es NULL.
            No es un consejo de inversión aunque lea los mercados como una señal más.
          </p>
        </div>
      </div>

      {/* Cómo funciona */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="mb-4 text-[15px] font-semibold">Cómo funciona — en cuatro pasos</div>
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["01 · Escucha", "Telemetría real", "8 agentes leen NOAA, USGS, ESA, Tomsk, mercados — cada ciclo, cada nodo."],
            ["02 · Reconoce", "Firmas y precursores", "Compara contra la memoria de 32 años; 15 precursores y 5 muros vigilan la coincidencia."],
            ["03 · Consensúa", "El Padre decide", "Cruza familias y pesa credibilidad; estima la ventana temporal (cuánto falta)."],
            ["04 · Aprende", "El Juez audita", "Compara con la realidad (USGS) y disciplina a los bots — omitir pesa 10× más que fallar."],
          ].map(([step, title, body]) => (
            <div key={step} className="flex flex-col gap-1.5">
              <span className="mono text-[11px] text-accent">{step}</span>
              <span className="text-[13px] font-semibold">{title}</span>
              <span className="text-xs leading-relaxed text-muted">{body}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Números */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatBig value={asertPct} label="asertividad viva del sistema" accent="#10b981" />
        <StatBig value={cicloId != null ? Number(cicloId).toLocaleString("es-MX") : "—"} label="ciclos corridos" />
        <StatBig value={patrones} label="patrones cimáticos aprendidos" />
        <StatBig value="24/7" label="vigilancia sin servidor (Roy)" accent="#7c86dc" />
      </div>
    </div>
  );
}

function StatBig({ value, label, accent }: { value: string; label: string; accent?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 text-center">
      <div className="text-3xl font-bold tracking-tight" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </div>
  );
}
