/**
 * Sentinel Omega - Dashboard Principal
 * Aplicación principal de detección de anomalías naturales
 */
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { BarraNav } from "@/components/BarraNav"
import { BarraLateral } from "@/components/BarraLateral"
import { PresentacionTab } from "@/components/tabs/PresentacionTab"
import { SintesisTab } from "@/components/tabs/SintesisTab"
import { PrincipalTab } from "@/components/tabs/PrincipalTab"
import { LokiTab } from "@/components/tabs/LokiTab"
import { PadreJuezTab } from "@/components/tabs/PadreJuezTab"
import { PrediccionesTab } from "@/components/tabs/PrediccionesTab"
import { MapasTab } from "@/components/tabs/MapasTab"
import { SeñalesTab } from "@/components/tabs/SeñalesTab"
import { ModelosTab } from "@/components/tabs/ModelosTab"
import { ReportesTab } from "@/components/tabs/ReportesTab"
import { CimaticaTab } from "@/components/tabs/CimaticaTab"
import { PadrónTab } from "@/components/tabs/PadrónTab"
import { ConcilioTab } from "@/components/tabs/ConcilioTab"
import { WatchdogTab } from "@/components/tabs/WatchdogTab"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-surface">
        {/* Barra lateral */}
        <BarraLateral />

        {/* Área principal */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Barra de navegación superior */}
          <BarraNav />

          {/* Contenido principal */}
          <main className="flex-1 overflow-y-auto p-6 bg-surface">
            <ErrorBoundary>
            <Routes>
              <Route path="/" element={<PresentacionTab />} />
              <Route path="presentacion" element={<PresentacionTab />} />
              <Route path="sintesis" element={<SintesisTab />} />
              <Route path="principal" element={<PrincipalTab />} />
              <Route path="loki" element={<LokiTab />} />
              <Route path="padrejuez" element={<PadreJuezTab />} />
              <Route path="predicciones" element={<PrediccionesTab />} />
              <Route path="mapas" element={<MapasTab />} />
              <Route path="senales" element={<SeñalesTab />} />
              <Route path="modelos" element={<ModelosTab />} />
              <Route path="reportes" element={<ReportesTab />} />
              <Route path="cimatica" element={<CimaticaTab />} />
              <Route path="padron" element={<PadrónTab />} />
              <Route path="concilio" element={<ConcilioTab />} />
              <Route path="watchdog" element={<WatchdogTab />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
