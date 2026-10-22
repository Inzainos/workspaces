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
