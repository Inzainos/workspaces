/**
 * Cliente HTTP del dashboard — superficie completa, suelta y HONESTA.
 *
 * Endpoints verificados contra api.py (grep de @app.get, regla 0 — no
 * supuestos). Mantiene los métodos de la reestructuración (agents, estado,
 * loki_kp, padron) y RESTAURA los del cliente tipado original, porque los
 * tabs que siguen montados llaman con esas firmas: sismos(min, limit),
 * cimatica(limit, ambito), alertas, aciertos, ask… Sin ellos, tsc falla
 * en cascada y el build muere.
 *
 * estadoVivo apunta a /api/estado-vivo (el JSON unificado del launcher:
 * ok, auditoria, ciclo, senales, tono, cimatica_top…) — NO a /api/consenso,
 * que es otro contrato. Corregido tras el hallazgo del 10-22.
 */
const BASE = import.meta.env.VITE_API_BASE ?? ""

export async function apiRequest(method: string, path: string, body?: any): Promise<any> {
  const url = `${BASE}${path}`
  const opts: RequestInit = { method, headers: { "Content-Type": "application/json" } }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(url, opts)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} en ${path}`)
  }
  return res.json()
}

export function apiGet(path: string): Promise<any> {
  return apiRequest("GET", path)
}

export function apiPost(path: string, body: any): Promise<any> {
  return apiRequest("POST", path, body)
}

export const api = {
  // ── Estado del sistema ────────────────────────────────────────────────
  health: () => apiGet("/api/health"),
  healthApis: () => apiGet("/api/health/apis"),
  overview: () => apiGet("/api/overview"),
  estadoVivo: () => apiGet("/api/estado-vivo"),
  unificado: () => apiGet("/api/unificado"),
  agente: () => apiGet("/api/agente"),
  ask: (question: string) => apiPost("/api/ask", { question }),

  // ── Telemetría cruda ─────────────────────────────────────────────────
  telemetry: () => apiGet("/api/telemetry"),
  telemetryHistory: (limit = 48) => apiGet(`/api/telemetry/history?limit=${limit}`),
  climaEspacial: (limit = 80) => apiGet(`/api/clima_espacial?limit=${limit}`),
  schumannVivo: (limit = 120) => apiGet(`/api/schumann_vivo?limit=${limit}`),
  delta: (limit = 80) => apiGet(`/api/delta?limit=${limit}`),

  // ── Catálogos y señales ───────────────────────────────────────────────
  precursores: (limit = 50) => apiGet(`/api/precursores?limit=${limit}`),
  muro: (limit = 50) => apiGet(`/api/muro?limit=${limit}`),
  nodos: () => apiGet("/api/nodos"),
  sismos: (min = 4.5, limit = 200) => apiGet(`/api/sismos?min_magnitude=${min}&limit=${limit}`),
  ciclos: (limit = 50) => apiGet(`/api/ciclos?limit=${limit}`),
  detecciones: (limit = 100) => apiGet(`/api/detecciones?limit=${limit}`),
  alertas: (limit = 50) => apiGet(`/api/alertas?limit=${limit}`),
  aciertos: (limit = 100) => apiGet(`/api/aciertos?limit=${limit}`),

  // ── Cimática ─────────────────────────────────────────────────────────
  cimatica: (limit = 50, ambito?: string) =>
    apiGet(`/api/cimatica?limit=${limit}${ambito ? `&ambito=${encodeURIComponent(ambito)}` : ""}`),
  cimaticaAhora: () => apiGet("/api/cimatica/ahora"),

  // ── Bots / modelos / Juez ─────────────────────────────────────────────
  bots: (limit?: number) => apiGet(`/api/bots${limit ? `?limit=${limit}` : ""}`),
  sesgo: () => apiGet("/api/sesgo"),
  aprendizaje: () => apiGet("/api/aprendizaje"),
  firmas: () => apiGet("/api/firmas"),
  modelos: () => apiGet("/api/modelos"),
  juez: (limit = 100, fase = "viva") => apiGet(`/api/juez?limit=${limit}&fase=${fase}`),
  layers: () => apiGet("/api/layers"),
  lag: () => apiGet("/api/lag"),
  muroLags: () => apiGet("/api/muro_lags"),
  correlaciones: () => apiGet("/api/correlaciones"),
  consenso: (limit = 50) => apiGet(`/api/consenso?limit=${limit}`),
  heatmaps: () => apiGet("/api/heatmaps"),

  // ── Reportes y estado de canales ──────────────────────────────────────
  reportes: (name?: string) => apiGet(`/api/reportes${name ? `?name=${encodeURIComponent(name)}` : ""}`),
  telegramStatus: () => apiGet("/api/telegram/status"),

  // ── Aliases de la reestructuración (los mantengo: sus tabs los usan) ──
  agents: () => apiGet("/api/agente"),
  estado: () => apiGet("/api/overview"),
  loki_kp: (limit = 50) => apiGet(`/api/bots?bot=loki&limit=${limit}`),
  padron: (limit = 50) => apiGet(`/api/bots?bot=padron&limit=${limit}`),
}
