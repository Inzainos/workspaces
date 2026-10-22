/**
 * Utilidades generales para Sentinel Omega
 */

/**
 * Fusiona clases CSS condicionales (patrón clsx/twMerge).
 * Los valores falsy se descartan.
 */
export function cn(...classes: (string | undefined | null | false | 0)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function fmtNum(valor: number | string | undefined | null, decimales = 2): string {
  if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—"
  return Number(valor).toLocaleString("es-MX", { minimumFractionDigits: decimales, maximumFractionDigits: decimales })
}

export function fmtTs(ts: unknown): string {
  if (!ts) return "—"
  const n = Number(ts)
  if (Number.isFinite(n) && n > 1e11) {
    return new Date(n).toLocaleString("es-MX", { timeZone: "America/Mexico_City" })
  }
  if (Number.isFinite(n) && n > 1e9) {
    return new Date(n * 1000).toLocaleString("es-MX", { timeZone: "America/Mexico_City" })
  }
  const s = String(ts)
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s
  return "—"
}

export function esAusente(v: unknown): boolean {
  return v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v))
}

export function riskColor(nivel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null | undefined): string {
  switch (nivel) {
    case "LOW": return "#10b981"
    case "MODERATE": return "#ffc107"
    case "HIGH": return "#ff9100"
    case "CRITICAL": return "#ff1744"
    default: return "#8a8f98"
  }
}

export function riskColorDim(nivel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null | undefined): string {
  switch (nivel) {
    case "LOW": return "rgba(16, 185, 129, 0.15)"
    case "MODERATE": return "rgba(255, 193, 7, 0.15)"
    case "HIGH": return "rgba(255, 145, 0, 0.15)"
    case "CRITICAL": return "rgba(255, 23, 68, 0.15)"
    default: return "transparent"
  }
}

export function riesgoTexto(nivel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null | undefined): string {
  switch (nivel) {
    case "LOW": return "BAJO"
    case "MODERATE": return "MEDIO"
    case "HIGH": return "ALTO"
    case "CRITICAL": return "CRÍTICO"
    default: return "SIN DATO"
  }
}

export function colorRiesgoPorValor(valor: number | null, umbrales: [number, number, number] = [5, 15, 30]): string {
  if (valor === null || valor === undefined) return "var(--color-fuente-desvanecido)"
  if (valor >= umbrales[2]) return "var(--color-critico)"
  if (valor >= umbrales[1]) return "var(--color-aviso)"
  if (valor >= umbrales[0]) return "var(--color-atencion)"
  return "var(--color-calma)"
}

export function porcentaje(num: number, total: number): number {
  if (!total || !num) return 0
  return (num / total) * 100
}
