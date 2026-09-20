import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Map2D } from "@/components/maps/Map2D";
import { Globe3D } from "@/components/maps/Globe3D";
import { TabIntro, Caption } from "@/components/TabIntro";

/** Tab Mapas — 2D (precursores/eventos/alertas) + globo 3D (saturación por nodo). */
export function MapasTab() {
  const n = usePoll(useCallback(() => api.nodos(), []), 30000);
  const s = usePoll(useCallback(() => api.sismos(4.5, 60), []), 30000);

  const nodes = useMemo(
    () =>
      (n.data || [])
        .map((nd) => ({
          lat: Number(nd.lat),
          lon: Number(nd.lon),
          tipo: String(nd.tipo || ""),
          label: String(nd.nombre || ""),
          sat: Number(nd.saturacion ?? nd.saturation ?? nd.carga ?? 0),
          highlight: String(nd.nombre || "").toLowerCase().includes("tlaxcala"),
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [n.data],
  );
  const quakes = useMemo(
    () =>
      (s.data?.items || [])
        .map((q) => ({
          lat: Number(q.lat),
          lon: Number(q.lon),
          mag: Number(q.magnitude),
          label: String(q.region || ""),
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [s.data],
  );

  const counts = useMemo(() => {
    const c = { real: 0, ghost: 0, geobateria: 0 };
    for (const nd of nodes) {
      const t = nd.tipo.toLowerCase();
      if (t.includes("ghost") || t.includes("fantasma")) c.ghost++;
      else if (t.includes("geo")) c.geobateria++;
      else c.real++;
    }
    return c;
  }, [nodes]);

  const topSat = useMemo(
    () => [...nodes].filter((x) => x.sat > 0).sort((a, b) => b.sat - a.sat).slice(0, 6),
    [nodes],
  );

  return (
    <div className="space-y-6">
      <TabIntro title="Mapas — dónde vigila el sistema">
        <p>
          La malla UVG-125 sobre el planeta. El <b>mapa 2D</b> muestra nodos y sismos recientes por ubicación; el{" "}
          <b>globo 3D</b> resalta la tensión (saturación) acumulada por nodo. No es un mapa de alertas oficiales.
        </p>
      </TabIntro>

      <section className="space-y-2">
        <h4 className="text-sm font-medium">Mapa 2D — nodos, sismos y alertas</h4>
        <Map2D nodes={nodes} quakes={quakes} highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }} />
        <Caption>
          Nodos reales, fantasma (teóricos) y geobatería; los anillos son sismos ≥4.5 con coordenadas. Mercator; no es un
          mapa de alertas oficiales.
        </Caption>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="space-y-2">
          <h4 className="text-sm font-medium">Globo 3D — tensión por nodo</h4>
          <div className="rounded-lg border border-border bg-card p-3">
            <Globe3D nodes={nodes} quakes={quakes} />
          </div>
          <Caption>Arrastra para rotar. El color/tamaño de cada nodo refleja su saturación (carga acumulada, tope 1.0).</Caption>
        </section>

        <section className="space-y-2">
          <h4 className="text-sm font-medium">Nodos con más tensión</h4>
          <div className="rounded-lg border border-border bg-card p-4">
            {topSat.length ? (
              <div className="space-y-2.5">
                {topSat.map((nd, i) => (
                  <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
                    <div className="flex items-center gap-3">
                      <span className="w-32 truncate text-xs">{nd.label || "nodo"}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#232427]" style={{ minWidth: 80 }}>
                        <div
                          className="h-full"
                          style={{
                            width: `${Math.min(100, nd.sat * 100)}%`,
                            background: nd.sat > 0.8 ? "#ff9100" : nd.sat > 0.6 ? "#ffc107" : "#10b981",
                          }}
                        />
                      </div>
                    </div>
                    <span className="mono text-xs">{nd.sat.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Caption>Sin saturación por nodo en esta DB (se puebla al correr ciclos).</Caption>
            )}
            <div className="mt-4 grid grid-cols-3 gap-2.5">
              {[
                ["reales", counts.real],
                ["fantasma", counts.ghost],
                ["geobatería", counts.geobateria],
              ].map(([k, v]) => (
                <div key={k as string} className="rounded-lg bg-panel py-2.5 text-center">
                  <div className="text-lg font-bold">{v as number}</div>
                  <div className="text-[10px] text-muted">{k as string}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
