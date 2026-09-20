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
 * Sentinel Omega — rediseño a 7 pestañas:
 * Presentación · Principal · Predicciones · Mapas · Señales · Modelos · Reportes.
 * Tabs antiguos (Familias/Omega/Loki/PadreJuez) quedan como módulos reutilizables.
 */
export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-white/5 bg-[#08090a]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className="grid h-7 w-7 place-items-center rounded-md"
              style={{ background: "linear-gradient(140deg,#5e6ad2,#3a439c)" }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f7f8f8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 4 6v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6z" /></svg>
            </div>
            <div>
              <div className="text-sm font-semibold">Sentinel Omega</div>
              <div className="mono text-[11px] text-muted">Tablero de lectura · datos reales SQLite · no predice</div>
            </div>
          </div>
          <HealthStrip />
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
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
