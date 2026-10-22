/**
 * PADRE + JUEZ — superficie MONITOR.
 *
 * Padre es el árbitro jerárquico. Juez es el auditor que compara predicción
 * con realidad. Ambos juntos muestran si el sistema está aprendiendo o
 * si hay que desconfiar de sus predicciones.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, BarraVeredictos, SinDatos, BannerError } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function PadreJuezTab() {
  const padreF = useCallback(() => api.bots(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);

  const padre = usePoll(padreF, 30000);
  const juez = usePoll(juezF, 30000);

  const padreData = padre.data?.items as Record<string, unknown>[] || [];
  const juezData = juez.data?.items as Record<string, unknown>[] || [];

  const padreItems = padreData.map((b) => ({
    nombre: String(b.bot_name || b.nombre || "Desconocido"),
    peso: Number(b.peso_voto ?? 0),
    features: Number(b.feature_count ?? 0),
    fecha_ultimo: String(b.updated_at ?? ""),
  }));

  const juecesConVoto = juezData.filter((r) => r.peso_voto != null && Number(r.peso_voto) > 0).length;
  const aciertosJ = juezData.filter((r) => String(r.resultado || "").toUpperCase() === "ACIERTO").length;
  const fallosJ = juezData.filter((r) => String(r.resultado || "").toUpperCase() === "FALLO").length;
  const fpJ = juezData.filter((r) => String(r.resultado || "").toUpperCase() === "FALSO_POSITIVO").length;

  if (padre.error) return <BannerError mensaje={padre.error} />;
  if (padre.loading && !padre.data) return <SinDatos titulo="Cargando bots Padre..." />;

  return (
    <div className="space-y-5">
      {/* Resumen Padre */}
      <Panel
        detalle="Padre — Consenso jerárquico"
        objetivo={`${padreItems.length} bots · ${padreItems.length > 0 ? padreItems.reduce((a, b) => a + Number(b.peso_voto ?? 0), 0) : 0} pesos totales`}
        riesgo="BAJO"
        acción="verificar pesos"
      >
        <div className="grid gap-4 md:grid-cols-3">
          <Metrica
            detalle="Bots activos"
            objetivo={`${padreItems.length}`}
            riesgo={padreItems.length > 0 ? "BAJO" : "ALTO"}
            acción="revisar lista"
          />
          <Metrica
            detalle="Peso total"
            objetivo={padreItems.reduce((a, b) => a + Number(b.peso_voto ?? 0), 0).toFixed(2)}
            riesgo="BAJO"
            acción="verificar"
          />
          <Metrica
            detalle="Pesos únicos"
            objetivo={new Set(padreData.map((r) => r.peso_voto)).size}
            riesgo="BAJO"
            acción="verificar"
          />
        </div>
      </Panel>

      {/* Veredictos Juez */}
      <Panel
        detalle="Juez — Real vs Predicción"
        objetivo={`${juecesConVoto} con voto · ${aciertosJ} aciertos · ${fallosJ} fallos · ${fpJ} falsos positivos`}
        riesgo={falsosPositivos > aciertosJ ? "ALTO" : "BAJO"}
        acción="auditar modelo"
      >
        <BarraVeredictos aciertos={aciertosJ} falsosPositivos={fpJ} fallos={fallosJ} />
      </Panel>

      {/* Tabla Padre */}
      <Panel
        detalle="Pesos de bots (Padre)"
        objetivo={`${padreItems.length} bots registrados`}
        riesgo="BAJO"
        acción="revisar pesos"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-meta texto-desvanecido border-b border-border pb-2">
                <th className="texto-izquierda pb-2">Bot</th>
                <th className="texto-derecha pb-2">Peso</th>
                <th className="texto-meta texto-desvanecido pb-2">Features</th>
                <th className="texto-meta texto-desvanecido pb-2">Última actualización</th>
              </tr>
            </thead>
            <tbody>
              {padreItems.map((bot) => (
                <tr key={bot.nombre} className="border-b border-border/50 last:border-0">
                  <td className="texto-principal fuente-negrita">{bot.nombre}</td>
                  <td className="mono texto-principal fuente-negrita">{bot.peso.toFixed(2)}</td>
                  <td className="mono texto-meta texto-desvanecido">{bot.features}</td>
                  <td className="mono texto-meta texto-desvanecido">{fmtTs(bot.fecha_ultimo)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Historial Juez reciente */}
      <Panel
        detalle="Últimos veredictos del Juez"
        objetivo={`${juecesConVoto} con voto`}
        riesgo={falsosPositivos > 0 ? "MEDIO" : "BAJO"}
        acción="auditar resultados"
      >
        <div className="space-y-2">
          {juecesData.slice(0, 10).map((j, i) => (
            <div key={i} className="flex items-center gap-3 p-2 rounded-lg border border-border bg-surface-sunken">
              <span className="mono texto-principal fuente-negrita">
                {String(j.resultado || "—").toUpperCase()}
              </span>
              <span className="mono texto-meta texto-desvanecido">
                {j.bot_name || "bot desconocido"}
              </span>
              <span className="mono texto-meta texto-desvanecido">
                {fmtTs(j.timestamp || j.ts || j.fecha)}
              </span>
              <span className="mono texto-principal fuente-negrita ml-auto">
                {j.peso_voto != null ? j.peso_voto.toFixed(2) : "—"}
              </span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
