import { useMemo } from "react";

/**
 * CIMÁTICA COMO FIGURA — la vibración hecha visible (skill de cimática,
 * ~/conocimiento: Chladni/Jenny). La clave del patrón es un hash de
 * telemetría; hasta ahora se mostraba CRUDA (un muro de texto ilegible).
 * Esto la convierte en una FIGURA geométrica DETERMINISTA: la misma clave
 * siempre dibuja la misma figura — reconocible de reojo, como las
 * placas de Chladni.
 *
 * Cómo: la clave se hashea (FNV-1a) → PRNG determinista → 16 nodos sobre
 * anillos concéntricos con perturbación radial, espejados en el eje
 * vertical (las figuras de Chladni son simétricas) → SVG.
 *
 * Color: rampa NEUTRA (serie) a propósito — la figura es dato, no estado
 * de riesgo (regla 1 del sistema de diseño). Los puntos activos llevan el
 * acento tenue.
 */

function fnv1a(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** PRNG mulberry32 — determinista con la semilla del hash. */
function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function CimaticaFigura({
  clave,
  size = 140,
  puntos = 16,
}: {
  clave: string | null | undefined;
  size?: number;
  puntos?: number;
}) {
  const paths = useMemo(() => {
    if (!clave) return null;
    const seed = fnv1a(clave);
    const rnd = prng(seed);
    const c = size / 2;
    const R = size * 0.42;
    // 16 nodos en anillo con perturbación radial determinista
    const nodos: Array<[number, number]> = [];
    for (let i = 0; i < puntos; i++) {
      const ang = (i / puntos) * Math.PI * 2 - Math.PI / 2;
      const pert = 0.55 + rnd() * 0.45; // 0.55–1.0 del radio base
      const r = R * pert;
      nodos.push([c + Math.cos(ang) * r, c + Math.sin(ang) * r]);
    }
    // Espejo vertical (Chladni es simétrico): puntos de la izquierda
    // reflejados → figura cerrada suave
    const espejo: Array<[number, number]> = nodos.map(
      ([x, y]) => [size - x, y] as [number, number],
    );
    const polígono = [...nodos, ...espejo.reverse()];
    // Curva cerrada por puntos medios (suavizado tipo placa vibrante)
    const mid = (a: [number, number], b: [number, number]): [number, number] => [
      (a[0] + b[0]) / 2,
      (a[1] + b[1]) / 2,
    ];
    let d = "";
    for (let i = 0; i < polígono.length; i++) {
      const cur = polígono[i];
      const next = polígono[(i + 1) % polígono.length];
      const m = mid(cur, next);
      if (i === 0) d += `M ${m[0].toFixed(1)} ${m[1].toFixed(1)}`;
      else d += ` Q ${cur[0].toFixed(1)} ${cur[1].toFixed(1)} ${m[0].toFixed(1)} ${m[1].toFixed(1)}`;
    }
    d += " Z";
    // Cuerdas internas (las "líneas de nodo" de Chladni): 4 cuerdas
    // deterministas entre nodos opuestos — dan la textura de placa
    const cuerdas: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];
    for (let k = 0; k < 4; k++) {
      const i = Math.floor(rnd() * puntos);
      const j = Math.floor(rnd() * puntos);
      cuerdas.push({
        x1: nodos[i][0], y1: nodos[i][1],
        x2: espejo[j][0], y2: espejo[j][1],
      });
    }
    return { d, cuerdas, nodos, c };
  }, [clave, size, puntos]);

  if (!paths) {
    return (
      <div
        className="flex items-center justify-center rounded border border-border bg-surface-sunken"
        style={{ width: size, height: size }}
      >
        <span className="text-micro" style={{ color: "var(--color-faint)" }}>
          sin figura
        </span>
      </div>
    );
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Figura cimática del patrón actual"
    >
      <circle
        cx={paths.c} cy={paths.c} r={size * 0.46}
        fill="none" stroke="var(--color-border)" strokeWidth="1"
      />
      {paths.cuerdas.map((s, i) => (
        <line
          key={i}
          x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
          stroke="var(--color-base-600)"
          strokeWidth="0.7"
          opacity="0.5"
        />
      ))}
      <path
        d={paths.d}
        fill="color-mix(in oklch, var(--color-serie-1) 14%, transparent)"
        stroke="var(--color-serie-1)"
        strokeWidth="1.6"
      />
      {paths.nodos.map(([x, y], i) => (
        <circle
          key={i}
          cx={x} cy={y} r="1.7"
          fill="var(--color-base-300)"
        />
      ))}
    </svg>
  );
}
