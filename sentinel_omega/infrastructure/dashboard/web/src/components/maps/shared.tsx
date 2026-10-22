/**
 * Tipos compartidos para mapas
 */
export interface NodoMapa {
  lat: number | null
  lon: number | null
  tipo: string
  label: string
  sat?: number
  medido?: boolean
  updated?: string | null
}

export interface SismoMapa {
  lat: number | null
  lon: number | null
  mag: number | null
  label: string
  profundidadKm?: number | null
  ts?: number | null
}
