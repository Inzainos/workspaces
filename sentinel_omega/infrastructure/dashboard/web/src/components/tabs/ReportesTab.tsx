/**
 * REPORTES - Pantalla de reportes y auditoría
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function ReportesTab() {
  const reporteF = useCallback(() => api.reportes(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);

  const reporte = usePoll(reporteF, 30000);
  const juez = usePoll(juezF, 30000);

  const reporteData = reporte.data as any;
  const juezData = juez.data?.items as Record<string, unknown>[] || [];

  const aciertos = Number(juecesData.filter((r) => String(r.resultado || "").toUpperCase() === "ACIERTO").length || 0);
  const fallos = Number(juecesData.filter((r) => String(r.resultado || "").toUpperCase() === "FALLO").length || 0);
  const falsosPositivos = Number(juecesData.filter((r) => String(r.resultado || "").toUpperCase() === "FALSO_POSITIVO").length || 0);
  const totalVeredictos = aciertos + fallos + falsosPositivos;

  if (reporte.error) return <BannerError mensaje={reporte.error} />;
  if (reporte.loading && !reporte.data) return <SinDatos titulo="Cargando reportes..." />;

  return (
    <div className="space-y-5">
      {/* Resumen de veredictos */}
      <Panel
        detalle="Resumen de veredictos del Juez"
        objetivo={`${totalVeredictos} veredictos evaluados`}
        riesgo={falsosPositivos > aciertos ? "ALTO" : "BAJO"}
        acción="Revisar casos falsos"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Metrica
            detalle="Aciertos"
            objetivo={aciertos.toString()}
            riesgo="BAJO"
            acción="Ver detalle"
            icono={<CheckCircle className="w-4 h-4 texto-emerald-400" />}
          />
          <Metrica
            detalle="Falsos positivos"
            objetivo={fpJ.toString()}
            riesgo={fpJ > aciertos ? "ALTO" : "BAJO"}
            acción="Investigar"
          />
          <Metrica
            detalle="Fallos"
            objetivo={fallos.toString()}
            riesgo={fallos > aciertos ? "ALTO" : "BAJO"}
            acción="Auditar"
          />
        </div>
      </Panel>

      {/* Lista de veredictos recientes */}
      <Panel
        detalle="Últimos veredictos del Juez"
        objetivo={`Mostrando ${Math.min(juecesData.length, 10)} de ${juecesData.length}`}
        riesgo="BAJO"
        acción="Exportar reporte"
      >
        {juecesData.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-meta texto-desvanecido border-b border-border pb-2">
                  <th className="texto-izquierda pb-2">Fecha</th>
                  <th className="texto-izquierda pb-2">Bot</th>
                  <th className="texto-izquierda pb-2">Resultado</th>
                  <th className="texto-izquierda pb-2">Peso</th>
                  <th className="texto-izquierda pb-2">Estatus</th>
                </tr>
              </thead>
              <tbody>
                {juecesData.slice(0, 10).map((j, i) => (
                  <tr key={i} className="border-b border-border/50 last:border-0">
                    <td className="mono texto-meta texto-desvanecido">{fmtTs(j.timestamp || j.fecha)}</td>
                    <td className="mono texto-principal fuente-negrita">{j.bot_name || "bot desconocido"}</td>
                    <td className={`mono texto-principal fuente-negrita ${String(j.resultado || "").toUpperCase() === "ACIERTO" ? "texto-esmeralda-400" : String(j.resultado || "").toUpperCase() === "FALLO" ? "texto-rose-400" : "texto-orange-400"}`}>
                      {j.resultado || "—"}
                    </td>
                    <td className="mono texto-meta texto-desvanecido">{j.peso_voto?.toFixed(2) ?? "—"}</td>
                    <td className="mono texto-meta texto-desvanecido">{j.validado ? "Verificado" : "Pendiente"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <SinDatos título="Sin veredictos del Juez" detalle="No hay datos de veredictos disponibles aún." />
        )}
      </Panel>

      {/* Panel de reportes disponibles */}
      <Panel
        detalle="Reportes disponibles"
        objetivo={`${reporteData?.files?.length ?? 0} reportes`}
        riesgo="BAJO"
        acción="Descargar"
      >
        <div className="space-y-2">
          {reporteData?.files?.map((f: any, i: number) => (
            <div key={i} className="flex items-center justify-between p-2 rounded-lg border border-border bg-surface-sunken">
              <div className="flex items-center gap-2">
                <span className="mono texto-meta texto-desvanecido">📄</span>
                <span className="mono texto-primal fuente-negrita">{f.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="mono texto-meta texto-desvanecido">{fmtTs(f.mtime)}</span>
                <span className="mono texto-meta texto-desvanecido">
                  {(f.bytes / 1024).toFixed(1)} KB
                </span>
                <button className="mono texto-micro texto-emerald-400 hover:texto-esmeralda-400">Descargar</button>
              </div>
            </div>
          ))}
          {reporteData?.files?.length === 0 && (
            <div className="text-meta texto-desvanecido text-center py-4">
              No hay reportes disponibles aún. Ejecute una corrida para generar reportes.
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
