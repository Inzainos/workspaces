import { NavLink } from "react-router-dom"
import { Outlet } from "react-router-dom"

export default function Layout() {
  return (
    <div className="flex h-screen bg-superficie">
      {/* Sidebar */}
      <aside className="w-64 bg-superficie-sunken border-r border-border">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m12.78 1.41l-1.41 1.41M12 20l-1.41-1.41L12 12l1.41 1.41" />
              </svg>
            </div>
            <span className="texto-principal fuente-negrita">Sentinel Omega</span>
          </div>
          <nav className="mt-4">
            <navLink
              to="/"
              className={({ isActive }) =>
                cn(
                  "block px-3 py-2 texto-micro texto-muteado hover:bg-surface-sunken hover:texto-principal",
                  isActive && "texto-esmeralda-400 bg-surface/50",
                )
              }
            >
              Dashboard
            </navLink>
            <navLink
              to="/alertas"
              className={({ isActive }) =>
                cn(
                  "block px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                  isActive && "texto-esmeralda-400 bg-surface/50",
                )
              }
            >
              Alertas
            </navLink>
            <navLink
              to="/etiquetas"
              className={({ isActive }) =>
                cn(
                  "block px-3 py-2 texto-micro texto-desvanecido hover:bg-surface-sunken hover:texto-principal",
                  isActive && "texto-esmeralda-400 bg-surface/50",
                )
              }
            >
              Etiquetas
            </navLink>
          </nav>
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
