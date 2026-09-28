/**
 * Primitivas de dato — Sentinel Omega
 *
 * La idea que gobierna este archivo: el tablero no debe poder mentir por
 * descuido. Cada primitiva sabe distinguir "no hay lectura" de "midió cero",
 * y el color saturado está reservado al riesgo.
 *
 * Nada aquí inventa un valor por defecto. `null`/`undefined`/`NaN` se pintan
 * con `.dato-ausente`, que es visualmente distinto de un 0 real.
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/* ========================================================================== */
/* Riesgo                                                                     */
/* ========================================================================== */

export type Nivel = "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "DESCONOCIDO";

export function nivelDe(valor?: string | null): Nivel {
  const v = String(valor || "").toUpperCase();
  if (v === "LOW" || v === "MODERATE" || v === "HIGH" || v === "CRITICAL") return v;
  return "DESCONOCIDO";
}

/** Token CSS del nivel. Se usa en `color`/`background`, nunca un hex suelto. */
export function colorNivel(nivel: Nivel): string {
  switch (nivel) {
    case "LOW":
      return "var(--color-calma)";
    case "MODERATE":
      return "var(--color-atencion)";
    case "HIGH":
      return "var(--color-aviso)";
    case "CRITICAL":
      return "var(--color-critico)";
    default:
      return "var(--color-base-600)";
  }
}

export function colorNivelDim(nivel: Nivel): string {
  switch (nivel) {
    case "LOW":
      return "var(--color-calma-dim)";
    case "MODERATE":
      return "var(--color-atencion-dim)";
    case "HIGH":
      return "var(--color-aviso-dim)";
    case "CRITICAL":
      return "var(--color-critico-dim)";
    default:
      return "transparent";
  }
}

/** Etiqueta humana: qué hacer, no cómo se llama el enum. */
export function accionNivel(nivel: Nivel): string {
  switch (nivel) {
    case "LOW":
      return "calma";
    case "MODERATE":
      return "atención";
    case "HIGH":
      return "avisar";
    case "CRITICAL":
      return "protocolo";
    default:
      return "sin lectura";
  }
}

/* ========================================================================== */
/* Valor / ausencia                                                           */
/* ========================================================================== */

export function esAusente(v: unknown): boolean {
  return v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v));
}

/**
 * Número con ausencia explícita. `digits` fija decimales; `unidad` va en un
 * span atenuado para que no compita con la cifra.
 */
export function Cifra({
  valor,
  digits = 2,
  unidad,
  className,
}: {
  valor: unknown;
  digits?: number;
  unidad?: string;
  className?: string;
}) {
  if (esAusente(valor)) {
    return (
      <span className={cn("dato-ausente", className)} title="Sin lectura — no es un cero">
        —
      </span>
    );
  }
  const n = Number(valor);
  if (!Number.isFinite(n)) {
    return (
      <span className={cn("dato-ausente", className)} title="Valor no numérico">
        —
      </span>
    );
  }
  return (
    <span className={cn("tnum", className)}>
      {n.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits })}
      {unidad ? <span className="ml-0.5 text-[0.75em] font-normal text-faint">{unidad}</span> : null}
    </span>
  );
}

/* ========================================================================== */
/* Panel                                                                      */
/* ========================================================================== */

/**
 * Contenedor base. `titulo` + `meta` forman el encabezado; `nota` es la
 * explicación al pie (por qué importa este número), que en un tablero de
 * precursores no es decoración: evita que alguien lea una correlación como
 * una causa.
 */
export function Panel({
  titulo,
  meta,
  nota,
  children,
  className,
  acento,
}: {
  titulo?: ReactNode;
  meta?: ReactNode;
  nota?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Solo para riesgo: tiñe el borde superior. */
  acento?: Nivel;
}) {
  return (
    <section
      className={cn(
        "relative rounded-lg border border-border bg-surface",
        className,
      )}
      style={
        acento && acento !== "DESCONOCIDO"
          ? { boxShadow: `inset 0 2px 0 0 ${colorNivel(acento)}` }
          : undefined
      }
    >
      {(titulo || meta) && (
        <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-4 py-2.5">
          {titulo ? <h3 className="text-body font-semibold text-foreground">{titulo}</h3> : <span />}
          {meta ? <span className="etiqueta">{meta}</span> : null}
        </header>
      )}
      <div className="p-4">{children}</div>
      {nota ? (
        <footer className="border-t border-border px-4 py-2.5 text-meta leading-relaxed text-muted">
          {nota}
        </footer>
      ) : null}
    </section>
  );
}

/* ========================================================================== */
/* Métrica                                                                    */
/* ========================================================================== */

/**
 * Métrica de tablero. `jerarquia`:
 *  - "principal": la cifra que manda en la vista (una por pantalla).
 *  - "normal":    métrica de rejilla.
 *  - "compacta":  dato de apoyo en fila densa.
 *
 * `contexto` es obligatorio en la práctica: un número sin la escala contra la
 * que se lee es ruido. Aquí es donde va "de 333 eventos" o "1× = no aporta".
 */
