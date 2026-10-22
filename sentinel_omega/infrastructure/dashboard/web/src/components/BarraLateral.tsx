/**
 * Barra lateral de navegación para Sentinel Omega
 */
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

export function BarraLateral() {
  return (
    <aside className="w-64 bg-surface-sunken border-r border-border">
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
          <NavLink
            to="/principal"
            className={({ isActive }) =>
              cn(
                "flex items-center px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Dashboard Principal
          </NavLink>
          <NavLink
            to="/sintesis"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Síntesis
          </NavLink>
          <NavLink
            to="/predicciones"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Predicciones
          </NavLink>
          <NavLink
            to="/mapas"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Mapas
          </NavLink>
          <NavLink
            to="/señales"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Señales
          </NavLink>
          <NavLink
            to="/modelos"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Modelos
          </NavLink>
          <NavLink
            to="/reportes"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Reportes
          </NavLink>
          <NavLink
            to="/cimatica"
            className={({ isActive }) =>
              cn(
                "px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                isActive && "texto-esmeralda-400 bg-surface/50",
              )
            }
          >
            Cimática
          </NavLink>
        </nav>
      </div>
    </aside>
  )
}
