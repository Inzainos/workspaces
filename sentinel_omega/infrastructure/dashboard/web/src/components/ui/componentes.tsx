/**
 * Componentes de UI base para Sentinel Omega
 * Diseño minimalista, oscuro, centrado en datos
 */
import { cn } from "@/lib/utils"
import { riskColor, riskColorDim, riskTextColor } from "@/lib/ui"
import { ChevronDown, ChevronUp, AlertTriangle, AlertCircle, CheckCircle, Info, Clock, Zap, Shield, BarChart3, Activity } from "lucide-react"

export function Button({
  className,
  variant = "default",
  size = "md",
  disabled,
  children,
  ...props
}: React.ComponentProps<"button"> & {
  variant?: "default" | "destructive" | "outline" | "ghost" | "primary"
  size?: "sm" | "md" | "lg"
}) {
  const base = "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
  const variants = {
    default: "bg-surface border border-border text-foreground hover:bg-surface-highlight",
    destructive: "bg-red-500 text-white hover:bg-red-600",
    outline: "border border-border bg-transparent hover:bg-surface-highlight",
    ghost: "bg-transparent hover:bg-surface-highlight",
    primary: "bg-indigo-500 text-white hover:bg-indigo-600",
  }
  const sizes = {
    sm: "h-8 px-2 text-xs",
    md: "h-9 px-3 py-2",
    lg: "h-10 px-4 text-sm",
  }
  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}

export function Badge({
  className,
  variant,
  children,
}: {
  variant?: "success" | "warning" | "danger" | "info" | "neutral" | "risk-low" | "risk-moderate" | "risk-high" | "risk-critical"
  children: React.ReactNode
  className?: string
}) {
  const variantes: Record<string, string> = {
    success: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    warning: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    danger: "bg-rose-500/20 text-rose-400 border border-rose-500/30",
    info: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
    neutral: "bg-surface-sunken text-faint border border-border/50",
    "risk-low": "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    "risk-moderate": "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    "risk-high": "bg-orange-500/20 text-orange-400 border border-orange-500/30",
    "risk-critical": "bg-rose-500/20 text-rose-400 border border-rose-500/30",
  }
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.7rem] font-semibold uppercase tracking-tighter",
        variantes[variant],
        className
      )}
    >
      {children}
    </span>
  )
}

export function EstadoBadge({
  nivel,
  texto,
}: {
  nivel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "DESCONOCIDO" | null | undefined
  texto?: string
}) {
  const variantes: Record<string, string> = {
    LOW: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    MODERATE: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    HIGH: "bg-orange-500/20 text-orange-400 border border-orange-500/30",
    CRITICAL: "bg-rose-500/20 text-rose-400 border border-rose-500/30",
    DESCONOCIDO: "bg-surface-sunken text-faint border border-border/50",
  }
  const etiqueta = texto || nivel || "DESCONOCIDO"
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-tighter",
        variantes[nivel] || variantes.DESCONOCIDO
      )}
    >
      {etiqueta}
    </span>
  )
}

export function Tarjeta({
  clase,
  hijos,
  relleno = "p-5",
  ...otros
}: React.ComponentProps<"div"> & {
  relleno?: "ninguno" | "p-3" | "p-5" | "p-6"
}) {
  return (
    <div
      className={cn(
        "redondeado-xl borde borde-borde bg-superficie",
        clase,
        relleno
      )}
      {...otros}
    >
      {hijos}
    </div>
  )
}

export function EncabezadoTarjeta({
  clase,
  hijos,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex items-centro espacio-x-2 px-4 py-3 borde-b borde-borde", clase)}>
      {hijos}
    </div>
  )
}

export function ContenidoTarjeta({
  clase,
  hijos,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("px-4 py-4", clase)}>
      {hijos}
    </div>
  )
}

export function PieTarjeta({
  clase,
  hijos,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex items-centro px-4 py-3 borde-t borde-borde", clase)}>
      {hijos}
    </div>
  )
}

