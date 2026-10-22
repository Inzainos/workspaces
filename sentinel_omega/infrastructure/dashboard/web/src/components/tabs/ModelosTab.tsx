/**
 * Predicciones - Pantalla de predicciones del motor Sentinel
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function PrediccionesTab() {
  const mlF = useCallback(() => api.muroLags(), []);
  const ml = usePoll(mlF, 20000);

  const d = ml.data as any;

  if (ml.error) return <BannerError mensaje={ml.error} />;
  if (ml.loading && !ml.data) return <SinDatos título="Cargando datos de muros..." />;

  const mlActivo = d?.activo ?? false;
  const rest = ml.data?.dias_restantes ?? [];
  const activas = d?.activos ?? [];

  return (
    <div className="space-y-5">
      {/* Panel de estado */}
      <Panel
        detalle="Muro de lógicas"
        objetivo={`${mlActivo ? "Activo" : "Inactivo"}`}
        riesgo={mlActivo ? "MEDIO" : "BAJO"}
        acción="Ver detalle"
      >
        <div className="flex items-center gap-4">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: mlActivo ? "var(--color-esmeralda-400)" : "var(--color-gris-medio)" }}></div>
          <span className={`mono texto-principal fuente-negrita ${mlActivo ? "texto-esmeralda-400" : "texto-desvanecido"}`}>
            {mlActivo ? "ACTIVO" : "INACTIVO"}
          </span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="mono texto-desvanecido">Días restantes:</span>
          <span className="mono texto-principal fuente-negrita">
            {mlActivo && rest.length > 0 ? rest.join(" - ") : "—"}
          </span>
        </div>
      </Panel>

      {/* Tabla de nodos */}
      <Panel
        detalle="Nodos del muro"
        objetivo={`${d?.nodos?.length ?? 0} nodos`}
        riesgo="BAJO"
        acción="ver detalles"
      >
        {d?.nodos?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="texto-meta texto-desvanecido">
                <tr>
                  <th className="pb-2">Nodo</th>
                  <th className="pb-2">Estado</th>
                  <th className="pb-2">Saturación</th>
                  <th className="pb-2">Última actualización</th>
                </tr>
              </thead>
              <tbody>
                {d?.nodos.slice(0, 10).map((nodo: any) => (
                  <tr key={nodo.id} className="hover:bg-surface-sunken">
                    <td className="mono texto-micro texto-desvanecido">{nodo.nombre || nodo.id}</td>
                    <td className="mono texto-principal fuente-negrita">{nodo.estado || "desconocido"}</td>
                    <td className="mono texto-principal fuente-negrita">{nodo.saturacion?.toFixed(2) ?? "—"}</span>
                    <td className="mono texto-micro texto-desvanecido">{fmtTs(nodo.ultima_actualizacion)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <SinDatos título="Sin nodos registrados" />
        )}
      </Panel>

      {/* Métricas adicionales */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel
          detalle="Tasa de éxito"
          objetivo={`${d?.tasa_exito ?? 0}%`}
          riesgo={d?.tasa_exito >= 90 ? "BAJO" : d?.tasa_exito >= 70 ? "MEDIO" : "ALTO"}
          acción="ver historial"
        >
          <div className="flex items-baseline gap-2">
            <span className="mono texto-principal fuente-negrita">{d?.tasa_exito?.toFixed(1) ?? "—"}%</span>
          </div>
        </Panel>
        <Panel
          detalle="Última actualización"
          objetivo={d?.ultima_actualizacion ? fmtTs(d.ultima_actualizacion) : "—"}
          riesgo="BAJO"
          acción="ver histórico"
        >
          <div className="flex items-baseline gap-2">
            <span className="mono texto-principal fuente-negrita">
              {d?.ultima_actualizacion ? new Date(d.ultima_actualizacion).toLocaleString("es-MX") : "—"}
            </span>
          </div>
        </div>
      </Panel>
    </div>
  );
}
