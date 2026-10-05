import { useCallback, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Map2D } from "@/components/maps/Map2D";
import { Globe3D } from "@/components/maps/Globe3D";
import { colorRiesgoSat } from "@/components/maps/shared";
import { Panel, Metrica, esAusente } from "@/components/ui/data";
import type { NodoMapa, SismoMapa } from "@/components/maps/shared";

/**
 * MAPAS — superficie EXPLORE: mapa primero, controles al margen.
 *
 * Correcciones de dato vivas aquí:
 * - `Number(nd.saturacion ?? ... ?? 0)` convertía un nodo SIN medición en un
 *   nodo con saturación 0.00 (88 de 125 en cero: la diferencia importa). Ahora
 *   `medido` conserva la verdad y `sat` alimenta los mapas.
 * - `Number(nd.lat)` con `lat: null` da 0, no NaN: un nodo sin coordenadas
 *   pasaría el filtro `Number.isFinite` y caería en (0,0). Guard explícito.
 * - Los sismos traen `depth_km` y `timestamp` del catálogo: profundidad y
 *   recencia viajan al mapa en vez de descartarse.
 */
export function MapasTab() {
  const n = usePoll(useCallback(() => api.nodos(), []), 30000);
  const s = usePoll(useCallback(() => api.sismos(4.5, 60), []), 30000);
  const [focus, setFocus] = useState<string | null>(null);

  const nodes = useMemo<NodoMapa[]>(
    () =>
      (n.data || [])
        .map((nd) => {
          const bruto = nd.saturacion ?? nd.saturation ?? nd.carga;
          const lat = nd.lat == null ? Number.NaN : Number(nd.lat);
          const lon = nd.lon == null ? Number.NaN : Number(nd.lon);
          return {
            lat,
            lon,
            tipo: String(nd.tipo || ""),
            label: String(nd.nombre || ""),
            // `sat` alimenta los mapas; `medido` conserva la verdad.
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

  const quakes = useMemo<SismoMapa[]>(
    () =>
      (s.data?.items || [])
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

  const counts = useMemo(() => {
    const c = { real: 0, ghost: 0, geobateria: 0 };
    for (const nd of nodes) {
      const t = (nd.tipo ?? "").toLowerCase();
      if (t.includes("ghost") || t.includes("fantasma")) c.ghost++;
      else if (t.includes("geo")) c.geobateria++;
      else c.real++;
    }
    return c;
  }, [nodes]);

  const conCarga = useMemo(
    () => [...nodes].filter((x) => x.medido && (x.sat ?? 0) > 0).sort((a, b) => (b.sat ?? 0) - (a.sat ?? 0)),
    [nodes],
  );
  const enReposo = nodes.filter((x) => x.medido && x.sat === 0).length;
  const topSat = conCarga.slice(0, 8);
  const totalSismos = s.data?.total_matching;

  return (
    <div className="space-y-5">
      <Panel
        titulo="Malla UVG-125 y sismos recientes"
        meta={
          totalSismos != null
            ? `Mercator · últimos ${quakes.length} de ${totalSismos.toLocaleString("es-MX")} sismos M≥4.5`
            : "Mercator · M≥4.5"
        }
        nota="Nodos reales, Ghost (teóricos) y geobatería; los anillos son sismos con coordenadas del catálogo USGS — el color va por magnitud y la opacidad decae con la antigüedad. No es un mapa de alertas oficiales: muestra dónde mira el sistema, no dónde va a temblar."
      >
        <Map2D
          nodes={nodes}
          quakes={quakes}
          highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }}
          focus={focus}
        />
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <Panel
          titulo="Globo — tensión por nodo"
          meta="arrastra para rotar"
          nota="El radio y el aro de cada nodo crecen con su saturación acumulada (tope 1.0) y el aro va en la rampa de riesgo. Un nodo sin lectura se dibuja hueco y neutro, no cargado."
        >
          <Globe3D nodes={nodes} quakes={quakes} focus={focus} />
        </Panel>

        <div className="space-y-5">
          <Panel
            titulo="Nodos con más tensión"
            meta={`${conCarga.length} con carga`}
            nota={
              enReposo > 0
                ? `${enReposo} nodos medidos están en reposo (saturación 0.00) y ${
                    nodes.length - conCarga.length - enReposo
                  } no tienen lectura. Un cero medido y una casilla vacía no son lo mismo. Pasa el cursor por la lista para ubicar el nodo en ambos mapas.`
                : "Pasa el cursor por la lista para ubicar el nodo en ambos mapas."
            }
          >
            {topSat.length ? (
              <ul className="space-y-2.5">
                {topSat.map((nd, i) => {
                  const color = colorRiesgoSat(nd.sat ?? 0);
                  return (
                    <li
                      key={i}
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded px-1 transition-colors hover:bg-surface-raised"
                      onMouseEnter={() => setFocus(nd.label || null)}
                      onMouseLeave={() => setFocus(null)}
                      title={nd.region ? `${nd.label} · ${nd.region}` : nd.label}
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="w-28 shrink-0 truncate text-meta text-body" title={nd.label}>
                          {nd.label || "nodo"}
                        </span>
                        <div className="h-1.5 min-w-[60px] flex-1 overflow-hidden rounded-full bg-surface-sunken">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${Math.min(100, (nd.sat ?? 0) * 100)}%`, background: color }}
                          />
                        </div>
                      </div>
                      <span className="mono shrink-0 text-meta tabular-nums" style={{ color }}>
                        {(nd.sat ?? 0).toFixed(2)}
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
