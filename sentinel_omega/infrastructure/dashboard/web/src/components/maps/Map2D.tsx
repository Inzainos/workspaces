import { useMemo, useState } from "react";
import {
  CONTINENTES,
  colorTipo,
  colorRiesgoSat,
  colorSismo,
  alfaSismo,
  infoNodo,
  infoSismo,
  LeyendaMapa,
  type LngLat,
  type NodoMapa,
  type SismoMapa,
} from "./shared";

function mercator(lat: number, lon: number, w: number, h: number): [number, number] {
  const x = ((lon + 180) / 360) * w;
  const latClamped = Math.max(-85, Math.min(85, lat));
  const rad = (latClamped * Math.PI) / 180;
  const merc = Math.log(Math.tan(Math.PI / 4 + rad / 2));
  const y = h / 2 - (merc * w) / (2 * Math.PI);
  return [x, y];
}

function pathFromPoly(poly: LngLat[], w: number, h: number): string {
  if (!poly.length) return "";
  const [x0, y0] = mercator(poly[0][1], poly[0][0], w, h);
  const parts = [`M ${x0.toFixed(2)} ${y0.toFixed(2)}`];
  for (let i = 1; i < poly.length; i += 1) {
    const [x, y] = mercator(poly[i][1], poly[i][0], w, h);
    parts.push(`L ${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  parts.push("Z");
  return parts.join(" ");
}

/**
 * Mapa 2D Mercator — malla UVG-125 + sismos.
 *
 * Codificación (sistema de diseño: saturado = riesgo, nada más):
 * - tipo de nodo → categoría en la rampa de serie desaturada;
 * - carga acumulada → aro en la rampa de riesgo + radio creciente;
 * - sin lectura → punto hueco neutro (distinto de un cero medido, que va
 *   relleno con su color de tipo);
 * - sismo → aro por magnitud (M≥6 crítico), opacidad por recencia;
 * - hover → ficha bajo el mapa (el `<title>` nativo queda como respaldo).
 */
export function Map2D({
  nodes,
  quakes,
  highlight,
  focus,
}: {
  nodes: NodoMapa[];
  quakes?: SismoMapa[];
  highlight?: { lat: number; lon: number; label?: string };
  /** label del nodo a resaltar (p.ej. hover en el ranking de tensión) */
  focus?: string | null;
}) {
  const w = 900;
  const h = 420;
  const [hover, setHover] = useState<{ kind: "n" | "q"; i: number } | null>(null);

  const info = useMemo(() => {
    if (!hover) return null;
    if (hover.kind === "n") return nodes[hover.i] ? infoNodo(nodes[hover.i]) : null;
    const qs = quakes || [];
    return qs[hover.i] ? infoSismo(qs[hover.i]) : null;
  }, [hover, nodes, quakes]);

  return (
    <div className="space-y-2">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full cursor-crosshair rounded-lg border border-border bg-surface-sunken"
        role="img"
        aria-label="Mapa Mercator de la malla UVG-125 y sismos recientes"
      >
        {CONTINENTES.map((poly, i) => (
          <path
            key={`c${i}`}
            d={pathFromPoly(poly, w, h)}
            fill="var(--color-base-750)"
            fillOpacity={0.55}
            stroke="var(--color-base-600)"
            strokeWidth={0.7}
            opacity={0.9}
          />
        ))}

        {/* Graticule + etiquetas de latitud para leer la escala de reojo */}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const [, y] = mercator(lat, 0, w, h);
          return (
            <line
              key={`lat${lat}`}
              x1={0}
              x2={w}
              y1={y}
              y2={y}
              stroke="var(--color-base-100)"
              strokeOpacity={lat === 0 ? 0.07 : 0.045}
            />
          );
        })}
        {[-120, -60, 0, 60, 120].map((lon) => {
          const [x] = mercator(0, lon, w, h);
          return (
            <line key={`lon${lon}`} x1={x} x2={x} y1={0} y2={h} stroke="var(--color-base-100)" strokeOpacity={0.05} />
          );
        })}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const [, y] = mercator(lat, 0, w, h);
          return (
            <text key={`lt${lat}`} x={4} y={y - 3} fontSize={8} fill="var(--color-base-500)" className="mono">
              {lat === 0 ? "0°" : `${lat > 0 ? "" : "−"}${Math.abs(lat)}°`}
            </text>
          );
        })}

        {/* Nodos */}
        {nodes.map((n, i) => {
          const [x, y] = mercator(n.lat, n.lon, w, h);
          const esFoco = focus && n.label === focus;
          const sat = typeof n.sat === "number" ? n.sat : 0;
          const cargado = sat > 0 && n.medido !== false;
          const r = n.medido === false ? 2 : cargado ? 2 + Math.min(1, sat) * 3.2 : 2;
          return (
            <g key={`n${i}`} onMouseEnter={() => setHover({ kind: "n", i })} onMouseLeave={() => setHover(null)}>
              {n.medido === false ? (
                <circle cx={x} cy={y} r={r} fill="none" stroke="var(--color-base-500)" strokeWidth={1} opacity={0.85}>
                  <title>{infoNodo(n)}</title>
                </circle>
              ) : (
                <>
                  {cargado && (
                    <circle
                      cx={x}
                      cy={y}
                      r={r + 2.2}
                      fill="none"
                      stroke={colorRiesgoSat(sat)}
                      strokeWidth={1.2}
                      opacity={0.85}
                    />
                  )}
                  <circle cx={x} cy={y} r={r} fill={colorTipo(n.tipo)} opacity={hover?.kind === "n" && hover.i === i ? 1 : 0.92}>
                    <title>{infoNodo(n)}</title>
                  </circle>
                </>
              )}
              {esFoco && (
                <circle cx={x} cy={y} r={r + 5} fill="none" stroke="var(--color-base-100)" strokeWidth={1} strokeDasharray="2 2" />
              )}
            </g>
          );
        })}

        {/* Sismos */}
        {(quakes || []).map((q, i) => {
          const [x, y] = mercator(q.lat, q.lon, w, h);
          const mag = q.mag ?? 4.5;
          const r = 2 + Math.max(0, mag - 4.5) * 1.8;
          const alfa = alfaSismo(q.ts);
          const col = colorSismo(mag);
          return (
            <g key={`q${i}`} onMouseEnter={() => setHover({ kind: "q", i })} onMouseLeave={() => setHover(null)}>
              <circle cx={x} cy={y} r={r} fill="none" stroke={col} strokeWidth={1.2} opacity={alfa}>
                <title>{infoSismo(q)}</title>
              </circle>
              <circle cx={x} cy={y} r={1} fill={col} opacity={alfa * 0.8} />
            </g>
          );
        })}

        {/* Tlaxcala — nodo de observación */}
        {highlight
          ? (() => {
              const [x, y] = mercator(highlight.lat, highlight.lon, w, h);
              return (
                <g>
                  <circle cx={x} cy={y} r={7} fill="none" stroke="var(--color-serie-1)" strokeWidth={1.5} />
                  <circle cx={x} cy={y} r={3} fill="var(--color-base-100)" />
                  <text x={x + 10} y={y - 8} fill="var(--color-base-100)" fontSize={11}>
                    {highlight.label || "Tlaxcala"}
                  </text>
                </g>
              );
            })()
          : null}
      </svg>

      <LeyendaMapa />

      {/* Ficha de hover: altura fija para que el layout no salte */}
      <div className="mono min-h-5 text-meta text-body">
        {info ? (
          info
        ) : (
          <span className="text-faint">Pasa el cursor por un nodo o un sismo para ver su ficha.</span>
        )}
      </div>

      <p className="text-meta text-muted">
        Mapa 2D Mercator de los 125 nodos de topología y sismos recientes con coordenadas. No es un mapa de
        alertas oficiales. Si la tabla fuente USGS está vacía, la asignación nodo↔sismo de esta DB no fue
        remapeada.
      </p>
    </div>
  );
}
