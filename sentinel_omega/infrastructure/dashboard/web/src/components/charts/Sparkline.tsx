/**
 * Gráficas SVG sin dependencias.
 *
 * Criterio: una gráfica de tablero sin eje Y es un adorno. Antes estas
 * primitivas dibujaban la forma pero no la escala, así que una línea de
 * Fantasma plana en 8.1 y otra plana en 40 se veían idénticas. Ahora todas
 * rotulan mínimo/máximo y, donde importa, la referencia.
 *
 * Las series usan los tokens `--color-serie-*` (azules/teales desaturados) y
 * NUNCA los de riesgo: si una línea sale naranja, es que el dato está en zona
 * de aviso, no que tocaba ese color en la paleta.
 */
interface DataPoint {
  [key: string]: unknown;
}

const SERIES = [
  "var(--color-serie-1)",
  "var(--color-serie-2)",
  "var(--color-serie-3)",
  "var(--color-serie-4)",
];

const VBW = 640;

function fmtEje(v: number): string {
  const a = Math.abs(v);
  if (a >= 1000) return `${(v / 1000).toFixed(1)}k`;
  if (a >= 100) return v.toFixed(0);
  if (a >= 10) return v.toFixed(1);
  if (a >= 1) return v.toFixed(2);
  if (a === 0) return "0";
  return v.toFixed(3);
}

/* ========================================================================== */
/* Barras                                                                     */
/* ========================================================================== */

interface BarSeries {
  key: string;
  color?: string;
  name?: string;
}
interface SimpleBarsProps {
  data: DataPoint[];
  xKey: string;
  yKey?: string;
  color?: string;
  bars?: BarSeries[];
  height?: number;
  /** Rotula el eje X con el valor de `xKey` (útil en pocas categorías). */
  mostrarX?: boolean;
}