export function Metrica({
  etiqueta,
  valor,
  unidad,
  contexto,
  nivel,
  jerarquia = "normal",
  className,
}: {
  etiqueta: string;
  valor: ReactNode;
  unidad?: string;
  contexto?: ReactNode;
  nivel?: Nivel;
  jerarquia?: "principal" | "normal" | "compacta";
  className?: string;
}) {
  const tam =
    jerarquia === "principal"
      ? "text-[length:var(--text-hero-num)] leading-[1.02] font-bold"
      : jerarquia === "compacta"
        ? "text-[length:var(--text-read)] font-semibold"
        : "text-[length:var(--text-metric)] leading-tight font-semibold";

  return (
    <div className={cn("min-w-0", className)}>
      <div className="etiqueta truncate">{etiqueta}</div>
      <div
        className={cn("mt-1 tracking-tight tnum", tam)}
        style={nivel ? { color: colorNivel(nivel) } : { color: "var(--color-foreground)" }}
      >
        {valor}
        {unidad ? <span className="ml-1 text-[0.45em] font-medium text-faint">{unidad}</span> : null}
      </div>
      {contexto ? (
        <div className="mt-1 text-meta leading-snug text-muted" style={{ textWrap: "pretty" }}>
          {contexto}
        </div>
      ) : null}
    </div>
  );
}

/* ========================================================================== */
/* Escala de riesgo                                                           */
/* ========================================================================== */

/**
 * Fantasma sobre su escala real (0–15–30–50+), con los umbrales dibujados.
 * Un gauge de aguja no dice dónde están los cortes; esto sí. Es la diferencia
 * entre "8.11" y "8.11, y el siguiente umbral está en 15".
 */
