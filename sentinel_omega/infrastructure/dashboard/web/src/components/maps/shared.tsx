import type { ReactNode } from "react";

/**
 * Compartido entre Map2D y Globe3D: mundo, tipos, codificación y leyenda.
 *
 * Sistema de diseño: el color saturado significa riesgo y nada más. El TIPO de
 * nodo (real/ghost/geobatería) es una categoría, así que va en la rampa de
 * serie desaturada; la CARGA acumulada sí es riesgo, así que usa la rampa
 * calma→atención→aviso. Lo que no se midió se dibuja distinto de lo que midió
 * cero: hueco y neutro, nunca un punto cargado.
 */

export type LngLat = [number, number];

export type NodoMapa = {
  lat: number;
  lon: number;
  tipo?: string;
  label?: string;
  /** Saturación acumulada 0..1. `undefined` = el llamador no la conoce (tabs legacy). */
  sat?: number;
  /** `false` = sin lectura. `undefined` = tabs legacy: dibujar como antes. */
  medido?: boolean;
  highlight?: boolean;
  region?: string;
  updated?: string;
};

export type SismoMapa = {
  lat: number;
  lon: number;
  mag?: number;
  label?: string;
  depthKm?: number;
  /** epoch en segundos; `undefined` = sin fecha conocida (se atenúa a 0.7). */
  ts?: number;
};

// ── Mundo (aproximado, honesto) ────────────────────────────────────────────
// Mucho más detallado que las 6 manchas anteriores: costas reconocibles,
// islas grandes y arcos. Sigue siendo "aproximado" y el caption lo dice.

const NORTEAMERICA: LngLat[] = [
  [-166, 68], [-158, 71], [-148, 70], [-136, 69], [-126, 70], [-118, 72],
  [-108, 73], [-96, 73], [-86, 70], [-82, 66], [-86, 64], [-92, 62],
  [-94, 58], [-90, 57], [-82, 55], [-79, 51], [-70, 50], [-62, 50],
  [-56, 52], [-60, 55], [-66, 58], [-74, 60], [-78, 62], [-77, 67],
  [-72, 68], [-68, 61], [-59, 56], [-64, 49], [-70, 44], [-74, 40],
  [-76, 35], [-80, 32], [-80, 27], [-81, 25], [-83, 29], [-88, 30],
  [-94, 29], [-97, 26], [-96, 22], [-92, 19], [-88, 21], [-86, 16],
  [-84, 10], [-79, 9], [-77, 8], [-81, 8], [-85, 11], [-88, 14],
  [-92, 15], [-96, 16], [-105, 20], [-110, 24], [-114, 29], [-117, 33],
  [-121, 37], [-124, 42], [-124, 48], [-128, 51], [-132, 55], [-137, 58],
  [-146, 61], [-152, 59], [-158, 56], [-164, 60],
];

const SUDAMERICA: LngLat[] = [
  [-78, 8], [-72, 12], [-66, 10], [-60, 8], [-52, 5], [-50, 0],
  [-44, -3], [-38, -5], [-35, -9], [-38, -14], [-40, -20], [-42, -23],
  [-48, -26], [-53, -33], [-57, -36], [-62, -39], [-64, -42], [-65, -46],
  [-68, -50], [-66, -54], [-69, -55], [-72, -52], [-73, -46], [-72, -40],
  [-71, -32], [-70, -24], [-70, -18], [-75, -15], [-79, -7], [-81, -3],
  [-80, 1],
];

const AFRICA: LngLat[] = [
  [-9, 32], [-6, 35], [3, 37], [11, 37], [19, 32], [29, 31],
  [33, 29], [35, 22], [37, 18], [41, 15], [43, 11], [48, 11],
  [51, 11], [45, 4], [41, -1], [40, -6], [38, -11], [35, -16],
  [33, -21], [31, -26], [28, -32], [22, -34], [18, -33], [15, -27],
  [13, -19], [12, -11], [9, -2], [8, 3], [3, 6], [-4, 5],
  [-8, 4], [-13, 9], [-17, 14], [-17, 21], [-15, 25], [-13, 28],
];