export function SimpleBars({
  data,
  xKey,
  yKey,
  color,
  bars,
  height = 150,
  mostrarX = false,
}: SimpleBarsProps) {
  if (!data.length) return <VacioChart />;
  const series: Required<BarSeries>[] = (
    bars && bars.length ? bars : yKey ? [{ key: yKey, color: color || SERIES[0], name: yKey }] : []
  ).map((s, i) => ({ key: s.key, color: s.color || SERIES[i % SERIES.length], name: s.name || s.key }));
  if (!series.length) return <VacioChart texto="Sin series" />;

  const allVals = data.flatMap((d) => series.map((s) => Number(d[s.key]))).filter((v) => Number.isFinite(v));
  if (!allVals.length) return <VacioChart texto="Sin datos numéricos" />;
  const max = Math.max(...allVals, 0);

  const mL = 38, mR = 8, mB = mostrarX ? 20 : 10, mT = 8;
  const plotW = VBW - mL - mR;
  const plotH = height - mB - mT;
  const groupW = plotW / data.length;
  const barW = Math.max(2, (groupW * 0.78) / series.length);
  const multi = series.length > 1;

  return (
    <div className="space-y-1.5">
      <svg width="100%" height={height} viewBox={`0 0 ${VBW} ${height}`} preserveAspectRatio="none" role="img">
        {/* Rejilla + eje Y */}
        {[0, 0.5, 1].map((f) => {
          const y = mT + plotH * (1 - f);
          return (
            <g key={f}>
              <line x1={mL} y1={y} x2={VBW - mR} y2={y} stroke="var(--color-border)" strokeWidth={1} />
              <text
                x={mL - 5}
                y={y + 3}
                textAnchor="end"
                fill="var(--color-faint)"
                style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
              >
                {fmtEje(max * f)}
              </text>
            </g>
          );
        })}
        {data.map((d, i) =>
          series.map((s, j) => {
            const v = Number(d[s.key]);
            const h = max > 0 && Number.isFinite(v) ? (v / max) * plotH : 0;
            const x = mL + i * groupW + groupW * 0.11 + j * barW;
            return (
              <rect
                key={`${i}-${j}`}
                x={x}
                y={mT + plotH - h}
                width={barW}
                height={h}
                fill={s.color}
                rx={1.5}
              >
                <title>{`${String(d[xKey] ?? i)} · ${s.name}: ${Number.isFinite(v) ? v : "—"}`}</title>
              </rect>
            );
          }),
        )}
        {mostrarX &&
          data.map((d, i) => (
            <text
              key={`x${i}`}
              x={mL + i * groupW + groupW / 2}
              y={height - 6}
              textAnchor="middle"
              fill="var(--color-faint)"
              style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
            >
              {String(d[xKey] ?? "").slice(0, 8)}
            </text>
          ))}
      </svg>
      {multi ? (
        <ul className="flex flex-wrap gap-3 text-meta">
          {series.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-sm" style={{ background: s.color }} />
              <span className="text-muted">{s.name}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/* ========================================================================== */
/* Línea                                                                      */
/* ========================================================================== */

interface LineSparkProps {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
  /** Líneas horizontales de referencia (umbrales). */
  referencias?: { valor: number; color?: string; etiqueta?: string }[];
  /** Fuerza el dominio Y (si no, se ajusta a los datos). */
  dominio?: [number, number];
  /** Área bajo la curva. */
  area?: boolean;
}

export function LineSpark({
  data,
  xKey: _xKey,
  yKey,
  color = SERIES[0],
  height = 150,
  referencias = [],
  dominio,
  area = true,
}: LineSparkProps) {
  if (!data.length) return <VacioChart />;
  const values = data.map((d) => Number(d[yKey]));
  const finite = values.filter((v) => Number.isFinite(v));
  if (!finite.length) return <VacioChart texto="Sin datos numéricos" />;

  const refVals = referencias.map((r) => r.valor);
  let min = dominio ? dominio[0] : Math.min(...finite, ...refVals);
  let max = dominio ? dominio[1] : Math.max(...finite, ...refVals);

  // Serie constante: sin esto el dominio colapsa y la línea se dibuja pegada a
  // un borde con un eje que repite el mismo número tres veces (el caso real:
  // Schumann congelado en 8.26 rotulaba "8.0 / 8.0 / 7.0"). Se abre una
  // ventana simétrica alrededor del valor para que se lea como lo que es: una
  // recta.
  const serieConstante = Math.abs(max - min) < 1e-9;
  if (!dominio && serieConstante) {
    const centro = max;
    const margen = Math.abs(centro) * 0.02 || 0.5;
    min = centro - margen;
    max = centro + margen;
  } else if (!dominio) {
    const pad = (max - min) * 0.12 || Math.abs(max) * 0.12 || 1;
    min -= pad;
    max += pad;
  }
  const range = max - min || 1;

  const mL = 38, mR = 8, mB = 12, mT = 8;
  const plotW = VBW - mL - mR;
  const plotH = height - mB - mT;
  const stepX = plotW / Math.max(1, data.length - 1);
  const yDe = (v: number) => mT + plotH - ((v - min) / range) * plotH;

  const pts: string[] = [];
  data.forEach((d, i) => {
    const v = Number(d[yKey]);
    if (!Number.isFinite(v)) return;
    pts.push(`${(mL + i * stepX).toFixed(1)},${yDe(v).toFixed(1)}`);
  });
  const linea = pts.join(" ");
  const areaPath =
    area && pts.length > 1
      ? `M ${pts[0]} L ${pts.slice(1).join(" L ")} L ${mL + (data.length - 1) * stepX},${mT + plotH} L ${mL},${mT + plotH} Z`
      : null;

  const gid = `grad-${yKey.replace(/\W/g, "")}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${VBW} ${height}`} preserveAspectRatio="none" role="img">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 0.5, 1].map((f) => {
        const y = mT + plotH * (1 - f);
        return (
          <g key={f}>
            <line x1={mL} y1={y} x2={VBW - mR} y2={y} stroke="var(--color-border)" strokeWidth={1} />
            <text
              x={mL - 5}
              y={y + 3}
              textAnchor="end"
              fill="var(--color-faint)"
              style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
            >
              {fmtEje(min + range * f)}
            </text>
          </g>
        );
      })}
      {referencias.map((r, i) => (
        <g key={i}>
          <line
            x1={mL}
            y1={yDe(r.valor)}
            x2={VBW - mR}
            y2={yDe(r.valor)}
            stroke={r.color || "var(--color-aviso)"}
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.7}
          />
          {r.etiqueta ? (
            <text
              x={VBW - mR - 2}
              y={yDe(r.valor) - 3}
              textAnchor="end"
              fill={r.color || "var(--color-aviso)"}
              style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
            >
              {r.etiqueta}
            </text>
          ) : null}
        </g>
      ))}
      {areaPath ? <path d={areaPath} fill={`url(#${gid})`} /> : null}
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        points={linea}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* ========================================================================== */
/* Donut                                                                      */
/* ========================================================================== */

interface PieDatum {
  name: string;
  value: number;
  color?: string;
}

function donutSegment(cx: number, cy: number, R: number, r: number, a0: number, a1: number): string {
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const x0o = cx + R * Math.cos(a0), y0o = cy + R * Math.sin(a0);
  const x1o = cx + R * Math.cos(a1), y1o = cy + R * Math.sin(a1);
  const x1i = cx + r * Math.cos(a1), y1i = cy + r * Math.sin(a1);
  const x0i = cx + r * Math.cos(a0), y0i = cy + r * Math.sin(a0);
  return `M ${x0o} ${y0o} A ${R} ${R} 0 ${large} 1 ${x1o} ${y1o} L ${x1i} ${y1i} A ${r} ${r} 0 ${large} 0 ${x0i} ${y0i} Z`;
}

interface SimplePieProps {
  data: PieDatum[];
  height?: number;
  maxSize?: number;
  legend?: boolean;
  /** Texto al centro del donut (total, etiqueta). */
  centro?: { valor: string; etiqueta?: string };
}

export function SimplePie({ data, height = 150, maxSize = 168, legend = true, centro }: SimplePieProps) {
  const clean = (data || []).filter((d) => Number.isFinite(Number(d.value)) && Number(d.value) > 0);
  if (!clean.length) return <VacioChart />;
  const size = Math.min(height, maxSize);
  const total = clean.reduce((a, d) => a + Number(d.value), 0);
  const cx = size / 2, cy = size / 2;
  const R = size / 2 - 4;
  const r = R * 0.64;
  const colored = clean.map((d, i) => ({ ...d, _color: d.color || SERIES[i % SERIES.length] }));

  let start = -Math.PI / 2;
  const paths = colored.map((d, i) => {
    const frac = Number(d.value) / total;
    const a1 = start + frac * 2 * Math.PI;
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
    const p = (
      <path key={i} d={donutSegment(cx, cy, R, r, start, a1)} fill={d._color}>
        <title>{`${d.name}: ${Number(d.value).toLocaleString("es-MX")} (${(frac * 100).toFixed(1)}%)`}</title>
      </path>
    );
    start = a1;
    return p;
  });

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
          {paths}
        </svg>
        {centro ? (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="mono text-[15px] font-semibold text-foreground">{centro.valor}</span>
            {centro.etiqueta ? <span className="text-micro text-faint">{centro.etiqueta}</span> : null}
          </div>
        ) : null}
      </div>
      {legend ? (
        <ul className="min-w-[8rem] flex-1 space-y-1 text-meta">
          {colored.map((d, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 shrink-0 rounded-sm" style={{ background: d._color }} />
              <span className="truncate text-muted">{String(d.name)}</span>
              <span className="mono ml-auto tabular-nums text-body">
                {((Number(d.value) / total) * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function VacioChart({ texto = "Sin datos" }: { texto?: string }) {
  return <div className="py-8 text-center text-meta text-faint">{texto}</div>;
}
