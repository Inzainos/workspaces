/**
 * Padrón de Afiliados - Pantalla de monitoreo electoral
 */
import { useCallback } from "react"
import { api } from "@/lib/api"
import { usePoll } from "@/hooks/usePoll"
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data"

export function PadrónTab() {
  const estadoF = useCallback(() => api.estado(), [])
  const padrón = usePoll(estadoF, 60000)

  const d = padrón.data as any
  
  if (padrón.error) return <BannerError mensaje={padrón.error} />
  if (padrón.loading && !padrón.data) return <SinDatos título="Cargando datos del padrón..." />

  const total = d?.total_afiliados ?? 0
  const activos = d?.afiliados_activos ?? 0
  const inactivos = d?.afiliados_inactivos ?? 0
  const por_edad = d?.distribucion_edad || []
  const por_ciudad = d?.distribucion_ciudad || []

  return (
    <div className="space-y-5">
      {/* KPIs principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Metrica
          detalle="Total afiliados"
          objetivo={total.toLocaleString("es-MX")}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Activos"
          objetivo={activos.toLocaleString("es-MX")}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Inactivos"
          objetivo={inactivos.toLocaleString("es-MX")}
          riesgo="BAJO"
          acción="revisar"
        />
        <Metrica
          detalle="Tasa de participación"
          objetivo={d?.tasa_participacion ? `${d.tasa_participacion.toFixed(1)}%` : "—"}
          riesgo="BAJO"
          acción="ver tendencia"
        />
      </div>

      {/* Gráficos de distribución */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Panel
          detalle="Distribución por edad"
          objetivo={`${por_edad.length} grupos etarios`}
          riesgo="BAJO"
          acción="ver detalle"
        >
          <div className="h-96">
            {/* Gráfico de barras simples para distribución por edad */}
            <div className="flex items-end gap-2 h-[300px]">
              {por_edad.map((grupo: any, i: number) => {
                const porcentaje = grupo.cantidad / total * 100
                return (
                  <div key={i} className="flex flex-col items-center">
                    <div className="flex-1 bg-blue-500/60 rounded-t-lg" style={{ height: `${porcentaje}%` }}></div>
                    <span className="mono texto-micro texto-desvanecido text-center w-12">{grupo.rango_edad}</span>
                    <span className="mono texto-principal fuente-negrita">{grupo.cantidad.toLocaleString("es-MX")}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </Panel>
        <Panel
          detalle="Distribución por ciudad"
          objetivo={`${por_ciudad.length} ciudades`}
          riesgo="BAJO"
          acción="ver detalle"
        >
          <div className="flex flex-col items-start gap-2">
            {por_ciudad.slice(0, 8).map((ciudad: any, i: number) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg border border-border bg-superficie/50">
                <span className="mono texto-micro texto-desvanecido w-20">{ciudad.ciudad}</span>
                <div className="flex-1 h-2 bg-surface-sunken rounded-full">
                  <div className="h-full bg-indigo-500/60 rounded-lg" style={{ width: `${ciudad.porcentaje || 0}%` }}></div>
                </div>
                <span className="mono texto-primal fuente-negrita">{ciudad.cantidad.toLocaleString("es-MX")}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel
          detalle="Distribución por género"
          objetivo="Hombres y mujeres"
          riesgo="BAJO"
          acción="ver detalle"
        >
          <div className="flex items-center gap-4">
            <div className="flex-1 text-center">
              <div className="flex items-center gap-2">
                <span className="mono texto-principal fuente-negrita">Hombres</span>
                <span className="mono texto-meta texto-desvanecido">{d?.distribucion_genero?.hombres?.toLocaleString("es-MX") ?? "0"}</span>
              </div>
              <div className="w-full h-2 bg-surface-sunken rounded-full mt-2">
                <div className="h-full bg-blue-500/60 rounded-lg" style={{ width: `${d?.distribucion_genero?.hombres_pct ?? 0}%` }}></div>
              </div>
            </div>
            <div className="flex-1 text-center">
              <div className="flex items-center gap-2">
                <span className="mono texto-principal fuente-negrita">Mujeres</span>
                <span className="mono texto-meta texto-desvanecido">{d?.distribucion_genero?.mujeres?.toLocaleString("es-MX") ?? "0"}</span>
              </div>
              <div className="w-full h-2 bg-surface-sunken rounded-full mt-2">
                <div className="h-full bg-indigo-500/60 rounded-lg" style={{ width: `${d?.distribucion_genero?.mujeres_pct ?? 0}%` }}></div>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      {/* Tabla de cohortes recientes */}
      <Panel
        detalle="Cohortes recientes"
        objetivo={`Últimos ${d?.cohortes?.length ?? 0} registros`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        {d?.cohortes?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-meta texto-desvanecido">
                <tr>
                  <th className="pb-2">Fecha</th>
                  <th className="pb-2">Cohorte</th>
                  <th className="pb-2">Total</th>
                  <th className="pb-2">Tasa particip.</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {d.cohortes.slice(0, 10).map((c: any) => (
                  <tr key={c.id} className="hover:bg-surface-sunken/50">
                    <td className="mono texto-micro texto-desvanecido">{c.fecha}</td>
                    <td className="mono texto-principal fuente-negrita">{c.cohorte}</td>
                    <td className="mono texto-principal fuente-negrita">{c.total.toLocaleString("es-MX")}</td>
                    <td className="mono texto-meta texto-desvanecido">{c.tasa_participacion}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <SinDatos título="Sin cohortes registradas" />
        )}
      </Panel>
    </div>
  );
}
