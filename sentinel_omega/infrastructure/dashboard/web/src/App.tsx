import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { HealthStrip } from "@/components/HealthStrip";
import { PresentacionTab } from "@/components/tabs/PresentacionTab";
import { PrincipalTab } from "@/components/tabs/PrincipalTab";
import { PrediccionesTab } from "@/components/tabs/PrediccionesTab";
import { MapasTab } from "@/components/tabs/MapasTab";
import { SenalesTab } from "@/components/tabs/SenalesTab";
import { ModelosTab } from "@/components/tabs/ModelosTab";
import { ReportesTab } from "@/components/tabs/ReportesTab";

/**
 * Sentinel Omega — 7 pestañas.
 *
 * Cada pestaña se diseñó contra UNA superficie, y eso manda sobre la
 * composición (no al revés):
 *
 *   Presentación → Decide/Learn — la única donde un hero es correcto.
 *   Principal    → Monitor      — densidad y lectura de reojo, sin hero.
 *   Predicciones → Monitor
 *   Mapas        → Explore
 *   Señales      → Monitor
 *   Modelos      → Compare      — bots enfrentados, columnas alineadas.
 *   Reportes     → Explore
 *
 * El arranque es `principal`: quien abre esto quiere ver el estado, no que le
 * expliquen el producto.
 */
export default function App() {
  return (
    <div className="min-h-screen">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-surface-raised focus:px-3 focus:py-2"
      >
        Saltar al contenido
      </a>

      <header className="sticky top-0 z-20 border-b border-border bg-[color:var(--color-base-900)]/92 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-5 py-2.5">
          <div className="flex items-center gap-2.5">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z"
                stroke="var(--color-accent)"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <path d="M12 8v5M12 16v.6" stroke="var(--color-accent)" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
            <div className="leading-tight">
              <div className="text-body font-semibold text-foreground">Sentinel Omega</div>
              <div className="text-micro text-faint">
                Precursores de eventos naturales · lectura, no predicción
              </div>
            </div>
          </div>
          <HealthStrip />
        </div>
      </header>

      <main id="contenido" className="mx-auto max-w-[1600px] px-5 pb-16 pt-5">
        <Tabs defaultValue="principal">
          <TabsList>
            <TabsTrigger value="presentacion">Presentación</TabsTrigger>
            <TabsTrigger value="principal">Principal</TabsTrigger>
            <TabsTrigger value="predicciones">Predicciones</TabsTrigger>
            <TabsTrigger value="mapas">Mapas</TabsTrigger>
            <TabsTrigger value="senales">Señales</TabsTrigger>
            <TabsTrigger value="modelos">Modelos</TabsTrigger>
            <TabsTrigger value="reportes">Reportes</TabsTrigger>
          </TabsList>
          <TabsContent value="presentacion"><PresentacionTab /></TabsContent>
          <TabsContent value="principal"><PrincipalTab /></TabsContent>
          <TabsContent value="predicciones"><PrediccionesTab /></TabsContent>
          <TabsContent value="mapas"><MapasTab /></TabsContent>
          <TabsContent value="senales"><SenalesTab /></TabsContent>
          <TabsContent value="modelos"><ModelosTab /></TabsContent>
          <TabsContent value="reportes"><ReportesTab /></TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
