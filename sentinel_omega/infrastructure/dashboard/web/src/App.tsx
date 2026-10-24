/**
 * Sentinel Omega — SPA con Router.
 *
 * Ruta raíz = Principal (datos vivos, no un folleto estático). Quien abre
 * esto quiere ver el estado del planeta, no que le expliquen el producto.
 *
 * Sólo Sentinel Omega: Padrón, Concilio y Watchdog viven en SUS propios
 * proyectos y NO se duplican aquí (regla: cero datos sintéticos — sin
 * endpoint de esa fuente aquí, no se inventa su contenido).
 */
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { BarraLateral } from "@/components/BarraLateral"
import { PresentacionTab } from "@/components/tabs/PresentacionTab"
import { PrincipalTab } from "@/components/tabs/PrincipalTab"
import { SintesisTab } from "@/components/tabs/SintesisTab"
import { PrediccionesTab } from "@/components/tabs/PrediccionesTab"
import { MapasTab } from "@/components/tabs/MapasTab"
import { SeñalesTab } from "@/components/tabs/SeñalesTab"
import { CimaticaTab } from "@/components/tabs/CimaticaTab"
import { ModelosTab } from "@/components/tabs/ModelosTab"
import { LokiTab } from "@/components/tabs/LokiTab"
import { PadreJuezTab } from "@/components/tabs/PadreJuezTab"
import { ReportesTab } from "@/components/tabs/ReportesTab"

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-surface">
        <BarraLateral />
        <main className="flex-1 overflow-y-auto p-6 bg-surface">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<PrincipalTab />} />
              <Route path="presentacion" element={<PresentacionTab />} />
              <Route path="principal" element={<PrincipalTab />} />
              <Route path="sintesis" element={<SintesisTab />} />
              <Route path="predicciones" element={<PrediccionesTab />} />
              <Route path="mapas" element={<MapasTab />} />
              <Route path="senales" element={<SeñalesTab />} />
              <Route path="cimatica" element={<CimaticaTab />} />
              <Route path="modelos" element={<ModelosTab />} />
              <Route path="loki" element={<LokiTab />} />
              <Route path="padrejuez" element={<PadreJuezTab />} />
              <Route path="reportes" element={<ReportesTab />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </BrowserRouter>
  )
}
