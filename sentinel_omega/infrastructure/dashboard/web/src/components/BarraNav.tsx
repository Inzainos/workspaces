/**
 * Barra de navegación superior para Sentinel Omega
 */
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

export function BarraNav() {
  const items = [
    { to: "/principal", label: "Principal" },
    { to: "/sintesis", label: "Síntesis" },
    { to: "/predicciones", label: "Predicciones" },
    { to: "/mapas", label: "Mapas" },
    { to: "/senales", label: "Señales" },
    { to: "/cimatica", label: "Cimática" },
    { to: "/modelos", label: "Modelos" },
    { to: "/padrejuez", label: "Padre+Juez" },
    { to: "/reportes", label: "Reportes" },
  ]

  return (
    <nav className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-sunken">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center">
          <svg width="20" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m12.78 1.41l-1.41 1.41M12 20l-1.41-1.41L12 12l1.41 1.41" />
          </svg>
        </div>
        <div className="flex flex-col">
          <span className="texto-principal fuente-negrita texto-sm">Sentinel Omega</span>
          <span className="mono texto-micro texto-desvanecido">v2.0.0 - Plataforma de detección</span>
        </div>
      </div>
      <nav className="flex gap-1 flex-wrap">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </nav>
  )
}