export function TarjetaKPI({
  detalle,
  objetivo,
  riesgo,
  accion,
  sha256,
  cuarentena_path,
  original_path,
  forense_path,
  llm_nota,
  incidente_id,
}: {
  detalle: string
  objetivo: string | number
  riesgo?: string
  accion?: string
  sha256?: string
  cuarentena_path?: string
  original_path?: string
  forense_path?: string
  llm_nota?: string
  incidente_id?: number
  clase?: string
}) {
  const color = nivel ? riskColor(nivel) : undefined
  const colorOscuro = nivel ? riskColorDim(nivel) : undefined
  return (
    <div
      className={cn(
        "redondeado-xl borde borde-borde bg-superficie p-4",
        colorOscuro && `bg-[color-mix(in_oklab,${colorOscuro}50%,transparente)]`,
        clase
      )}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline gap-2">
          <span className="mono texto-principal fuente-negrita">{valor}</span>
          {unidad ? <span className="ml-0.5 texto-[0.7rem] fuente-medio texto-desvanecido">{unidad}</span> : null}
        </div>
        {contexto && (
          <div className="mt-1 texto-meta texto-desvanecido texto-con-ajuste">{contexto}</div>
        )}
      </div>
    </div>
  )
}

export function EstadoVacío({
  título,
  detalle,
  ícono = <Info className="w-6 h-6" />,
}: {
  título: string
  detalle?: string
  ícono?: React.ReactNode
}) {
  return (
    <div className="redondeado-lg borde borde-desgastado bg-superficie-penumbra p-8 texto-centro">
      <div className="flex items-centro espacio-x-2 mb-3 texto-fuente-desvanecido">{ícono}</div>
      <div className="texto-principal fuente-negrita">{título}</div>
      {detalle && <div className="mt-1 texto-meta texto-desvanecido">{detalle}</div>}
    </div>
  )
}

export function BannerError({
  mensaje,
}: {
  mensaje: string
}) {
  return (
    <div
      className="redondeado-lg borde borde-desgastado borde-rose-500/50 bg-rose-500/10 px-4 py-3 texto-rose-400"
    >
      {mensaje}
    </div>
  )
}

export function GiradorCargando({
  clase = "w-5 h-5",
}: {
  clase?: string
}) {
  return (
    <svg className={cn("girar", clase)} viewBox="0 0 24 24">
      <circulo clase="opacidad-25" cx="12" cy="12" r="10" trazo="colores-actual" trazoAncho="4"></circulo>
      <ruta clase="opacidad-75" relleno="colores-actual" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938" />
    </svg>
  )
}

export function CabeceraSección({
  título,
  subtítulo,
}: {
  título: string
  subtítulo?: string
}) {
  return (
    <div className="mb-6">
      <h2 className="texto-2xl fuente-negrita texto-primer-plano">{título}</h2>
      {subtítulo && <p className="texto-meta texto-desvanecido mt-1">{subtítulo}</p>}
    </div>
  )
}

export function EncabezadoSección({
  título,
  acción,
}: {
  título: string
  acción?: React.ReactNode
}) {
  return (
    <div className="flex items-centro espacio-x-2 px-4 py-3 borde-b borde-borde">
      <div className="flex items-centro gap-2">
        <div className="h-2 w-2 redondo-lleno bg-esmeralda-400" />
        <span className="texto-principal fuente-negrita">{título}</span>
      </div>
      {acción}
    </div>
  )
}

export function AcciónRápida({
  clase,
  hijos,
}: React.ComponentProps<"div"> & {
  clase?: string
}) {
  return (
    <div className={cn(
      "inline-flex items-center justify-center redondeado-md fuente-negrita transición-colores enfoque-visible:desenfoque-nulo enfoque-visible:anillo-2 enfoque-visible:anillo-desplazamiento-2 desactivado:puntero-eventos-none desactivado:opacidad-50",
      clase
    )}
    >
      {hijos}
    </button>
  )
}

export function CifraGrande({
  valor,
  subtítulo,
  nivel,
  clase,
}: {
  valor: string | number
  subtítulo?: string
  nivel?: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null
  clase?: string
}) {
  const color = nivel ? riskColor(nivel) : undefined
  return (
    <div className={cn("flex-col", clase)}>
      <div className={cn("texto-3xl fuente-negrita texto-primer-plano", color && `texto-${color.replace('#','')}`)}>
        {valor}
      </div>
      {subtítulo && <div className="texto-[0.68rem] texto-desvanecido">{subtítulo}</div>}
    </div>
  )
}
