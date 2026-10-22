/**
 * SeñalesVivas - Visualización de señales activas en tiempo real
 */
import { useMemo } from "react"
import { fmtTs } from "@/lib/utils"
import { nivelDe, colorNivel } from "@/components/ui/data"

interface SeñalViva {
  id: string
  tipo: string
  valor: number
  nodo: string
  lag: number
  confianza: number
  riesgo: string
  timestamp: number
}

export function SeñalesVivas({
  señales,
  texto,
  nivelRiesgo,
}: {
  señales: SeñalViva[]
  texto?: string
  nivelRiesgo?: string
}) {
  if (!señales || señales.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 p-4 text-fuente-desvanecido text-meta text-center">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-4 h-4 rounded-full bg-superficie-sunken" />
          <span>Sin señales activas</span>
        </div>
      </div>
    </div>
  )

  const ordenadas = [...señales].sort((a, b) => Number(b.valor) - Number(a.valor))
  const niveles = {
    CRITICAL: "var(--color-critico)",
    HIGH: "var(--color-aviso)",
    MEDIUM: "var(--color-atencion)",
    LOW: "var(--color-calma)",
  }

  return (
    <div className="space-y-2">
      {señales.slice(0, 10).map((s) => {
        const nivel = s.nivel || "BAJO"
        const color = {
          CRITICAL: "var(--color-critico)",
          HIGH: "var(--color-aviso)",
          MEDIUM: "var(--color-atencion)",
          LOW: "var(--color-calma)",
        }[nivel] || "var(--color-fuente-desvanecido)"
        
        return (
          <div key={s.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg border border-border/50 bg-superficie-sunken">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="mono texto-principal fuente-negrita texto-[0.7rem]">{s.tipo}</span>
            <span className="mono texto-meta texto-desvanecido">•</span>
            <span className="mono texto-principal fuente-negrita">{s.valor.toFixed(2)}</span>
            <span className="mono texto-meta texto-desvanecido">@ ${nodo.nodo || "nodo"}</span>
            <span className={`mono texto-micro px-1 py-0.5 rounded bg-${nivel === "CRITICAL" ? "rose-500/20" : nivel === "HIGH" ? "orange-500/20" : "var(--color-surface-sunken)"} text-${nivel === "CRITICAL" ? "texto-rose-400" : nivel === "HIGH" ? "texto-orange-400" : "texto-desvanecido"}`}>
              {nivel}
            </span>
            <span className="ml-auto mono texto-desvanecido texto-[0.65rem]">
              {fmtTs(s.timestamp || s.ts || Date.now())}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
