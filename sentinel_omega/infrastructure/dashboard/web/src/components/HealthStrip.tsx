import { useCallback } from "react";
import { api, type Health, type ApiHealth } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { fmtTs } from "@/lib/utils";

export function HealthStrip() {
  const fetcher = useCallback(() => api.health(), []);
  const { data, loading, error } = usePoll<Health>(fetcher, 20000);
  const fuentesFetcher = useCallback(() => api.healthApis(), []);
  const { data: fuentes } = usePoll<ApiHealth>(fuentesFetcher, 60000);

  if (loading && !data) {
    return <div className="rounded-lg border border-border bg-card/40 px-3 py-2 text-xs text-muted">Cargando salud del sistema…</div>;
  }

  if (error) {
    return <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">Health error: {error}</div>;
  }

  const ok = data?.status === "ok" && data?.db_exists;
  return (
    <div className="rounded-lg border border-border bg-card/40 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className={ok ? "text-success" : "text-warning"}>{ok ? "● OK" : "● DEGRADED"}</span>
        <span className="mono text-muted">ciclos: {String(data?.ciclos ?? "—")}</span>
        <span className="mono text-muted">último ciclo: {fmtTs(data?.last_cycle_ts ?? null)}</span>
        <span className="mono text-muted">stale: {String(data?.stale ?? "—")}</span>
        <span className="mono text-muted">db: {data?.db_exists ? "presente" : "faltante"}</span>
      </div>
      {fuentes && Object.keys(fuentes).length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-white/5 pt-2">
          <span className="mono text-[10px] uppercase text-muted">fuentes</span>
          {Object.entries(fuentes).map(([nombre, f]) => {
            const estado = String(f?.status || "").toUpperCase();
            const color =
              estado === "LIVE"
                ? "border-success/40 bg-success/10 text-success"
                : estado === "LOCF_ACTIVE"
                  ? "border-warning/40 bg-warning/10 text-warning"
                  : estado === "STALE"
                    ? "border-danger/40 bg-danger/10 text-danger"
                    : "border-border bg-card/40 text-muted";
            const horas = Number(f?.age_h);
            const edad = Number.isFinite(horas)
              ? horas < 1
                ? `${Math.round(horas * 60)}m`
                : horas < 48
                  ? `${horas.toFixed(1)}h`
                  : `${Math.round(horas / 24)}d`
              : "—";
            return (
              <span
                key={nombre}
                title={`${nombre}: ${estado} · hace ${edad}`}
                className={`mono rounded border px-1.5 py-0.5 text-[10.5px] ${color}`}
              >
                {nombre} · {edad}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
