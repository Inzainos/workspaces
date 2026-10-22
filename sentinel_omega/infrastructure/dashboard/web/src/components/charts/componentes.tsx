/**
 * Componentes de gráficos para Sentinel Omega
 * Gráficos simples en SVG para visualización de datos de precursors
 */
import { cn } from "@/lib/utils"
import { fmtNum } from "@/lib/utils"
import { colorNivelDim, riskColor } from "@/lib/ui"

/**
 * Barra de veredictos del Juez
 * Muestra aciertos / falsos positivos / fallos en proporción real
 */
export function BarraVeredictos({
  aciertos,
  falsosPositivos,
  fallos,
  altura = 28,
}: {
  aciertos: number
  falsosPositivos: number
  fallos: number
  altura?: number
}) {
  const total = aciertos + falsosPositivos + fallos
  if (!total) {
    return (
      <div className="flex items-center gap-2 text-meta texto-desvanecido">
        <span className="mono texto-principal fuente-negrita">—</span>
        <span>Sin veredictos resueltos</span>
      </div>
    )
  }

  const p = (n: number) => Math.round((n / total) * 100)
  const totalPct = Math.round(100)

  return (
    <div className="flex flex-col gap-3">
      <div className="relative w-full h-[altura]">
        <div className="absolute inset-y-0 left-0 w-full h-full bg-surface-sunken" />
        <div className="absolute inset-y-0 left-0 h-full bg-emerald-500/60 rounded-lg" style={{ width: `${p(aciertos)}%` }} />
        <div className="absolute inset-y-0 left-[${p(aciertos)}%] h-full bg-orange-500/60 rounded-lg" style={{ width: `${p(falsosPositivos)}%` }} />
        <div className="absolute inset-y-0 left-[${p(aciertos + falsosPositivos)}%] h-full bg-rose-500/60 rounded-lg" style={{ width: `${p(fallos)}%` }} />
      </div>
      <div className="flex justify-between text-micro text-desvanecido text-mono">
        <span>Aciertos: {aciertos}</span>
        <span className="texto-esmeralda-400">{aciertos}</span>
        <span>Falsos positivos: {falsosPositivos}</span>
        <span className="texto-orange-400">{falsosPositivos}</span>
        <span>Fallos: {fallos}</span>
        <span className="texto-rose-400">{fallos}</span>
      </div>
    </div>
  )
}

/**
 * Línea de serie simple (sparkline)
 */
export function LíneaSerie({
  datos,
  objetivo,
  altura = 240,
  color = "var(--color-serie-1)",
  destacarÚltimo = false,
  título,
}: {
  datos: Array<{ x: number | string; y: number }> | number[]
  objetivo?: string
  altura?: number
  color?: string
  destacarÚltimo?: boolean
  título?: string
}) {
  const pts = typeof datos[0] === "number"
    ? datos.map((v, i) => ({ x: i, y: Number(v) }))
    : datos.map((d) => ({ x: Number(d.x), y: Number(d.y) }))

  if (pts.length === 0) return null

  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const rangeX = maxX === minX ? 1 : maxX - minX
  const rangeY = maxY === minY ? 1 : maxY - minY

  const path = puntos
    .map((p, i) => {
      const x = ((p.x - minX) / rangeX) * 100
      const y = 100 - ((p.y - minY) / rangeY) * 100
      return `${i === 0 ? "M" : "L"}${x}% ${y}%`
    })
    .join("")

  return (
    <div className="relative w-full h-[altura]">
      {título && (
        <div className="texto-meta texto-desvanecido texto-xs mb-2">{título}</div>
      )}
      <svg
        className="w-full h-[altura]"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ altura }}
      >
        <path
          d={path}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {destacarÚltimo && pts.length > 0 && (
          <circle
            cx={((pts[pts.length - 1].x - minX) / rangeX) * 100}
            cy={100 - ((pts[pts.length - 1].y - minY) / rangeY) * 100}
            r={2.5}
            fill={color}
          />
        )}
      </svg>
    </div>
  )
}

/**
 * Barras simples
 */
export function SimpleBars({
  datos,
  altura = 240,
  color = "var(--color-serie-1)",
}: {
  datos: Array<{ clave: string; valor: number; color?: string }>
  altura?: number
  color?: string
}) {
  if (!datos || datos.length === 0) return null

  const maxVal = Math.max(...datos.map((d) => Number(d.valor)))

  return (
    <div className="flex flex-col items-end gap-2 h-[altura]">
      {datos.map((d, i) => {
        const valor = Number(d.valor)
        const pct = maxVal > 0 ? (valor / maxVal) * 100 : 0
        const colorBarra = d.color || color
        return (
          <div key={i} className="flex flex-col items-end gap-1">
            <div className="flex-1 bg-surface-sunken rounded-t-sm" style={{ height: altura }}>
              <div className="h-full bg-gradient-to-t from-${colorRiesgoColor(d.valor, umbralesDefault)} to-${colorRiesgoColor(d.valor, umbralesDefault)}/60" style={{ height: `${Math.max(pct, 5)}%` }} />
            </div>
            <span className="mono texto-micro texto-desvanecido w-16 truncate">{d.clave}</span>
            <span className="mono texto-principal fuente-negrita">{valor.toFixed(2)}</span>
          </div>
        )
      })}
    </div>
  )
}

function colorRiesgoColor(valor: number, umbrales: [number, number, number]): string {
  if (valor >= umbrales[2]) return "var(--color-critico)"
  if (valor >= umbrales[1]) return "var(--color-aviso)"
  if (valor >= umbrales[0]) return "var(--color-atencion)"
  return "var(--color-calma)"
}

const umbralesDefault: [number, number, number] = [5, 15, 30]

/**
 * Indicador de estado con punto de color
 */
export function IndicadorEstado({
  estado,
  texto,
}: {
  estado: "activo" | "inactivo" | "advertencia" | "error" | "desconocido"
  texto?: string
  tamaño?: "sm" | "md"
}) {
  const colores: Record<string, string> = {
    activo: "var(--color-calma)",
    inactivo: "var(--color-fuente-desvanecido)",
    advertencia: "var(--color-aviso)",
    error: "var(--color-critico)",
    desconocido: "var(--color-fuente-desvanecido)",
  }
  const tamaños: Record<string, string> = {
    sm: "h-2.5 w-2.5",
    md: "h-3 w-3",
  }

  return (
    <div className="flex items-center gap-1.5">
      <div className={`${tamaños[tamaño]} reducir-redondo`} style={{ backgroundColor: colores[estado] || colores.desconocido }} />
      {texto && <span className="mono texto-micro texto-desvanecido">{texto}</span>}
    </div>
  )
}
