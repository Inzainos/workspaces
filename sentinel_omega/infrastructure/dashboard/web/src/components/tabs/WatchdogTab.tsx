/**
 * Watchdog - Pantalla de monitoreo de seguridad
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";

export function WatchdogTab() {
  const estadoF = useCallback(() => api.estado(), []);
  const estado = usePoll(estadoF, 60000);

  const d = estado.data as any;

  if (estado.error) return <BannerError mensaje={estado.error} />;
  if (estado.loading && !estado.data) return <SinDatos título="Cargando estado del watchdog..." />;

  return (
    <div className="space-y-5">
      {/* Resumen general */}
      <div className="grid gap-4 md:grid-cols-3">
        <Panel
          detalle="Estado del sistema"
          objetivo={d?.estado?.estado || "desconocido"}
          riesgo={d?.estado?.estado === "en_linea" ? "BAJO" : "ALTO"}
          acción={d?.estado?.estado === "en_linea" ? "monitorear" : "reiniciar"}
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">Estado del sistema</span>
              <span className="mono texto-meta texto-desvanecido">
                {d?.estado?.estado === "en_linea" ? "en línea" : "desconectado"}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">Última sincronización:</span>
              <span className="mono texto-meta texto-desvanecido">{fmtTs(d?.estado?.ultima_sincronizacion)}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">Núcleos activos:</span>
              <span className="mono texto-principal fuente-negrita">{d?.estado?.nucleos_activos ?? 0}</span>
            </div>
          </div>
        </Panel>
        <Panel
          detalle="Votos recientes"
          objetivo={`${d?.votaciones?.total_votos ?? 0}`}
          riesgo="BAJO"
          acción="ver detalle"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={d?.votaciones?.total_votos ?? 0} />
              </span>
              <span className="mono texto-micro texto-desvanecido">votos totales</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={d?.votaciones?.votos_aprobados ?? 0} />
              </span>
              <span className="mono texto-micro texto-desvanecido">aprobados</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={d?.votaciones?.votos_rechazados ?? 0} />
              </span>
              <span className="mono texto-micro texto-desvanecido">rechazados</span>
            </div>
          </div>
        </Panel>
        <Panel
          detalle="Nodos activos"
          objetivo={`${d?.red?.nodos_activos ?? 0}`}
          riesgo="BAJO"
          acción="ver detalle"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">{d?.red?.nodos_activos ?? 0}</span>
              <span className="mono texto-micro texto-desvanecido">nodos conectados</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={d?.red?.latencia_promedio_ms?.toFixed(0) ?? "—"} />
              </span>
              <span className="mono texto-micro texto-desvanecido">latencia promedio (ms)</span>
            </div>
          </div>
        </Panel>
      </div>

      {/* Tabla de nodos recientes */}
      <Panel
        detalle="Nodos recientes"
        objetivo={`${d?.red?.nodos_recientes?.length ?? 0}}`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        {d?.red?.nodos_recientes?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-meta texto-desvanecido">
                <tr>
                  <th className="pb-2">Nodo</th>
                  <th className="pb-2">Estado</th>
                  <th className="pb-2">Última actividad</th>
                  <th className="pb-2">Latencia</th>
                </tr>
              </thead>
              <tbody>
                {d?.red?.nodos_recientes.slice(0, 10).map((nodo: any) => (
                  <tr key={nodo.id} className="hover:bg-surface-sunken">
                    <td className="mono texto-micro texto-desvanecido">{nodo.id}</td>
                    <td className="mono texto-principal fuente-negrita">{nodo.estado}</td>
                    <td className="mono texto-micro texto-desvanecido">{fmtTs(nodo.ultima_actividad)}</td>
                    <td className="mono texto-micro texto-desvanecido">{nodo.latencia_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <SinDatos título="Sin nodos recientes" />
        )}
      </Panel>

      {/* Estadísticas de votación */}
      <Panel
        detalle="Estadísticas de votación"
        objetivo={`${d?.votaciones?.total_votos ?? 0}`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-superficie-sunken">
            <span className="mono texto-meta texto-desvanecido">Votos aprobados</span>
            <span className="mono texto-principal fuente-negrita texto-esmeralda-400">
              {d?.votaciones?.votos_aprobados ?? 0}
            </span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-superficie-sunken">
            <span className="mono texto-meta texto-desvanecido">Votos rechazados</span>
            <span className="mono texto-principal fuente-negrita texto-rose-400">
              {d?.votaciones?.votos_rechazados ?? 0}
            </span>
          </div>
        </div>
      </Panel>
    </div>
  );
}