const EURASIA: LngLat[] = [
  [-9, 43], [-9, 37], [-1, 38], [1, 41], [3, 42], [7, 44],
  [10, 44], [13, 45], [15, 40], [18, 40], [16, 38], [19, 40],
  [21, 38], [23, 36], [26, 38], [29, 36], [31, 36], [34, 36],
  [36, 36], [36, 33], [35, 29], [38, 22], [40, 17], [43, 13],
  [48, 14], [52, 17], [56, 19], [59, 22], [61, 25], [66, 25],
  [67, 23], [70, 21], [72, 19], [73, 15], [76, 9], [79, 10],
  [80, 13], [81, 16], [84, 19], [87, 21], [90, 22], [92, 21],
  [94, 18], [97, 13], [99, 9], [100, 4], [103, 1], [105, 3],
  [104, 8], [100, 13], [102, 12], [105, 10], [107, 11], [109, 14],
  [107, 18], [106, 20], [108, 21], [110, 21], [114, 22], [117, 24],
  [120, 28], [122, 31], [120, 34], [122, 37], [121, 39], [124, 40],
  [126, 38], [129, 35], [127, 34], [125, 38], [128, 40], [131, 43],
  [135, 44], [138, 47], [141, 50], [141, 53], [138, 55], [141, 58],
  [143, 59], [147, 60], [153, 60], [157, 61], [160, 60], [163, 58],
  [170, 62], [176, 65], [179, 66], [178, 70], [170, 70], [160, 71],
  [150, 72], [140, 73], [128, 73], [113, 74], [100, 76], [86, 75],
  [73, 73], [66, 70], [57, 69], [48, 68], [44, 66], [38, 64],
  [33, 66], [30, 70], [26, 71], [20, 70], [15, 68], [12, 65],
  [10, 63], [8, 61], [10, 58], [7, 58], [4, 56], [3, 53],
  [0, 50], [-2, 48], [-5, 48],
];

const AUSTRALIA: LngLat[] = [
  [114, -22], [113, -26], [115, -33], [118, -35], [124, -33], [130, -32],
  [134, -33], [136, -35], [138, -35], [140, -38], [145, -39], [147, -38],
  [150, -37], [152, -33], [153, -28], [153, -25], [150, -22], [147, -19],
  [143, -17], [142, -13], [141, -12], [137, -12], [136, -15], [135, -12],
  [132, -11], [130, -13], [128, -15], [125, -16], [122, -18], [119, -20],
];

const GROENLANDIA: LngLat[] = [
  [-58, 76], [-56, 72], [-52, 68], [-48, 61], [-53, 60], [-55, 63],
  [-60, 66], [-68, 70], [-73, 74], [-66, 78], [-60, 80],
];

const ISLAS: LngLat[][] = [
  // Gran Bretaña e Irlanda
  [[-5, 50], [1, 51], [0, 53], [-2, 55], [-2, 58], [-4, 58.5], [-6, 57], [-8, 54], [-6, 52]],
  [[-10, 52], [-6, 52], [-6, 55], [-8, 55], [-10, 54]],
  // Islandia
  [[-24, 65], [-20, 66.5], [-15, 66], [-14, 65], [-17, 64], [-21, 63.5]],
  // Japón
  [[130, 31], [132, 34], [136, 35], [140, 36], [141, 39], [140, 42], [143, 43], [145, 44], [143, 45.5], [141, 45], [139, 42], [137, 40], [136, 37], [133, 35], [131, 33]],
  // Madagascar
  [[44, -25], [47, -25], [50, -19], [49, -13], [46, -16], [44, -20]],
  // Nueva Zelanda
  [[172, -34], [175, -37], [178, -38], [176, -41], [172, -44], [168, -46], [166, -46], [170, -42], [173, -38]],
  // Sumatra / Java
  [[95, 5], [98, 3], [101, 0], [104, -4], [106, -6], [103, -5], [99, -1], [96, 3]],
  [[105, -6], [110, -7], [114, -8], [115, -9], [110, -8], [106, -7]],
  // Borneo / Nueva Guinea / Filipinas
  [[109, 1], [113, 4], [117, 7], [119, 4], [118, 0], [114, -3], [110, -2]],
  [[131, -1], [136, -2], [141, -3], [146, -6], [150, -9], [147, -10], [142, -8], [137, -6], [133, -3], [130, -2]],
  [[120, 18], [122, 15], [124, 11], [126, 7], [125, 9], [122, 13], [121, 16]],
  // Cuba / Sri Lanka
  [[-85, 22], [-80, 23], [-75, 20], [-77, 20], [-82, 21]],
  [[80, 6], [82, 7], [81, 9], [80, 8]],
];

export const CONTINENTES: LngLat[][] = [
  NORTEAMERICA, SUDAMERICA, EURASIA, AFRICA, AUSTRALIA, GROENLANDIA, ...ISLAS,
];

// ── Codificación ───────────────────────────────────────────────────────────

const COLOR_TIPO: Record<string, string> = {
  real: "var(--color-serie-1)",
  ghost: "var(--color-base-500)",
  geobattery: "var(--color-serie-2)",
};

export const colorTipo = (tipo?: string): string =>
  COLOR_TIPO[(tipo || "real").toLowerCase()] ?? COLOR_TIPO.real;

