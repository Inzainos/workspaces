/**
 * Componentes base de UI para Sentinel Omega Dashboard
 * Diseño minimalista, oscuro, centrado en datos
 */
import { cn } from "@/lib/utils"
import { riskColor, riskColorDim, riskTextColor, fmtNum, esAusente } from "@/lib/ui"
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
  const variants = {
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
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}

export function StatusBadge({
  nivel,
  valor,
}: {
  nivel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | "DESCONOCIDO" | null | undefined
  valor?: string
}) {
  const variants: Record<string, string> = {
    LOW: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    MODERATE: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    HIGH: "bg-orange-500/20 text-orange-400 border border-orange-500/30",
    CRITICAL: "bg-rose-500/20 text-rose-400 border border-rose-500/30",
    DESCONOCIDO: "bg-surface-sunken text-faint border border-border/50",
  }
  const label = valor || nivel || "DESCONOCIDO"
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.65rem] font-semibold tracking-tighter",
        variants[nivel] || variants.DESCONOCIDO
      )}
    >
      {label}
    </span>
  )
}

export function Card({
  className,
  children,
  padding = "p-5",
  ...props
}: React.ComponentProps<"div"> & {
  padding?: "none" | "p-3" | "p-5" | "p-6"
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface relative overflow-hidden",
        padding,
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  className,
  children,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex items-center gap-2 px-4 py-3 border-b border-border", className)}>
      {children}
    </div>
  )
}

export function CardContent({
  className,
  children,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("px-4 py-4", className)}>
      {children}
    </div>
  )
}

export function CardFooter({
  className,
  children,
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex items-center px-4 py-3 border-t border-border", className)}>
      {children}
    </div>
  )
}

export function KpiCard({
  titulo,
  valor,
  unidad,
  contexto,
  nivel,
  tendencia,
  className,
}: {
  titulo: string
  valor: string | number
  unidad?: string
  contexto?: string
  nivel?: "LOW" | "MODERATE" | "HIGH" | "CRITICAL" | null
  tendencia?: "sube" | "baja" | "estable"
  className?: string
}) {
  const color = nivel ? riskColor(nivel) : undefined
  const colorDim = nivel ? riskColorDim(nivel) : undefined
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-4",
        colorDim && `bg-[color-mix(in_oklab,${colorDim}50%,transparent)]`,
        className
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-meta text-muted uppercase tracking-tighter text-[0.625rem]">{etiqueta}</div>
        {tendencia && (
          <span
            className="flex items-center gap-1 text-[0.7rem] font-semibold"
            class={tendencia === "sube" ? "text-emerald-400" : tendencia === "baja" ? "text-rose-400" : "text-faint"}
          >
            {tendencia === "sube" ? "↑" : tendencia === "baja" ? "↓" : "—"}
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={cn("text-2xl font-bold text-foreground", color && `text-${color.replace('#','')}`)}>
          {valor}
        </span>
        {unidad && <span className="ml-0.5 text-[0.7rem] font-medium text-faint">{unidad}</span>}
      </div>
      {contexto && (
        <div className="mt-1 text-[0.68rem] text-muted leading-snug">{contexto}</div>
      )}
    </div>
  )
}

export function EmptyState({
  titulo,
  detalle,
  icono = <Info className="w-6 h-6" />,
}: {
  titulo: string
  detalle?: string
  icono?: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface-sunken/50 p-8 text-center">
      <div className="flex items-center justify-center gap-2 mb-3 text-faint">{icono}</div>
      <div className="text-body font-medium text-body">{titulo}</div>
      {detalle && <div className="mt-1 text-meta text-muted">{detalle}</div>}
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
      className="rounded-lg border border-dashed border-rose-500/50 bg-rose-500/10 px-4 py-3 text-rose-400"
    >
      {mensaje}
    </div>
  )
}

export function LoadingSpinner({
  className = "w-5 h-5",
}: {
  className?: string
}) {
  return (
    <svg className={cn("animate-spin", className)} viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938" />
    </svg>
  )
}

export function TabHeader({
  titulo,
  subtitulo,
}: {
  titulo: string
  subtitulo?: string
}) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-bold text-foreground tracking-tight">{titulo}</h2>
      {subtitulo && <p className="text-meta text-muted mt-1">{subtitulo}</p>}
    </div>
  )
}

export function SectionHeader({
  titulo,
  accion,
}: {
  titulo: string
  accion?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-emerald-400" />
        <span className="text-base font-semibold text-foreground">{titulo}</span>
      </div>
      {accion}
    </div>
  )
}
