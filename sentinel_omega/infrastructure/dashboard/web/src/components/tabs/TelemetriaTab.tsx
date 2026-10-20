import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Kpi } from "@/components/Kpi";
import { DataTable } from "@/components/DataTable";
import { SimpleBars, LineSpark } from "@/components/charts/Sparkline";

const flareEmoji = (cls: string) => cls === "X" ? "☀️" : cls === "M" ? "☀️" : cls === "C" ? "🌤️" : "";
const flareColor = (cls: string) => cls === "X" ? "red" : cls === "M" ? "orange" : cls === "C" ? "yellow" : "gray";

export function TelemetriaTab() {
  const fetchLatest = useCallback(() => api.telemetry(), []);
  const fetchHistory = useCallback(() => api.telemetryHistory(48), []);

  const latestData = usePoll(fetchLatest, 30000);
  const historyData = usePoll(fetchHistory, 30000);

  const telemetry = latestData.data;
  const history = historyData.data?.history ?? [];

  // GOES X-ray from sources (latest)
  const goesSource = telemetry?.sources?.find((s: any) => s.id === "goes");
  const goesFluxClass = goesSource?.processed?.value?.flux_class ?? "none";
  const goesFluxMax = goesSource?.processed?.value?.flux_max;

  // Alfa-2 thermal from sources (latest)
  const copernicusSource = telemetry?.sources?.find((s: any) => s.id === "copernicus");
  const zonesWithAnomalies = copernicusSource?.processed?.value?.zones_with_anomalies?.length ?? 0;
  const maxAnomalies = copernicusSource?.processed?.value?.zones_with_anomalies?.reduce((m: number, z: any) => Math.max(m, z.thermal_anomalies), 0) ?? 0;

  const kpis = useMemo(() => [
    { label: "Kp", value: telemetry?.latest?.kp?.toFixed(2) ?? "—", color: (telemetry?.latest?.kp ?? 0) > 5 ? "red" : "green" },
    { label: "Schumann (Hz)", value: telemetry?.latest?.schumann?.toFixed(2) ?? "—" },
    { label: "Fase Lunar", value: telemetry?.latest?.lunar_phase?.toFixed(2) ?? "—" },
    { label: "Rotación (ms/día)", value: telemetry?.latest?.rotation?.toFixed(4) ?? "—" },
    { label: "GOES X-ray", value: goesFluxClass !== "none" ? `${flareEmoji(goesFluxClass)} ${goesFluxClass}` : "—", color: goesFluxClass !== "none" ? flareColor(goesFluxClass) : undefined },
    { label: "Alfa-2 Térmico", value: zonesWithAnomalies > 0 ? `${zonesWithAnomalies} zonas` : "NEUTRAL", color: zonesWithAnomalies >= 3 ? "red" : zonesWithAnomalies > 0 ? "orange" : "green" },
  ], [telemetry, goesFluxClass, zonesWithAnomalies]);

  if (latestData.loading && !latestData.data) return <div className="p-4 text-center text-gray-400">Cargando telemetría...</div>;
  if (latestData.error) return <div className="p-4 text-center text-red-400">Error: {String(latestData.error)}</div>;

  return (
    <div className="p-4 space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {kpis.map((k, i) => <Kpi key={i} {...k} />)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-3">Kp — Últimas 48h</h3>
          <LineSpark
            data={history.map(d => ({ key: d.ts, value: d.kp }))}
            xKey="key"
            yKey="value"
            color="#3b82f6"
            height={250}
          />
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-3">Schumann — Últimas 48h</h3>
          <LineSpark
            data={history.map(d => ({ key: d.ts, value: d.schumann }))}
            xKey="key"
            yKey="value"
            color="#10b981"
            height={250}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-3">Fase Lunar — Últimas 48h</h3>
          <LineSpark
            data={history.map(d => ({ key: d.ts, value: d.lunar_phase }))}
            xKey="key"
            yKey="value"
            color="#f59e0b"
            height={250}
          />
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-3">Rotación — Últimas 48h</h3>
          <LineSpark
            data={history.map(d => ({ key: d.ts, value: d.rotation }))}
            xKey="key"
            yKey="value"
            color="#8b5cf6"
            height={250}
          />
        </div>
      </div>

      {/* GOES X-ray history */}
      {history.length > 0 && history[0].goes_flux_max !== undefined && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3">GOES X-ray Flux — Últimas 48h</h3>
            <LineSpark
              data={history.map(d => ({ key: d.ts, value: d.goes_flux_max }))}
              xKey="key"
              yKey="value"
              color="#f97316"
              height={250}
            />
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-white font-semibold mb-3">Alfa-2 Anomalías Térmicas — Últimas 48h</h3>
            <LineSpark
              data={history.map(d => ({ key: d.ts, value: d.alfa2_zones_anom }))}
              xKey="key"
              yKey="value"
              color="#ef4444"
              height={250}
            />
          </div>
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white font-semibold mb-3">Datos Brutos — Últimas 48h</h3>
        <DataTable
          rows={history as Record<string, unknown>[]}
          columns={[
            { key: "ts", label: "Timestamp" },
            { key: "kp", label: "Kp", render: (_, v: unknown) => Number(v).toFixed(2) },
            { key: "schumann", label: "Schumann", render: (_, v: unknown) => Number(v).toFixed(2) },
            { key: "lunar_phase", label: "Fase Lunar", render: (_, v: unknown) => Number(v).toFixed(2) },
            { key: "rotation", label: "Rotación", render: (_, v: unknown) => Number(v).toFixed(4) },
            { key: "goes_flux_max", label: "GOES Flux", render: (_, v: unknown) => v ? Number(v).toExponential(1) : "—" },
            { key: "goes_flux_class", label: "Clase", render: (_, v: unknown) => v ? `${flareEmoji(String(v))} ${v}` : "—" },
            { key: "alfa2_zones_anom", label: "Alfa-2 Zonas", render: (_, v: unknown) => v ? String(v) : "—" },
          ]}
          pageSize={20}
        />
      </div>
    </div>
  );
}