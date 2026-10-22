/**
 * SEÑALES — superficie MONITOR.
 *
 * Telemetría cruda por familia. Cada señal cruda se muestra con su valor
 * real; los nulos se ominten para no confundir ausencia con cero.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { SimpleBars } from "@/components/charts/componentes";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";
import { Gauge } from "@/components/charts/componentes";

export function SeñalesTab() {
  const sch = useCallback(() => api.schumannVivo(120), []);
  const clima = useCallback(() => api.climaEspacial(80), []);
  const delta = useCallback(() => api.delta(80), []);
  const ca = useCallback(() => api.cimaticaAhora(), []);
  const salud = useCallback(() => api.telemetry(), []);
  const tel = usePoll(useCallback(() => api.telemetry(), []), 30000);

  const sch = usePoll(sch, 30000);
  const climaData = usePoll(clima, 30000);
  const deltaData = usePoll(delta, 30000);
  const caData = usePoll(ca, 40000);

  const schS = sch.data?.items?.map((r: any) => ({ v: Number(r.schumann_hz) })).filter((p: any) => !esAusente(p.v)) || [];
  const climaItems = clima.data?.items || [];
  const dmes = climaItems.map((r: any) => ({ v: Number(r.dmes_g) })).filter((p: any) => !esAusente(p.v));
  const bzS = climaItems.map((r: any) => ({ v: Number(r.bz_nT) })).filter((p: any) => !esAusente(p.v));
  const deltaS = deltaData.data?.delta?.map((r: any) => ({ v: Number(r.composite_score) })).filter((p: any) => !esAusente(p.v)) || [];

  const schLatest = sch.data?.items?.[sch.data.items.length - 1] as any;
  const schEstado = (salud.data?.beta1 as { status?: string } | undefined)?.status || "";
  const schCongelado = schEstado === "CONGELADO";

  if (ev.error) return <BannerError mensaje={ev.error} />;
  if (ev.loading && !ev.data) return <SinDatos titulo="Leyendo señalización..." />;

  return (
    <div className="space-y-5">
      {/* beta1 Schumann */}
      <Panel
        detalle="Beta-1 — Resonancia Schumann"
        objetivo="Tomsk · referencia 7.83 Hz"
        riesgo={schCongelado ? "ALTO" : "BAJO"}
        accion="verificar fuente"
      >
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={schLatest?.schumann_hz} />
              </span>
              <span
                className={`mono texto-micro font-semibold uppercase ${schCongelado ? "texto-orange-400" : "texto-esmeralda-400"}`}
              >
                {schCongelado ? "CONGELADO" : "ACTIVO"}
              </span>
            </div>
            <p className="mt-2 texto-meta">
              {schEstado === "CONGELADO"
                ? "Esta fuente está sirviendo el mismo valor una y otra vez: la serie se refresca pero no mide nada. El Padre ignora esta señal mientras esté congelada."
                : "El latido de Schumann: todo el resto se correlaciona contra él."}
            </p>
          </div>
          <div className="h-40">
            <Sparkline
              datos={schS}
              objetivo="Schumann Hz"
              altura={200}
              color="#ef4444"
              líneasMostrar={false}
            />
          </div>
        </div>
      </Panel>

      {/* Clima espacial */}
      <Panel
        detalle="Clima espacial"
        objetivo={`${climaItems.length} lecturas`}
        riesgo={bzS.some((p) => Math.abs(p.v) > 10) ? "MEDIO" : "BAJO"}
        acción="verificar BOZ"
      >
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={bzS[bzS.length - 1]?.v} />
              </span>
              <span className="mono texto-micro fuente-negrita">nT</span>
            </div>
            <p className="texto-meta texto-desvanecido">Bz — componente sur del campo magnético interplanetario</p>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="mono texto-principal fuente-negrita">
              <Cifra valor={bzS.length > 0 ? bzS[bzS.length - 1].v : null} />
            </span>
            <span className="mono texto-micro fuente-negrita">nT</span>
          </div>
        </div>
      </Panel>

      {/* Delta (financiero) */}
      <Panel
        detalle="Delta — Financiero"
        objetivo={`${deltaS.length} lecturas`}
        riesgo={deltaS.some((p) => Math.abs(p.v) > 2) ? "MEDIO" : "BAJO"}
        acción="verificar tendencias"
      >
        <div className="h-64">
          <SimpleBars
            datos={deltaS.map((p, i) => ({ key: String(i), valor: p.v, color: "var(--color-serie-1)" }))}
            claveClave="clave"
            valorClave="valor"
            altura={240}
          />
        </div>
      </Panel>
    </div>
  );
}

function esAusente(v: unknown): boolean {
  return v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v));
}
