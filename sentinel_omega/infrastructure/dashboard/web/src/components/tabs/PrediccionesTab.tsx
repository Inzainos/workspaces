/**
 * Predicciones - Pantalla de predicciones del motor Sentinel
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";

export function PrediccionesTab() {
  const prediccionesF = useCallback(() => api.predicciones(), []);
  const predicciones = usePoll(predonF, 30000);

  const d = predicciones.data as any;

  if (predicciones.error) return <BannerError mensaje={predicciones.error} />;
  if (predicciones.loading && !predicciones.data) return <SinDatos título="Cargando predicciones..." />;

  return (
    <div className="space-y-5">
      {/* Resumen de predicciones */}
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica
          detalle="Predicciones activas"
          objetivo={d?.total_predicciones ?? 0}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Aciertos"
          objetivo={d?.aciertos ?? 0}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Falsos positivos"
          objetivo={d?.falsos_positivos ?? 0}
          riesgo="MEDIO"
          acción="revisar"
        />
      </div>

      {/* Tabla de predicciones recientes */}
      <Panel
        detalle="Últimas predicciones"
        objetivo={`${d?.predicciones?.length ?? 0} registros`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        {d?.predicciones?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-meta texto-desvanecido">
                <tr>
                  <th className="pb-2">Fecha</th>
                  <th className="pb-2">Modelo</th>
                  <th className="pb-2">Resultado</th>
                  <th className="pb-2">Probabilidad</th>
                </tr>
              </thead>
              <tbody>
                {d.cohortes.slice(0, 10).map((c: any) => (
                  <tr key={c.id} className="hover:bg-surface-sunken">
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
          <SinDatos título="Sin predicciones recientes" />
        )}
      </Panel>

      {/* Distribución por tipo */}
      <Panel
        detalle="Distribución por tipo de predicción"
        objetivo={`${d?.distribucion_por_tipo?.length ?? 0} tipos`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        <div className="flex flex-col gap-2">
          {(d?.distribucion_por_tipo || []).slice(0, 6).map((c: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-2 rounded-lg border border-border bg-superficie-sunken">
              <span className="mono texto-micro texto-desvanecido w-20">{c.tipo}</span>
              <div className="flex-1 h-2 bg-surface-sunken rounded-full">
                <div className="h-full bg-indigo-500/60 rounded-lg" style={{ width: `${ciudad.porcentaje || 0}%` }}></div>
              </div>
              <span className="mono texto-principal fuente-negrita">{c.cantidad.toLocaleString("es-MX")}</span>
            </div>
          ))}
        </div>
        </Panel>
      </div>
    </div>
  );
}
