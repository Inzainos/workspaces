type Pt = { lat: number; lon: number; label?: string; tipo?: string; mag?: number };

type LngLat = [number, number];

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

const CONTINENTS: LngLat[][] = [
  // Norteamérica (muy simplificado)
  [[-168, 72], [-145, 70], [-128, 61], [-124, 48], [-118, 33], [-110, 27], [-98, 20], [-84, 22], [-76, 30], [-69, 45], [-82, 58], [-102, 70], [-130, 73]],
  // Sudamérica
  [[-81, 12], [-74, 5], [-70, -10], [-66, -20], [-60, -32], [-54, -44], [-48, -53], [-40, -50], [-36, -33], [-43, -15], [-52, 0], [-66, 8]],
  // Eurasia
  [[-10, 72], [20, 72], [50, 65], [85, 60], [118, 54], [136, 48], [150, 38], [136, 30], [110, 22], [88, 18], [75, 8], [60, 8], [44, 16], [32, 31], [17, 35], [3, 45], [-8, 56]],
  // África
  [[-17, 37], [6, 35], [24, 30], [33, 19], [40, 7], [44, -12], [38, -28], [28, -35], [15, -35], [3, -23], [-5, -6], [-10, 10]],
  // Australia
  [[112, -11], [122, -18], [134, -24], [146, -30], [153, -37], [146, -44], [130, -42], [118, -33], [112, -22]],
  // Groenlandia
  [[-54, 82], [-38, 78], [-30, 72], [-42, 65], [-56, 68], [-62, 75]],
];

const TIPO: Record<string, string> = {
  real: "#5e6ad2",
  ghost: "#8a8f98",
  geobattery: "#ffc107",
};

export function Map2D({
  nodes,
  quakes,
  highlight,
}: {
  nodes: Pt[];
  quakes?: Pt[];
  highlight?: { lat: number; lon: number; label?: string };
}) {
  const w = 900;
  const h = 420;
  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full rounded-lg border border-border bg-[#0b0c0d]">
        <rect width={w} height={h} fill="#0b0c0d" />
        {CONTINENTS.map((poly, i) => (
          <path
            key={`c${i}`}
            d={pathFromPoly(poly, w, h)}
            fill="rgba(94,106,210,0.12)"
            stroke="rgba(148,163,184,0.20)"
            strokeWidth={0.9}
          />
        ))}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const [, y] = mercator(lat, 0, w, h);
          return <line key={`lat${lat}`} x1={0} x2={w} y1={y} y2={y} stroke="rgba(255,255,255,0.035)" />;
        })}
        {[-120, -60, 0, 60, 120].map((lon) => {
          const [x] = mercator(0, lon, w, h);
          return <line key={lon} x1={x} x2={x} y1={0} y2={h} stroke="rgba(255,255,255,0.04)" />;
        })}
        {nodes.map((n, i) => {
          const [x, y] = mercator(n.lat, n.lon, w, h);
          return (
            <circle key={`n${i}`} cx={x} cy={y} r={2.4} fill={TIPO[n.tipo || "real"] || "#5e6ad2"} opacity={0.9}>
              <title>{`${n.label || ""} ${n.tipo || ""}`}</title>
            </circle>
          );
        })}
        {(quakes || []).map((q, i) => {
          const [x, y] = mercator(q.lat, q.lon, w, h);
          const r = 2 + Math.max(0, (q.mag || 4.5) - 4) * 1.6;
          return (
            <circle key={`q${i}`} cx={x} cy={y} r={r} fill="none" stroke="#ff1744" strokeWidth={1} opacity={0.8}>
              <title>{`M${q.mag} ${q.label || ""}`}</title>
            </circle>
          );
        })}
        {highlight ? (
          (() => {
            const [x, y] = mercator(highlight.lat, highlight.lon, w, h);
            return (
              <g>
                <circle cx={x} cy={y} r={7} fill="none" stroke="#5e6ad2" strokeWidth={1.5} />
                <circle cx={x} cy={y} r={3} fill="#f7f8f8" />
                <text x={x + 10} y={y - 8} fill="#f7f8f8" fontSize="11">
                  {highlight.label || "Tlaxcala"}
                </text>
              </g>
            );
          })()
        ) : null}
      </svg>
      <div className="flex flex-wrap gap-3 text-xs text-muted">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: "#5e6ad2" }} /> real</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: "#8a8f98" }} /> ghost</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: "#ffc107" }} /> geobatería</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full border border-danger" /> sismo ≥4.5</span>
      </div>
      <p className="text-xs text-muted">
        Mapa 2D Mercator de los 125 nodos de topología y sismos recientes con coordenadas. No es un mapa de alertas
        oficiales. Si la tabla fuente USGS está vacía, la asignación nodo↔sismo de esta DB no fue remapeada.
      </p>
    </div>
  );
}
