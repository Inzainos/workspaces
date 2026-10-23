/**
 * MAPAS — superficie EXPLORE: mapa primero, controles al margen.
 *
 * Correcciones de dato vivas aquí:
 * - `Number(nd.saturacion ?? ... ?? 0)` convertía un nodo sin medición en
 *   un nodo con saturación 0.00 (benigno vs importante). Ahora `medido`
 *   conserva la verdad.
 * - `Number(nd.lat)` con `lat: null` da 0, no NaN: un nodo sin coordenadas
 *   pasaría el filtro y caería en (0,0). Guard explícito.
 * - Los sismos traen `depth_km` y `timestamp`: profundidad y recencia
 *   viajan al mapa en vez de descartarse.
 */
import { useCallback, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { MapaFractal } from "@/components/maps/MapaFractal";
import { Panel, Metrica, Cifra, SinDatos, esAusente } from "@/components/ui/data";
import type { NodoMapa, SismoMapa } from "@/components/maps/shared";

export function MapasTab() {
  const n = usePoll(useCallback(() => api.nodos(), []), 30000);
  const s = usePoll(useCallback(() => api.sismos(4.5, 60), []), 30000);
  const [focus, setFocus] = useState<string | null>(null);

  const nodos = useMemo<NodoMapa[]>(
    () =>
      ((n.data as any[]) || [])
        .map((nd) => {
          const bruto = nd.saturacion ?? nd.saturation ?? nd.carga;
          const lat = nd.lat == null ? Number.NaN : Number(nd.lat);
          const lon = nd.lon == null ? Number.NaN : Number(nd.lon);
          return {
            lat,
            lon,
            tipo: String(nd.tipo || ""),
            label: String(nd.nombre || ""),
            sat: esAusente(bruto) ? 0 : Number(bruto),
            medido: !esAusente(bruto),
            region: nd.region == null ? undefined : String(nd.region),
            updated: nd.updated_at == null ? undefined : String(nd.updated_at),
            highlight: String(nd.nombre || "").toLowerCase().includes("tlaxcala"),
          } satisfies NodoMapa;
        })
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [n.data],
  );

  const sismos = useMemo<SismoMapa[]>(
    () =>
      ((s.data?.items as any[]) || [])
        .map((q) => {
          const lat = q.lat == null ? Number.NaN : Number(q.lat);
          const lon = q.lon == null ? Number.NaN : Number(q.lon);
          return {
            lat,
            lon,
            mag: esAusente(q.magnitude) ? undefined : Number(q.magnitude),
            label: String(q.region || ""),
            depthKm: esAusente(q.depth_km) ? undefined : Number(q.depth_km),
            ts: esAusente(q.timestamp) ? undefined : Number(q.timestamp),
          } satisfies SismoMapa;
        })
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [s.data],
  );

  const contados = useMemo(() => {
    const c = { reales: 0, fantasmas: 0, geoBateria: 0 };
    for (const nd of nodos) {
      const t = (nd.tipo || "").toLowerCase();
      if (t.includes("fantasma")) c.fantasmas++;
      else if (t.includes("geo")) c.geoBateria++;
      else c.reales++;
    }
    return c;
  }, [nodos]);

  const conCarga = useMemo(
    () => [...nodos].filter((x) => x.medido && (x.sat ?? 0) > 0).sort((a, b) => (b.sat ?? 0) - (a.sat ?? 0)),
    [nodos],
  );
  const enReposo = nodos.filter((x) => x.medido && x.sat === 0).length;
  const topSat = conCarga.slice(0, 8);
  const totalSismos = (s.data as any)?.total_matching;

  return (
    <div className="space-y-5">
      <Panel
        titulo="Malla UVG-125 y sismos recientes"
        meta={sismos.length ? `${sismos.length} sismos M≥4.5` : "ningún sismo reciente"}
        acento={nodos.some((x) => (x.sat ?? 0) > 0.8) ? "HIGH" : "LOW"}
      >
        <MapaFractal
          nodos={nodos}
          sismos={sismos}
          altura={520}
          foco={focus}
          setFoco={setFocus}
        />
        <div className="grid gap-4 md:grid-cols-3 mt-4">
          <Metrica
            etiqueta="Nodos vivos"
            valor={`${nodos.length}`}
            contexto={`${contados.reales} reales · ${contados.fantasmas} fantasmas · ${contados.geoBateria} geobatería`}
          />
          <Metrica
            etiqueta="Sismos M≥4.5"
            valor={`${sismos.length}`}
            contexto={`${totalSismos != null ? Number(totalSismos).toLocaleString("es-MX") : "?"} en ventana`}
          />
          <Metrica
            etiqueta="Nodos con carga"
            valor={`${conCarga.length}`}
            contexto={`${enReposo} sin carga · mayor: ${topSat[0]?.label ?? "—"}`}
          />
        </div>
      </Panel>

      <Panel titulo="Top nodos por carga" meta={`Top ${topSat.length} de ${nodos.length} nodos`}>
        {topSat.length ? (
          <div className="space-y-2">
            {topSat.map((nd, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-2 rounded-lg border border-border bg-surface-sunken"
              >
                <div className="mono texto-principal fuente-negrita">{nd.label}</div>
                <div className="flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="mono texto-meta">Lat:</span>
                    <span className="mono texto-principal fuente-negrita">{nd.lat?.toFixed(4)}</span>
                    <span className="mono texto-meta">Lon:</span>
                    <span className="mono texto-principal fuente-negrita">{nd.lon?.toFixed(4)}</span>
                  </div>
                  <div className="w-full h-2 bg-surface-sunken mt-1 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(nd.sat ?? 0) * 100}%`,
                        background: "linear-gradient(to right, var(--color-calma), var(--color-aviso), var(--color-critico))",
                      }}
                    ></div>
                  </div>
                  <div className="flex items-baseline gap-2 mt-1 texto-micro texto-desvanecido">
                    <span>Saturación: {(nd.sat ?? 0).toFixed(2)}</span>
                    <span>{nd.medido ? "medido" : "no medido"}</span>
                    {nd.updated && <span>{String(nd.updated).slice(0, 10)}</span>}
                  </div>
                </div>
                <div className="mono texto-principal fuente-negrita">
                  <Cifra valor={nd.sat} digits={2} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <SinDatos titulo="Sin nodos con carga" />
        )}
      </Panel>
    </div>
  );
}