/** Carga acumulada = riesgo. Umbrales alineados con el ranking de tensión. */
export function colorRiesgoSat(sat: number): string {
  if (sat >= 0.8) return "var(--color-aviso)";
  if (sat >= 0.6) return "var(--color-atencion)";
  return "var(--color-calma)";
}

/** Un sismo ocurrió: es el riesgo materializado, en la rampa por magnitud. */
export function colorSismo(mag: number): string {
  if (mag >= 6) return "var(--color-critico)";
  if (mag >= 5) return "var(--color-aviso)";
  return "var(--color-atencion)";
}

/** Recencia: 0.95 recién ocurrido, decae lineal hasta 0.35 a los 60 días. */
export function alfaSismo(ts?: number, ahoraS?: number): number {
  if (ts == null || !Number.isFinite(ts)) return 0.7;
  const ahora = ahoraS ?? Date.now() / 1000;
  const dias = Math.max(0, (ahora - ts) / 86400);
  return 0.95 - 0.6 * Math.min(1, dias / 60);
}

export function fmtEdadSismo(ts?: number, ahoraS?: number): string {
  if (ts == null || !Number.isFinite(ts)) return "fecha desconocida";
  const ahora = ahoraS ?? Date.now() / 1000;
  const h = Math.max(0, (ahora - ts) / 3600);
  if (h < 1) return "hace menos de 1 h";
  if (h < 24) return `hace ${Math.floor(h)} h`;
  const d = Math.floor(h / 24);
  if (d < 30) return `hace ${d} día${d === 1 ? "" : "s"}`;
  return `hace ${Math.floor(d / 30)} mes(es)`;
}

export const fmtTipo = (tipo?: string): string => {
  const t = (tipo || "").toLowerCase();
  if (t === "geobattery" || t.includes("geo")) return "geobatería";
  if (t.includes("ghost") || t.includes("fantasma")) return "ghost";
  return t || "real";
};

/** Ficha de nodo para la línea de hover. La ausencia se nombra, no se inventa. */
export function infoNodo(n: NodoMapa): string {
  const partes = [n.label || "nodo", fmtTipo(n.tipo)];
  if (n.medido === false) {
    partes.push("sin lectura de saturación");
  } else if (typeof n.sat === "number") {
    partes.push(`saturación ${n.sat.toFixed(2)}`);
  }
  if (n.region) partes.push(n.region);
  if (n.updated) partes.push(`lectura ${n.updated}`);
  return partes.join(" · ");
}

export function infoSismo(q: SismoMapa): string {
  const partes = [`M${(q.mag ?? 0).toFixed(1)}`];
  if (typeof q.depthKm === "number") partes.push(`${q.depthKm.toFixed(0)} km de profundidad`);
  if (q.label) partes.push(q.label);
  partes.push(fmtEdadSismo(q.ts));
  return partes.join(" · ");
}

// ── Leyenda compartida ─────────────────────────────────────────────────────

function Swatch({ children }: { children: ReactNode }) {
  return <span className="mr-1.5 inline-flex h-3 w-3 items-center justify-center">{children}</span>;
}

export function LeyendaMapa() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-meta text-muted">
      <span>
        <Swatch>
          <i className="h-2 w-2 rounded-full" style={{ background: "var(--color-serie-1)" }} />
        </Swatch>
        real
      </span>
      <span>
        <Swatch>
          <i className="h-2 w-2 rounded-full" style={{ background: "var(--color-base-500)" }} />
        </Swatch>
        ghost
      </span>
      <span>
        <Swatch>
          <i className="h-2 w-2 rounded-full" style={{ background: "var(--color-serie-2)" }} />
        </Swatch>
        geobatería
      </span>
      <span>
        <Swatch>
          <i className="h-2 w-2 rounded-full border border-base-500 bg-transparent" />
        </Swatch>
        sin lectura
      </span>
      <span title="El aro y el tamaño del nodo crecen con la saturación acumulada (tope 1.0)">
        carga:
        <Swatch>
          <i className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--color-calma)" }} />
        </Swatch>
        <Swatch>
          <i className="h-2 w-2 rounded-full" style={{ background: "var(--color-atencion)" }} />
        </Swatch>
        <Swatch>
          <i className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--color-aviso)" }} />
        </Swatch>
      </span>
      <span title="Color por magnitud; la opacidad decae con la antigüedad (60 días)">
        sismo:
        <Swatch>
          <i className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--color-atencion)" }} />
        </Swatch>
        M≥4.5
        <Swatch>
          <i className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--color-critico)" }} />
        </Swatch>
        M≥6
      </span>
      <span>
        <Swatch>
          <i className="h-1.5 w-1.5 rounded-full bg-base-100 ring-1 ring-serie-1" />
        </Swatch>
        Tlaxcala
      </span>
    </div>
  );
}
