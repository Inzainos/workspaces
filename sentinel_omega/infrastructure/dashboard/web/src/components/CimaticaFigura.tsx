/**
 * CimaticaFigura - Visualización de cimática (patrones Chladni)
 */
import { useMemo } from "react"
import { fmtNum } from "@/lib/utils"

interface CimaticaFiguraProps {
  clave: string
  frecuencia?: number
  altura?: number
  ancho?: number
  color?: string
}

export function CimaticaFigura({
  clave,
  frecuencia,
  altura = 200,
  ancho = 200,
  color = "var(--color-calma)",
}: CimaticaFiguraProps) {
  // Generar patrón de cimática determinístico basado en la clave
  const generarPatrones = (clave: string) => {
    let hash = 0
    for (let i = 0; i < clave.length; i++) {
      hash = clave.charCodeAt(i) + ((hash << 5) - hash)
      hash = hash & hash
    }
    return Math.abs(hash)
  }

  const hash = generarPatrones(clave || "vacío")
  const numPuntos = 12 + (hash % 20) // Entre 12 y 32 puntos
  const radioExterno = 80
  const radioInterno = 30
  const centroX = 100
  const centroY = 100

  // Generar puntos del patrón de cimática
  const puntos = []
  for (let i = 0; i < numPuntos; i++) {
    const angulo = (i / numPuntos) * 2 * Math.PI
    const raio = radioInterno + (radioExterno - radioInterno) * (0.3 + 0.7 * Math.sin(hash * i + i))
    const x = centroX + raio * Math.cos(angulo)
    const y = centroY + raio * Math.sin(angulo)
    puntos.push({ x, y, r: 2 + (hash % 3) })
  }

  return (
    <div className="flex items-center justify-center w-full h-full" style={{ altura, ancho }}>
      <svg width={ancho} height={altura} viewBox="0 0 200 200" style={{ width: "100%", height: "100%" }}>
        {/* Círculos de referencia */}
        <circle cx={centroX} cy={centroY} r={radioExterno} fill="none" stroke="var(--color-borde)" strokeWidth="1" opacity={0.3} />
        <circle cx={centroX} cy={centroY} r={radioInterno} fill="none" stroke="var(--color-borde)" strokeWidth="1" opacity={0.15} />

        {/* Líneas radiales */}
        {puntos.map((p, i) => {
          const angulo = (i / numPuntos) * 2 * Math.PI
          const x2 = centroX + radioExterno * Math.cos(angulo)
          const y2 = centroY + radioExterno * Math.sin(angulo)
          return (
            <line key={`l-${i}`} x1={centroX} y1={centroY} x2={x2} y2={y2} stroke="var(--color-borde)" strokeWidth="0.5" opacity={0.2} />
          )
        })}

        {/* Puntos del patrón */}
        {puntos.map((p, i) => (
          <circle key={`p-${i}`} cx={p.x} cy={p.y} r={p.r} fill={color} opacity={0.8} />
        ))}
      </svg>
    </div>
  )
}

export default CimaticaFigura
