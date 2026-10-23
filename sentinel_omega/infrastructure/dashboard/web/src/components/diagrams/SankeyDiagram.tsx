/**
 * SANKEY — flujo de consenso Padre → Juez.
 *
 * Muestra cómo fluyen las señales de los bots hacia el Padre, del Padre al
 * Juez, y del Juez al veredicto final. Cada ancho de banda es proporcional
 * al volumen de señales/veredictos.
 *
 * Diseño: colores neutros (no se usa el rojo de riesgo para flujo);
 * el único color de riesgo aparece si hay un veredicto FALLO.
 */

interface NodoSankey {
  id: string;
  label: string;
  valor: number;
  color?: string;
}
interface EnlaceSankey {
  origen: string;
  destino: string;
  valor: number;
  color?: string;
}

interface SankeyDiagramProps {
  nodos: NodoSankey[];
  enlaces: EnlaceSankey[];
  alto?: number;
}

export function SankeyDiagram({ nodos, enlaces, alto = 220 }: SankeyDiagramProps) {
  if (nodos.length === 0 || enlaces.length === 0) return null;

  const w = 720;
  const h = alto;
  const mL = 140, mR = 140, mT = 20, mB = 20;
  const plotW = w - mL - mR;
  const plotH = h - mT - mB;

  // Calcular flujos entrantes/salientes por nodo
  const entradas: Record<string, number> = {};
  const salidas: Record<string, number> = {};
  enlaces.forEach((e) => {
    entradas[e.destino] = (entradas[e.destino] || 0) + e.valor;
    salidas[e.origen] = (salidas[e.origen] || 0) + e.valor;
  });

  // Valor de cada nodo = max(entrada, salida)
  const valorNodo: Record<string, number> = {};
  nodos.forEach((n) => {
    valorNodo[n.id] = Math.max(entradas[n.id] || 0, salidas[n.id] || 0, n.valor);
  });

  const total = Math.max(...Object.values(valorNodo), 1);

  // Posiciones X por capa
  const capas: Record<string, number> = {};
  nodos.forEach((n) => {
    if (n.id.startsWith("bot")) capas[n.id] = 0;
    else if (n.id === "padre") capas[n.id] = 1;
    else if (n.id === "juez") capas[n.id] = 2;
    else capas[n.id] = 3;
  });

  // Y dentro de cada capa (apilado)
  const ocupados: Record<number, number> = {}; // capa → y acumulado
  const posY: Record<string, number> = {};
  nodos.forEach((n) => {
    const capa = capas[n.id];
    const y = (ocupados[capa] || mT) + valorNodo[n.id] / 2;
    posY[n.id] = y;
    ocupados[capa] = (ocupados[capa] || mT) + valorNodo[n.id];
  });

  // Normalizar Y para que quepa en plotH
  const ocupacionMax = Math.max(...Object.values(ocupados), mT + plotH);
  const escalaY = plotH / (ocupacionMax - mT);
  const yFinal: Record<string, number> = {};
  nodos.forEach((n) => {
    const capa = capas[n.id];
    const yBase = (ocupados[capa] || mT) - valorNodo[n.id] / 2;
    yFinal[n.id] = mT + (yBase - mT) * escalaY + valorNodo[n.id] / 2 * escalaY;
  });

  const xPorCapa: Record<number, number> = {};
  const capasUnicas = [...new Set(Object.values(capas))].sort((a, b) => a - b);
  capasUnicas.forEach((capa, i) => {
    xPorCapa[capa] = mL + (i / (capasUnicas.length - 1)) * plotW;
  });

  return (
    <div className="flex flex-col gap-2">
      <svg width="100%" height={alto} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Flujo de consenso Padre → Juez">
        {/* Enlaces */}
        {enlaces.map((e, i) => {
          const x1 = xPorCapa[capas[e.origen]] + (capas[e.origen] === capasUnicas.length - 1 ? 0 : 0);
          const x2 = xPorCapa[capas[e.destino]];
          const y1 = yFinal[e.origen];
          const y2 = yFinal[e.destino];
          const grosor = Math.max(1, (e.valor / total) * plotH);
          const color = e.valor > 0 ? "color-mix(in oklch, var(--color-serie-1) 40%, transparent)" : "var(--color-base-600)";

          // Curva Bézier suave
          const cp1x = x1 + (x2 - x1) * 0.5;
          const cp2x = x2 - (x2 - x1) * 0.5;

          return (
            <path
              key={`e${i}`}
              d={`M ${x1} ${y1} C ${cp1x} ${y1} ${cp2x} ${y2} ${x2} ${y2}`}
              fill="none"
              stroke={color}
              strokeWidth={grosor}
              strokeOpacity={0.5}
            />
          );
        })}
        {/* Nodos */}
        {nodos.map((n) => {
          const x = xPorCapa[capas[n.id]];
          const y = yFinal[n.id];
          const r = Math.max(6, Math.min(14, Math.sqrt(valorNodo[n.id] / total) * 20));
          const esPadre = n.id === "padre";
          const esJuez = n.id === "juez";
          return (
            <g key={n.id}>
              <circle cx={x} cy={y} r={r} fill={n.color || (esPadre ? "var(--color-serie-1)" : esJuez ? "var(--color-serie-2)" : "var(--color-base-600)")} />
              <text x={x} y={y + 4} textAnchor="middle" fill="var(--color-base-100)" style={{ fontSize: 10, fontFamily: "var(--font-mono)" }}>
                {n.label}
              </text>
              <text x={x} y={y - r - 6} textAnchor="middle" fill="var(--color-faint)" style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}>
                {valorNodo[n.id].toLocaleString("es-MX")}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-4 text-meta text-muted text-micro">
        {nodos.map((n) => (
          <span key={n.id} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: n.color || "var(--color-base-600)" }} />
            <span>{n.label}</span>
            <span className="mono">{valorNodo[n.id].toLocaleString("es-MX")}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
