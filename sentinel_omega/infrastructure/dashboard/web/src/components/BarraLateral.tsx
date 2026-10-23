/**
 * BarraLateral — única navegación (BarraNav era un duplicado).
 * Sólo Sentinel Omega: Padrón/Concilio/Watchdog quitados (viven en sus
 * propios proyectos).
 */
import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"

const ITEMS = [
  { to: "/principal", label: "Principal" },
  { to: "/sintesis", label: "Síntesis" },
  { to: "/predicciones", label: "Predicciones" },
  { to: "/mapas", label: "Mapas" },
  { to: "/senales", label: "Señales" },
  { to: "/cimatica", label: "Cimática" },
  { to: "/modelos", label: "Modelos" },
  { to: "/loki", label: "Loki" },
  { to: "/padrejuez", label: "Padre + Juez" },
  { to: "/reportes", label: "Reportes" },
]

export function BarraLateral() {
  return (
    <aside className="w-56 shrink-0 border-r border-border/60 bg-[#0f1011] flex flex-col">
      <div className="px-4 py-5 border-b border-border/60">
        <div className="flex items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z" stroke="var(--color-acento)" strokeWidth="1.6" strokeLinejoin="round" />
            <path d="M12 8v5M12 16v.6" stroke="var(--color-acento)" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          <div>
            <div className="font-bold text-sm text-foreground">Sentinel Omega</div>
            <div className="text-[0.65rem] text-faint">precursores · lectura</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "block px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-surface-raised text-foreground border border-border"
                  : "text-muted hover:text-foreground hover:bg-surface-raised/50"
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
