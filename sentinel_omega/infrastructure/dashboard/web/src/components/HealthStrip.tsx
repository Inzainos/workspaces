import { useCallback } from "react";
import { api, type Health } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { fmtTs } from "@/lib/utils";

export function HealthStrip() {
  const fetcher = useCallback(() => api.health(), []);
  const { data, loading, error } = usePoll<Health>(fetcher, 20000);

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
    </div>
  );
}
