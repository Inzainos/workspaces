import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Kpi } from "@/components/Kpi";
import { fmtNum } from "@/lib/utils";

export function TelemetryStrip() {
  const fetcher = useCallback(() => api.telemetry(), []);
  const { data, loading, error } = usePoll(fetcher, 25000);

  if (loading && !data) {
    return <div className="text-xs text-muted">Cargando telemetría…</div>;
  }

  if (error) {
    return <div className="text-xs text-warning">Telemetría no disponible: {error}</div>;
  }

  const ciclo = data?.ciclo || {};
  const precursor = data?.precursor || {};

  return (
    <div className="grid gap-3 md:grid-cols-4">
      <Kpi label="SEÑAL GEO" value={String(ciclo.geo_signal ?? "—")} hint="del último ciclo" />
      <Kpi label="CONF" value={fmtNum(ciclo.geo_confidence)} hint="confianza consenso" />
      <Kpi label="LOCF CACHE" value={String(data?.locf_cache_n ?? "—")} hint="filas persistentes" />
      <Kpi label="FANTASMA" value={fmtNum(precursor.fantasma ?? ciclo.fantasma)} hint="telemetría rápida" />
    </div>
  );
}
