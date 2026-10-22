/**
 * SEÑALES — superficie MONITOR.
 *
 * Telemetría cruda por familia. Cada señal cruda se muestra con su valor
 * real; los nulos se omiten para no confundir ausencia con cero.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { SimpleBars, Gauge } from "@/components/charts/componentes";
import { Panel, Cifra, SinDatos, BannerError } from "@/components/ui/data";

export function SeñalesTab() {
  const schFn = useCallback(() => api.schumannVivo(120), []);
  const climaFn = useCallback(() => api.climaEspacial(80), []);
  const deltaFn = useCallback(() => api.delta(80), []);
  const telFn = useCallback(() => api.telemetry(), []);

  const sch = usePoll(schFn, 30000);
  const climaData = usePoll(climaFn, 30000);
  const deltaData = usePoll(deltaFn, 30000);
  const tel = usePoll(telFn, 30000);

  const schLatest = (sch.data?.items?.[0] ?? null) as any;
  const schAct = schLatest?.schumann_activity;
  const climaItems = (climaData.data?.items ?? []) as any[];
  const bzLast = climaItems.length > 0 ? climaItems[climaItems.length - 1]?.bz_nT : null;
  const kpLast = climaItems.length > 0 ? climaItems[climaItems.length - 1]?.kp_max : null;
  const deltaItems = (deltaData.data?.delta ?? []) as any[];
  const deltaLast = deltaItems.length > 0 ? deltaItems[deltaItems.length - 1]?.composite_score : null;

  if (sch.error && climaData.error && deltaData.error) {
    return <BannerError mensaje="Todas las fuentes de señales fallaron" />;
  }

  return (
    <div className="space-y-5">
      {/* Schumann — actividad (la frecuencia no se mide desde el retiro del Hz) */}
      <Panel
        detalle="Beta-1 — Resonancia Schumann"
        objetivo="Tomsk · frecuencia sin medir, solo actividad"
        riesgo={schAct != null && schAct > 15 ? "MEDIO" : "BAJO"}
        accion="verificar fuente"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={schAct} digits={1} />
              </span>
              <span className="mono texto-micro texto-desvanecido">% actividad</span>
            </div>
            <p className="mt-2 texto-meta texto-desvanecido">
              La frecuencia NO se mide desde el 2026-10-09 (la «fórmula» 7,83+act×0,02 era un derivado, se retiró).
              Lo único medido en vivo es la ACTIVIDAD (intensidad del espectrograma de Tomsk).
            </p>
            {schLatest && (
              <p className="mt-1 texto-micro texto-desvanecido">
                Última lectura: {String(schLatest.timestamp_blk ?? "—").slice(0, 16)} UTC
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <span className="texto-micro texto-desvanecido">Lecturas recientes</span>
              <span className="mono texto-principal fuente-negrita">{sch.data?.items?.length ?? 0}</span>
            </div>
          </div>
        </div>
      </Panel>

      {/* Clima espacial */}
      <Panel
        detalle="Clima espacial"
        objetivo={`${climaItems.length} lecturas`}
        riesgo={kpLast != null && kpLast >= 5 ? "ALTO" : bzLast != null && Math.abs(bzLast) > 10 ? "MEDIO" : "BAJO"}
        acción="verificar Bz"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex flex-col">
            <span className="texto-micro texto-desvanecido">Bz (nT)</span>
            <span className="mono texto-principal fuente-negrita text-xl">
              <Cifra valor={bzLast} digits={1} />
            </span>
          </div>
          <div className="flex flex-col">
            <span className="texto-micro texto-desvanecido">Kp máximo</span>
            <span className="mono texto-principal fuente-negrita text-xl">
              <Cifra valor={kpLast} digits={1} />
            </span>
          </div>
          <div className="flex flex-col">
            <span className="texto-micro texto-desvanecido">Estado</span>
            <span className={`mono texto-micro fuente-negrita ${kpLast >= 5 ? "texto-critico" : kpLast >= 4 ? "texto-aviso" : "texto-calma"}`}>
              {kpLast >= 5 ? "TORMENTA" : kpLast >= 4 ? "INQUIETUD" : "CALMA"}
            </span>
          </div>
        </div>
      </Panel>

      {/* Delta (financiero) */}
      <Panel
        detalle="Delta — Financiero"
        objetivo={`${deltaItems.length} lecturas`}
        riesgo={deltaLast != null && Math.abs(deltaLast) > 2 ? "MEDIO" : "BAJO"}
        acción="verificar tendencias"
      >
        {deltaItems.length > 0 ? (
          <div className="flex flex-col gap-2">
            {deltaItems.slice(-5).map((r, i) => (
              <div key={i} className="flex items-baseline justify-between border-b border-border/30 pb-1">
                <span className="texto-micro texto-desvanecido">{String(r.timestamp_blk ?? "—").slice(0, 16)}</span>
                <span className="mono texto-principal fuente-negrita">
                  <Cifra valor={r.composite_score} digits={3} />
                </span>
              </div>
            ))}
          </div>
        ) : (
          <SinDatos titulo="Sin datos financieros" detalle="El bot delta no tiene lecturas recientes." />
        )}
      </Panel>

      {/* Telemetría del ciclo */}
      <Panel
        detalle="Telemetría del ciclo actual"
        objetivo="Último snapshot"
        riesgo={tel.error ? "ALTO" : "BAJO"}
        acción="ver detalle"
      >
        {tel.error ? (
          <BannerError mensaje="No se pudo leer la telemetría" />
        ) : tel.data ? (
          <div className="flex flex-col gap-1">
            {(tel.data?.sources ?? []).map((s: any, i: number) => (
              <div key={i} className="flex items-baseline justify-between border-b border-border/30 pb-1">
                <span className="texto-micro texto-desvanecido">{s.label ?? s.id ?? "—"}</span>
                <span className="mono texto-micro">{s.inbound?.status ?? "—"}</span>
              </div>
            ))}
          </div>
        ) : (
          <SinDatos titulo="Cargando telemetría..." />
        )}
      </Panel>
    </div>
  );
}