export function EscalaRiesgo({
  valor,
  max = 50,
  umbrales = [15, 30],
}: {
  valor: number | null | undefined;
  max?: number;
  umbrales?: number[];
}) {
  const v = esAusente(valor) ? null : Number(valor);
  const pct = v === null ? 0 : Math.max(0, Math.min(100, (v / max) * 100));
  const nivel: Nivel =
    v === null ? "DESCONOCIDO" : v >= 30 ? "CRITICAL" : v >= 15 ? "HIGH" : v >= 5 ? "MODERATE" : "LOW";

  return (
    <div className="space-y-1.5">
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-surface-sunken">
        {/* Zonas: teñidas muy suave, solo para ubicar los cortes. */}
        <div className="absolute inset-y-0 left-0 w-full opacity-[0.28]">
          <div
            className="absolute inset-y-0 left-0"
            style={{ width: `${(5 / max) * 100}%`, background: "var(--color-calma)" }}
          />
          <div
            className="absolute inset-y-0"
            style={{
              left: `${(5 / max) * 100}%`,
              width: `${((15 - 5) / max) * 100}%`,
              background: "var(--color-atencion)",
            }}
          />
          <div
            className="absolute inset-y-0"
            style={{
              left: `${(15 / max) * 100}%`,
              width: `${((30 - 15) / max) * 100}%`,
              background: "var(--color-aviso)",
            }}
          />
          <div
            className="absolute inset-y-0"
            style={{
              left: `${(30 / max) * 100}%`,
              right: 0,
              background: "var(--color-critico)",
            }}
          />
        </div>
        {/* Marca del valor: la única parte opaca. */}
        {v !== null && (
          <div
            className="absolute inset-y-0 w-[3px] rounded-full"
            style={{ left: `calc(${pct}% - 1.5px)`, background: colorNivel(nivel) }}
          />
        )}
        {umbrales.map((u) => (
          <div
            key={u}
            className="absolute inset-y-0 w-px bg-base-400/50"
            style={{ left: `${(u / max) * 100}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between text-micro text-faint mono">
        <span>0</span>
        {umbrales.map((u) => (
          <span key={u}>{u}</span>
        ))}
        <span>{max}+</span>
      </div>
    </div>
  );
}

/* ========================================================================== */
/* Estado de fuente                                                           */
/* ========================================================================== */

/**
 * Chip de fuente. CONGELADO es un estado de primera clase: una fuente puede
 * estar fresquísima y no estar midiendo nada (Tomsk sirvió la misma imagen
 * durante días). Frescura ≠ validez.
 */
export function ChipFuente({
  nombre,
  estado,
  edadH,
  nota,
}: {
  nombre: string;
  estado: string;
  edadH?: number | null;
  nota?: string;
}) {
  const e = String(estado || "").toUpperCase();
  const estilo =
    e === "LIVE"
      ? { color: "var(--color-calma)", background: "var(--color-calma-dim)", borderColor: "var(--color-calma)" }
      : e === "LOCF_ACTIVE"
        ? { color: "var(--color-atencion)", background: "var(--color-atencion-dim)", borderColor: "var(--color-atencion)" }
        : e === "CONGELADO"
          ? { color: "var(--color-aviso)", background: "var(--color-aviso-dim)", borderColor: "var(--color-aviso)" }
          : e === "STALE"
            ? { color: "var(--color-critico)", background: "var(--color-critico-dim)", borderColor: "var(--color-critico)" }
            : { color: "var(--color-faint)", background: "transparent", borderColor: "var(--color-border)" };

  const edad =
    edadH == null || !Number.isFinite(Number(edadH))
      ? "—"
      : Number(edadH) < 1
        ? `${Math.round(Number(edadH) * 60)}m`
        : Number(edadH) < 48
          ? `${Number(edadH).toFixed(1)}h`
          : `${Math.round(Number(edadH) / 24)}d`;

  return (
    <span
      title={nota ? `${nombre}: ${e} · hace ${edad}\n${nota}` : `${nombre}: ${e} · hace ${edad}`}
      className="mono inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-micro"
      style={{ ...estilo, borderColor: `color-mix(in oklch, ${estilo.borderColor} 45%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: estilo.color }} />
      {nombre}
      <span className="opacity-60">{edad}</span>
      {e === "CONGELADO" ? <span className="opacity-90">⚠</span> : null}
    </span>
  );
}

/* ========================================================================== */
/* Veredicto                                                                  */
/* ========================================================================== */

/**
 * Barra de veredictos del Juez: aciertos / falsos positivos / fallos en
 * proporción real, con los tres números a la vista.
 *
 * Existe porque el KPI de "asertividad" deja los falsos positivos FUERA del
 * denominador: 98.6 % suena impecable y esconde 1.651 falsas alarmas. Aquí no
 * se pueden esconder — ocupan su ancho.
 */
export function BarraVeredictos({
  aciertos,
  falsosPositivos,
  fallos,
}: {
  aciertos: number;
  falsosPositivos: number;
  fallos: number;
}) {
  const total = aciertos + falsosPositivos + fallos;
  if (!total) return <div className="text-meta text-muted">Sin veredictos resueltos.</div>;
  const p = (n: number) => (n / total) * 100;

  const filas = [
    { k: "aciertos", n: aciertos, c: "var(--color-calma)", t: "Acertó (incluye los silencios en calma)" },
    { k: "falsas alarmas", n: falsosPositivos, c: "var(--color-aviso)", t: "Avisó y no pasó nada" },
    { k: "omisiones", n: fallos, c: "var(--color-critico)", t: "Pasó algo y no avisó — pesa 10×" },
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-surface-sunken">
        {filas.map((f) =>
          f.n > 0 ? (
            <div key={f.k} title={`${f.t}: ${f.n.toLocaleString("es-MX")}`} style={{ width: `${p(f.n)}%`, background: f.c }} />
          ) : null,
        )}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {filas.map((f) => (
          <li key={f.k} className="flex items-baseline gap-1.5 text-meta" title={f.t}>
            <span className="h-2 w-2 shrink-0 rounded-sm" style={{ background: f.c }} />
            <span className="text-muted">{f.k}</span>
            <span className="mono font-semibold text-foreground">{f.n.toLocaleString("es-MX")}</span>
            <span className="mono text-faint">{p(f.n).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ========================================================================== */
/* Muro                                                                       */
/* ========================================================================== */

/** Las 5 paredes como segmentos discretos. Un 2/5 debe verse como 2 de 5. */
export function SegmentosMuro({
  activos,
  total = 5,
  breach,
}: {
  activos: number | null | undefined;
  total?: number;
  breach?: boolean;
}) {
  const n = esAusente(activos) ? null : Number(activos);
  return (
    <div className="flex items-center gap-1.5" title={`${n ?? "—"} de ${total} paredes activas`}>
      {Array.from({ length: total }, (_, i) => {
        const on = n !== null && i < n;
        return (
          <div
            key={i}
            className="h-6 flex-1 rounded-sm border transition-colors"
            style={{
              background: on ? (breach ? "var(--color-critico)" : "var(--color-atencion)") : "var(--color-surface-sunken)",
              borderColor: on
                ? breach
                  ? "var(--color-critico)"
                  : "var(--color-atencion)"
                : "var(--color-border)",
              opacity: on ? 0.9 : 1,
            }}
          />
        );
      })}
    </div>
  );
}

/* ========================================================================== */
/* Vacío / error                                                              */
/* ========================================================================== */

export function SinDatos({ titulo, detalle }: { titulo: string; detalle?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface-sunken/60 px-4 py-8 text-center">
      <div className="text-body font-medium text-body">{titulo}</div>
      {detalle ? <div className="mt-1 text-meta text-muted">{detalle}</div> : null}
    </div>
  );
}

export function BannerError({ mensaje }: { mensaje: string }) {
  return (
    <div
      className="rounded-lg border px-4 py-3 text-body"
      style={{
        borderColor: "color-mix(in oklch, var(--color-critico) 45%, transparent)",
        background: "var(--color-critico-dim)",
        color: "var(--color-critico)",
      }}
    >
      {mensaje}
    </div>
  );
}
