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
import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Mapa2D } from "@/components/maps/Map2D";
import { Globo3D } from "@/components/maps/Globe3D";
import { colorRiesgoSat } from "@/components/maps/shared";
import { Panel, Metrica, esAusente } from "@/components/ui/data";
import type { NodoMapa, SismoMapa } from "@/components/maps/shared";

export function MapasTab() {
  const n = usePoll(useCallback(() => api.nodos(), []), 30000);
  const s = usePoll(useCallback(() => api.sismos(4.5, 60), []), 30000);
  const [focus, setFocus] = useState<string | null>(null);

  const nodos = useMemo<NodoMapa[]>(
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
      (s.data?.items || [])
        .map((q) => {
          const lat = q.lat == null ? Number.NaN : Number(q.lat);
          const lon = q.lon == null ? Number.NaN : Number(q.lon);
          return {
            lat,
            lon,
            mag: esAusente(q.magnitude) ? undefined : Number(q.magnitude),
            label: String(q.region || ""),
            profundidadKm: esAusente(q.depth_km) ? undefined : Number(q.depth_km),
            ts: esAusente(q.timestamp) ? undefined : Number(q.timestamp),
          } satisfies SismoMapa;
        })
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [s.data],
  );

  const contados = useMemo(() => {
    const c = { reales: 0, fantasmas: 0, geoBatería: 0 };
    for (const nd of nodos) {
      const t = (nd.tipo || "").toLowerCase();
      if (t.includes("fantasma") || t.includes("fantasma")) c.fantasmas++;
      else if (t.includes("geo")) c.geoBatería++;
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
  const totalSismos = s.data?.total_matching;

  return (
    <div className="space-y-5">
      <Panel
        detalle="Malla UVG-125 y sismos recientes"
        objetivo={sismos.length ? `${sismos.length} sismos M≥4.5` : "ningún sismo reciente"}
        riesgo={nodos.some((n) => (n.sat ?? 0) > 0.8) ? "ALTO" : "BAJO"}
        acción="revisar nodos críticos"
      >
        <MapaFractal
          nodos={nodos}
          sismos={sismos}
          altura={520}
          foco={focus}
          setFoco={setFocus}
        />
        <div className="grid gap-4 md:grid-cols-[repeat(auto-fit,minmax(0,1fr))]">
          <Metrica
            detalle="Nodos vivos"
            objetivo={`${nodos.length} nodos · ${contdos.reales} reales · ${contdos.fantasmas} fantasmas · ${contdos.geoBatería} geobatería`}
            riesgo={contdos.fantasmas > 0 ? "MEDIO" : "BAJO"}
            acción="revisar mapa"
            sha256={undefined}
          />
          <Metrica
            detalle="Sismos M≥4.5"
            objetivo={`${sismos.length} detectados · ${totalSismos ?? "?"} en ventana`}
            riesgo={sismos.length > 5 ? "ALTO" : "BAJO"}
            acción="revisar mapa"
            sha256={undefined}
          />
          <Metrica
            detalle="Nodos con carga"
            objetivo={`${conCarga.length} con señal · ${enReposo} sin carga`}
            riesgo={conCarga.length > 5 ? "MEDIO" : "BAJO"}
            acción="inspeccionar"
            sha256={topSat[0]?.topSat?.nodo?.substring(0,16)}
          />
        </div>
      </Panel>

      {/* ================= TOP NODOS POR CARGA ================= */}
      <Panel
        detalle="Top nodos por carga"
        objetivo={`Top ${topSat.length} de ${nodos.length} nodos`}
        riesgo={topSat[0]?.sat ?? 0 > 0.8 ? "ALTO" : "BAJO"}
        acción="inspeccionar nodo"
      >
        {topSat.length ? (
          <div className="space-y-2">
            {topSat.map((n, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-2 rounded-lg border border-border bg-surface-sunken"
              >
                <div className="mono texto-principal fuente-negrita">{n.label}</div>
                <div className="flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="mono texto-meta">Lat:</span>
                    <span className="mono texto-principal fuente-negrita">{n.lat?.toFixed(4)}</span>
                    <span className="mono texto-meta">Lon:</span>
                    <span className="mono texto-principal fuente-negrita">{n.lon?.toFixed(4)}</span>
                  </div>
                  <div className="w-full h-2 bg-surface bg-fondo mt-1 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-var(--color-calma) via-var(--color-aviso) to-var(--color-critico)"
                      style={{ width: `${(n.sat ?? 0) * 100}%` }}
                    ></div>
                  </div>
                  <div className="flex items-baseline gap-2 mt-1 texto-micro texto-muteado">
                    <span>Saturación: {(n.sat ?? 0).toFixed(2)}</span>
                    <span>{n.medido ? "medido" : "no medido"}</span>
                    {n.updated && <span>{new Date(n.updated).toLocaleDateString("es-MX")}</span>}
                  </div>
                </div>
                <div className="mono texto-principal fuente-negrita">
                  {(n.sat ?? 0).toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <SinDatos título="Sin nodos con carga" />
        )}
      </Panel>
    </div>
  );
}
