/**
 * Barra lateral de navegación para Sentinel Omega
 */
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

export function BarraLateral() {
  const items = [
    { to: "/principal", label: "Dashboard Principal" },
    { to: "/sintesis", label: "Síntesis" },
    { to: "/predicciones", label: "Predicciones" },
    { to: "/mapas", label: "Mapas" },
    { to: "/senales", label: "Señales" },
    { to: "/cimatica", label: "Cimática" },
    { to: "/modelos", label: "Modelos" },
    { to: "/loki", label: "Loki" },
    { to: "/padrejuez", label: "Padre + Juez" },
    { to: "/reportes", label: "Reportes" },
    { to: "/padron", label: "Padrón" },
    { to: "/concilio", label: "Concilio" },
    { to: "/watchdog", label: "Watchdog" },
  ]

  return (
    <aside className="w-64 bg-surface-sunken border-r border-border overflow-y-auto">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center">
            <svg width="20" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m12.78 1.41l-1.41 1.41M12 20l-1.41-1.41L12 12l1.41 1.41" />
            </svg>
          </div>
          <span className="texto-principal fuente-negrita">Sentinel Omega</span>
        </div>
        <nav className="space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                  isActive && "texto-esmeralda-400 bg-surface/50",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  )
}
