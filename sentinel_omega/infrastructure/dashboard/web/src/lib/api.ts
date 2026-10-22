/**
 * Cliente HTTP para llamadas a la API de Sentinel Omega
 * Todas las peticiones van contra el backend de FastAPI en el mismo origen
 */
const BASE = import.meta.env.VITE_API_BASE ?? ""

export async function apiRequest(method: string, path: string, body?: any): Promise<any> {
  const url = `${BASE}${path}`
  const opts: RequestInit = { method, headers: { "Content-Type": "application/json" } }
  if (body) opts.body = JSON.stringify(body)
  try {
    const res = await fetch(url, opts)
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`)
    }
    return res.json()
  } catch (e) {
    throw new Error(`Error en petición a ${path}: ${e}`)
  }
}

/**
 * GET wrapper
 */
export function apiGet(path: string): Promise<any> {
  return apiRequest("GET", path)
}

/**
 * POST wrapper
 */
export function apiPost(path: string, body: any): Promise<any> {
  return apiRequest("POST", path, body)
}

/**
 * Objeto api con métodos para cada endpoint del dashboard.
 * Mapea los nombres que usan las pestañas a las rutas de FastAPI.
 */
export const api = {
  overview: (params?: string) => apiGet(`/api/overview${params ? `?${params}` : ""}`),
  healthApis: () => apiGet("/api/health/apis"),
  telemetry: () => apiGet("/api/telemetry"),
  telemetryHistory: (limit = 48) => apiGet(`/api/telemetry/history?limit=${limit}`),
  climaEspacial: (limit = 80) => apiGet(`/api/sismos?limit=${limit}`),
  schumannVivo: (limit = 120) => apiGet(`/api/cimatica?vivo=1&limit=${limit}`),
  delta: (limit = 80) => apiGet(`/api/bots?bot=delta&limit=${limit}`),
  cimaticaAhora: () => apiGet("/api/cimatica/ahora"),
  cimatica: (params?: string) => apiGet(`/api/cimatica${params ? `?${params}` : ""}`),
  precursores: (limit = 80) => apiGet(`/api/precursores?limit=${limit}`),
  muro: () => apiGet("/api/muro"),
  muroLags: () => apiGet("/api/muro_lags"),
  firmas: (params?: string) => apiGet(`/api/firmas${params ? `?${params}` : ""}`),
  bots: (limit = 50) => apiGet(`/api/bots?limit=${limit}`),
  juez: (limit = 80, fase = "viva") => apiGet(`/api/juez?limit=${limit}&fase=${fase}`),
  layers: () => apiGet("/api/layers"),
  modelos: () => apiGet("/api/modelos"),
  reportes: (name?: string) => apiGet(`/api/reportes${name ? `?name=${encodeURIComponent(name)}` : ""}`),
  nodos: () => apiGet("/api/nodos"),
  sismos: (limit = 50) => apiGet(`/api/sismos?limit=${limit}`),
  agents: () => apiGet("/api/agente"),
  estado: () => apiGet("/api/overview"),
  estadoVivo: () => apiGet("/api/consenso"),
  padron: (limit = 50) => apiGet(`/api/bots?bot=padron&limit=${limit}`),
  loki_kp: (limit = 50) => apiGet(`/api/bots?bot=loki&limit=${limit}`),
  heatmaps: () => apiGet("/api/heatmaps"),
  consenso: (limit = 50) => apiGet(`/api/consenso?limit=${limit}`),
};
