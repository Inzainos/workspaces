/**
 * HEATMAP CALENDARIO — calor de eventos por hora × día.
 *
 * Diseño basado en Business Intelligence: densidad sobre tiempo, no
 * precisión puntual. Cada celda = una hora; el color = intensidad (0 = sin
 * datos, rampa neutra = riesgo). Sirve para ver patrones de recurrencia
 * sin afirmar causalidad.
 */

interface CalEvento {
  ts: number; // epoch segundos
  intensidad: number; // 0..1
  label?: string;
}

interface HeatmapChartProps {
  datos: CalEvento[];
  /** Título de la métrica que se está mostrando (ej. "Fantasmas M≥4.5") */
  metrica?: string;
  /** Horas de ventana (ej. 24 = último día) */
  horasVentana?: number;
  /** Cuántas horas mostrar en el eje X */
  horasEje?: number;
  /** Altura del SVG */
  alto?: number;
}

export function HeatmapChart({
  datos,
  metrica,
  horasVentana = 72,
  horasEje = 24,
  alto = 160,
}: HeatmapChartProps) {
  const ahora = Math.max(...datos.map((d) => d.ts), Date.now() / 1000);
  const desde = ahora - horasVentana * 3600;

  // Agrupar por día y hora
  const grilla: Record<string, number> = {};
  datos.forEach((d) => {
    if (d.ts < desde) return;
    const fecha = new Date(d.ts * 1000);
    const dia = fecha.toISOString().slice(0, 10);
    const hora = fecha.getUTCHours();
    const clave = `${dia}:${hora}`;
    grilla[clave] = Math.max(grilla[clave] ?? 0, d.intensidad);
  });

  const claves = Object.keys(grilla).sort();
  if (claves.length === 0) return null;

  // Determinar días únicos y horas del día
  const dias = Array.from(new Set(claves.map((c) => c.slice(0, 10)))).sort();
  const horas = Array.from(new Set(claves.map((c) => c.slice(11, 13)))).sort();

  const w = 720;
  const h = alto;
  const mL = 40, mR = 10, mT = 24, mB = 24;
  const celdasX = Math.min(horasEje, horas.length);
  const celdasY = Math.min(7, dias.length); // máximo 7 días
  const cellW = (w - mL - mR) / celdasX;
  const cellH = (h - mT - mB) / celdasY;

  // Día más reciente a la derecha
  const diasVisibles = dias.slice(-celdasX);
  const horasVisibles = horas.slice(-celdasY).reverse(); // 0 arriba

  // Escala de color neutra: gris → verde suave (solo para intensidad)
  const colorCelda = (v: number) => {
    if (v <= 0) return "var(--color-base-800)";
    if (v < 0.33) return "color-mix(in oklch, var(--color-calma) 30%, transparent)";
    if (v < 0.66) return "color-mix(in oklch, var(--color-atencion) 30%, transparent)";
    return "color-mix(in oklch, var(--color-critico) 30%, transparent)";
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="etiqueta">{metrica ?? "Eventos por hora · día"}</span>
        <span className="mono text-micro text-faint">
          {diasVisibles.length} días · últimas {horasVentana} h
        </span>
      </div>
      <svg width="100%" height={alto} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Calor de eventos por hora y día">
        {/* Eje X: días */}
        {diasVisibles.map((dia, i) => {
          const x = mL + i * cellW + cellW / 2;
          return (
            <text key={`dx${i}`} x={x} y={h - 6} textAnchor="middle" fill="var(--color-faint)" style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}>
              {dia.slice(5)}
            </text>
          );
        })}
        {/* Eje Y: horas */}
        {horasVisibles.map((hora, i) => {
          const y = mT + i * cellH + cellH / 2;
          return (
            <text key={`hy${i}`} x={mL - 5} y={y + 3} textAnchor="end" fill="var(--color-faint)" style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}>
              {hora}:00
            </text>
          );
        })}
        {/* Celdas */}
        {claves.map((clave) => {
          const dia = clave.slice(0, 10);
          const hora = clave.slice(11, 13);
          const di = diasVisibles.indexOf(dia);
          const hi = horasVisibles.indexOf(hora);
          if (di < 0 || hi < 0) return null;
          const x = mL + di * cellW;
          const y = mT + hi * cellH;
          const v = grilla[clave];
          return (
            <rect
              key={clave}
              x={x + 1}
              y={y + 1}
              width={cellW - 2}
              height={cellH - 2}
              fill={colorCelda(v)}
              stroke="var(--color-base-700)"
              strokeWidth={0.5}
              opacity={v > 0 ? 0.9 : 0.35}
            >
              <title>{`${dia} ${hora}:00 — ${(v * 100).toFixed(0)}%`}</title>
            </rect>
          );
        })}
      </svg>
      <div className="flex items-center gap-3 text-meta text-muted text-micro">
        <span>sin datos</span>
        <span className="h-2 w-2 rounded-full inline-block" style={{ background: "color-mix(in oklch, var(--color-calma) 30%, transparent)" }} />
        <span>bajo</span>
        <span className="h-2 w-2 rounded-full inline-block" style={{ background: "color-mix(in oklch, var(--color-critico) 30%, transparent)" }} />
        <span>alto</span>
      </div>
    </div>
  );
}
