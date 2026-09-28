import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Map2D } from "@/components/maps/Map2D";
import { Globe3D } from "@/components/maps/Globe3D";
import { Panel, Metrica, esAusente } from "@/components/ui/data";

/**
 * MAPAS — superficie EXPLORE.
 *
 * El usuario navega un espacio abierto (la malla UVG-125 sobre el planeta),
 * así que la composición es mapa-primero y los controles/resúmenes quedan al
 * margen.
 *
 * Corrección de dato: `Number(nd.saturacion ?? ... ?? 0)` convertía un nodo
 * SIN medición en un nodo con saturación 0.00 — indistinguible de uno medido
 * y tranquilo. Con 88 de 125 nodos en cero, esa diferencia importa: ahora los
 * nodos sin lectura se cuentan aparte y no entran al ranking.
 */
export function MapasTab() {
  const n = usePoll(useCallback(() => api.nodos(), []), 30000);
  const s = usePoll(useCallback(() => api.sismos(4.5, 60), []), 30000);

  const nodes = useMemo(
    () =>
      (n.data || [])
        .map((nd) => {
          const bruto = nd.saturacion ?? nd.saturation ?? nd.carga;
          return {
            lat: Number(nd.lat),
            lon: Number(nd.lon),
            tipo: String(nd.tipo || ""),
            label: String(nd.nombre || ""),
            // `sat` alimenta el globo (necesita número); `medido` conserva la
            // verdad de si hubo lectura.
            sat: esAusente(bruto) ? 0 : Number(bruto),
            medido: !esAusente(bruto),
            highlight: String(nd.nombre || "").toLowerCase().includes("tlaxcala"),
          };
        })
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

  const conCarga = useMemo(
    () => [...nodes].filter((x) => x.medido && x.sat > 0).sort((a, b) => b.sat - a.sat),
    [nodes],
  );
  const enReposo = nodes.filter((x) => x.medido && x.sat === 0).length;
  const topSat = conCarga.slice(0, 8);

  return (
    <div className="space-y-5">
      <Panel
        titulo="Malla UVG-125 y sismos recientes"
        meta="Mercator · M≥4.5"
        nota="Nodos reales, Ghost (teóricos) y geobatería; los anillos son sismos con coordenadas del catálogo USGS. No es un mapa de alertas oficiales: muestra dónde mira el sistema, no dónde va a temblar."
      >
        <Map2D nodes={nodes} quakes={quakes} highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }} />
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <Panel
          titulo="Globo — tensión por nodo"
          meta="arrastra para rotar"
          nota="El tamaño y color de cada nodo reflejan su saturación acumulada (tope 1.0). Un nodo sin lectura no se dibuja cargado: se dibuja neutro."
        >
          <Globe3D nodes={nodes} quakes={quakes} />
        </Panel>

        <div className="space-y-5">
          <Panel
            titulo="Nodos con más tensión"
            meta={`${conCarga.length} con carga`}
            nota={
              enReposo > 0
                ? `${enReposo} nodos medidos están en reposo (saturación 0.00) y ${
                    nodes.length - conCarga.length - enReposo
                  } no tienen lectura. Un cero medido y una casilla vacía no son lo mismo.`
                : undefined
            }
          >
            {topSat.length ? (
              <ul className="space-y-2.5">
                {topSat.map((nd, i) => {
                  const color =
                    nd.sat > 0.8 ? "var(--color-aviso)" : nd.sat > 0.6 ? "var(--color-atencion)" : "var(--color-calma)";
                  return (
                    <li key={i} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="w-28 shrink-0 truncate text-meta text-body" title={nd.label}>
                          {nd.label || "nodo"}
                        </span>
                        <div className="h-1.5 min-w-[60px] flex-1 overflow-hidden rounded-full bg-surface-sunken">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${Math.min(100, nd.sat * 100)}%`, background: color }}
                          />
                        </div>
                      </div>
                      <span className="mono shrink-0 text-meta tabular-nums" style={{ color }}>
                        {nd.sat.toFixed(2)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="py-4 text-center text-meta text-muted">
                Ningún nodo registra carga acumulada todavía.
              </p>
            )}
          </Panel>

          <Panel titulo="Composición de la malla" meta="125 nodos">
            <div className="grid grid-cols-3 gap-4">
              <Metrica etiqueta="Reales" jerarquia="compacta" valor={counts.real} contexto="medición directa" />
              <Metrica etiqueta="Ghost" jerarquia="compacta" valor={counts.ghost} contexto="teóricos" />
              <Metrica etiqueta="Geobatería" jerarquia="compacta" valor={counts.geobateria} contexto="acumuladores" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
