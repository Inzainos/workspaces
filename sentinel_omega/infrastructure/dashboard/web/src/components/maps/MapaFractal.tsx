/**
 * Mapa 2D con nodos UVG-125 y sismos
 */
import { useCallback, useMemo } from "react"
import { NodoMapa, SismoMapa } from "@/components/maps/shared"

interface MapaFractalProps {
  nodos: NodoMapa[]
  sismos: SismoMapa[]
  altura?: number
  foco: string | null
  setFoco: (v: string | null) => void
}

export function MapaFractal({
  nodos,
  sismos,
  altura = 420,
  foco,
  setFoco,
}: MapaFractalProps) {
  const contenedorRef = useCallback((el: HTMLDivElement | null) => {
    // TODO: Implementar pan/zoom con D3 si es necesario
  }, [])

  return (
    <div className="relative w-full h-[altura] bg-surface rounded-lg border border-border overflow-hidden">
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 1000 600"
        preserveAspectRatio="none"
      >
        {/* Fondo oscuro */}
        <rect width="100%" height="100%" fill="var(--color-superficie)" />
        <rect width="100%" height="100%" fill="var(--color-fondo-superficie-sunido)" opacity={0.3} />

        {/* Líneas de referencia */}
        {Array.from({ length: 5 }, (_, i) => i).map((i) => {
          const x = (i / 4) * 1000
          return (
            <line key={`v-${i}`} x1={x} y1={0} x2={x} y2={600} stroke="var(--color-borde)" strokeWidth="0.5" opacity={0.3} />
          )
        })}
        {Array.from({ length: 4 }, (_, i) => i).map((i) => {
          const y = (i / 3) * 600
          return (
            <line key={`h-${i}`} x1={0} y1={y} x2={1000} y2={y} stroke="var(--color-borde)" strokeWidth="0.5" opacity={0.3} />
          )
        })}

        {/* Sismos: círculos con radio proporcional a magnitud */}
        {sismos.map((s) => {
          const x = 500 + (s.lon * 3.45)
          const y = 300 - (s.lat * 1.5)
          const r = Math.max(3, Math.min(12, (s.mag ?? 4) * 1.5))
          const color = s.mag ? (s.mag >= 7 ? "var(--color-critico)" : s.mag >= 6 ? "var(--color-aviso)" : "var(--color-calma)") : "var(--color-fuente-desvanecido)"
          
          return (
            <circle
              key={`sismo-${s.lat}-${s.lon}-${s.mag}`}
              cx={x}
              cy={y}
              r={r}
              fill={color}
              stroke="white"
              strokeWidth={1}
              opacity={0.7}
              title={`${s.label || "Sismo"} - M${s.mag?.toFixed(1)} - ${new Date(s.ts ?? 0).toLocaleDateString("es-MX")}`}
            />
          )
        })}

        {/* Nodos */}
        {nodos.map((nodo) => {
          const x = 500 + (nodo.lon * 3.45)
          const y = 300 - (nodo.lat * 1.5)
          const sat = nodo.sat ?? 0
          const color = nodo.medido ? (sat > 0.8 ? "var(--color-critico)" : sat > 0.5 ? "var(--color-aviso)" : sat > 0.2 ? "var(--color-atencion)" : "var(--color-calma)") : "var(--color-fuente-desvanecido)"
          const esFoco = foco === nodo.label

          return (
            <circle
              key={nodo.label}
              cx={x}
              cy={y}
              r={esFoco ? 8 : (nodo.medido ? 4 + (sat ?? 0) * 3 : 2)}
              fill={nodo.medido ? color : "transparent"}
              stroke={esFoco ? "var(--color-acento)" : color}
              strokeWidth={esFoco ? 3 : (nodo.medido ? 1 : 0.5)}
              opacity={nodo.medido ? 0.9 : 0.3}
              cursor="pointer"
              onClick={() => setFoco?.(nodo.label)}
              title={`${nodo.label}\nSaturación: ${(sat ?? 0).toFixed(2)}\n${nodo.tipo}\n${nodo.region || ""}`}
            />
          )
        })}
      </svg>

      {/* Leyenda */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1 text-[0.7rem] text-fuente-desvanecido bg-superficie/80 p-2 rounded-md border border-border/50">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-var(--color-calma)" />
          <span>Baja</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-var(--color-atencion)" />
          <span>Media</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-var(--color-critico)" />
          <span>Alta</span>
        </div>
        <div className="flex items-center gap-1 mt-1">
          <div className="w-2 h-2 rounded-full bg-var(--color-fuente-desvanecido)" />
          <span>Sismos M≥4.5</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Globo 3D - Versión simplificada (mapa 2D con estilo globo)
 */
export function Globo3D({
  nodos,
  sismos,
  altura = 420,
  foco,
  setFoco,
}: {
  nodos: NodoMapa[]
  sismos: SismoMapa[]
  altura?: number
  foco: string | null
  setFoco: (v: string | null) => void
}) {
  return (
    <div className="relative w-full h-[altura] bg-surface rounded-lg border border-border overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,var(--color-superficie-sunido),var(--color-superficie))] rounded-lg" />
      <MapaFractal nodos={nodos} sismos={sismos} altura={altura} foco={foco} setFoco={setFoco} />
    </div>
  )
}
