interface DataPoint {
  // La API devuelve Record<string, unknown>; los charts coercionan con Number()/String().
  [key: string]: unknown;
}

/** Paleta consistente (theme-friendly). Se usa cuando el dato no trae color. */
const PALETTE = [
  "#5e6ad2", "#10b981", "#ffc107", "#ff9100", "#ff1744",
  "#3b82f6", "#8b5cf6", "#14b8a6", "#ec4899", "#f59e0b",
];

// Ancho del sistema de coordenadas interno; el viewBox lo reescala al 100%.
const VBW = 640;

interface BarSeries {
  key: string;
  color?: string;
  name?: string;
}
interface SimpleBarsProps {
  data: DataPoint[];
  xKey: string;
  /** Serie única (compat). Ignorado si se pasa `bars`. */
  yKey?: string;
  color?: string;
  /** Multi-serie: barras agrupadas por categoría. */
  bars?: BarSeries[];
  height?: number;
}

/**
 * Barras agrupadas. Acepta `bars` (multi-serie) o `yKey` (serie única).
 * Coordenadas internas reescaladas al 100% del contenedor vía viewBox.
 */
export function SimpleBars({ data, xKey: _xKey, yKey, color = "#5e6ad2", bars, height = 150 }: SimpleBarsProps) {
  if (!data.length) return <div className="py-8 text-center text-xs text-muted">Sin datos</div>;
  const series: Required<BarSeries>[] = (
    bars && bars.length ? bars : yKey ? [{ key: yKey, color, name: yKey }] : []
  ).map((s, i) => ({ key: s.key, color: s.color || PALETTE[i % PALETTE.length], name: s.name || s.key }));
  if (!series.length) return <div className="py-8 text-center text-xs text-muted">Sin series</div>;

  const allVals = data.flatMap((d) => series.map((s) => Number(d[s.key]))).filter((v) => Number.isFinite(v));
  if (!allVals.length) return <div className="py-8 text-center text-xs text-muted">Sin datos numéricos</div>;
  const max = Math.max(...allVals, 0);

  const marginL = 24, marginR = 8, marginB = 10, marginT = 10;
  const plotW = VBW - marginL - marginR;
  const plotH = height - marginB - marginT;
  const groupW = plotW / data.length;
  const barW = Math.max(2, (groupW * 0.8) / series.length);
  const multi = series.length > 1;

  return (
    <div className="space-y-1">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${VBW} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        role="img"
      >
        {data.map((d, i) =>
          series.map((s, j) => {
            const v = Number(d[s.key]);
            const h = max > 0 && Number.isFinite(v) ? (v / max) * plotH : 0;
            const x = marginL + i * groupW + groupW * 0.1 + j * barW;
            const y = height - marginB - h;
            return <rect key={`${i}-${j}`} x={x} y={y} width={barW} height={h} fill={s.color} rx={2} />;
          }),
        )}
      </svg>
      {multi ? (
        <ul className="flex flex-wrap gap-3 text-xs">
          {series.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
              <span className="text-muted">{s.name}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

interface LineSparkProps {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
}

export function LineSpark({ data, xKey: _xKey, yKey, color = "#ec4899", height = 150 }: LineSparkProps) {
  if (!data.length) return <div className="py-8 text-center text-xs text-muted">Sin datos</div>;
  const values = data.map((d) => Number(d[yKey]));
  const finite = values.filter((v) => Number.isFinite(v));
  if (!finite.length) return <div className="py-8 text-center text-xs text-muted">Sin datos numéricos</div>;
  const max = Math.max(...finite);
  const min = Math.min(...finite);
  const range = max - min || 1;
  const stepX = (VBW - 40) / Math.max(1, data.length - 1);
  const points = data
    .map((d, i) => {
      const v = Number(d[yKey]);
      if (!Number.isFinite(v)) return null;
      const x = i * stepX + 20;
      const y = height - 10 - ((v - min) / range) * (height - 20);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .filter(Boolean)
    .join(" ");
  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${VBW} ${height}`}
      preserveAspectRatio="none"
      className="w-full"
      role="img"
    >
      <polyline fill="none" stroke={color} strokeWidth={2} points={points} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

interface PieDatum {
  name: string;
  value: number;
  color?: string;
}
interface SimplePieProps {
  data: PieDatum[];
  height?: number;
  /** Máximo lado del donut en px (acota gráficas grandes). */
  maxSize?: number;
  legend?: boolean;
}

function donutSegment(cx: number, cy: number, R: number, r: number, a0: number, a1: number): string {
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const x0o = cx + R * Math.cos(a0), y0o = cy + R * Math.sin(a0);
  const x1o = cx + R * Math.cos(a1), y1o = cy + R * Math.sin(a1);
  const x1i = cx + r * Math.cos(a1), y1i = cy + r * Math.sin(a1);
  const x0i = cx + r * Math.cos(a0), y0i = cy + r * Math.sin(a0);
  return `M ${x0o} ${y0o} A ${R} ${R} 0 ${large} 1 ${x1o} ${y1o} L ${x1i} ${y1i} A ${r} ${r} 0 ${large} 0 ${x0i} ${y0i} Z`;
}

/**
 * Donut robusto: color opcional (cae a paleta), maneja el caso de una sola
 * porción (círculo completo) y trae leyenda. Acotado por `maxSize`.
 */
export function SimplePie({ data, height = 150, maxSize = 180, legend = true }: SimplePieProps) {
  const clean = (data || []).filter((d) => Number.isFinite(Number(d.value)) && Number(d.value) > 0);
  if (!clean.length) return <div className="py-8 text-center text-xs text-muted">Sin datos</div>;
  const size = Math.min(height, maxSize);
  const total = clean.reduce((a, d) => a + Number(d.value), 0);
  const cx = size / 2, cy = size / 2;
  const R = size / 2 - 6;
  const r = R * 0.58; // agujero del donut
  const colored = clean.map((d, i) => ({ ...d, _color: d.color || PALETTE[i % PALETTE.length] }));

  let start = -Math.PI / 2;
  const paths = colored.map((d, i) => {
    const frac = Number(d.value) / total;
    let a1 = start + frac * 2 * Math.PI;
    // Círculo completo (una sola porción): partir en dos mitades para que el arco dibuje.
    if (colored.length === 1 || frac >= 0.9999) {
      const mid = start + Math.PI;
      const p = (
        <g key={i}>
          <path d={donutSegment(cx, cy, R, r, start, mid)} fill={d._color} />
          <path d={donutSegment(cx, cy, R, r, mid, start + 2 * Math.PI)} fill={d._color} />
        </g>
      );
      start = a1;
      return p;
    }
    const p = <path key={i} d={donutSegment(cx, cy, R, r, start, a1)} fill={d._color} />;
    start = a1;
    return p;
  });

  return (
    <div className="flex flex-wrap items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" className="shrink-0">
        {paths}
      </svg>
      {legend ? (
        <ul className="min-w-[8rem] space-y-1 text-xs">
          {colored.map((d, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: d._color }} />
              <span className="truncate text-muted">{String(d.name)}</span>
              <span className="mono ml-auto">{((Number(d.value) / total) * 100).toFixed(0)}%</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
