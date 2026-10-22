/**
 * PrincipalTab - Tablero principal de Sentinel Omega
 * Vista general del estado del sistema con métricas clave y estado de los bots
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, BarraVeredictos, SinDatos, BannerError, nivelDe, colorNivel, accionNivel, esAusente } from "@/components/ui/data";
import { Gauge } from "@/components/charts/componentes";

export function PrincipalTab() {
  const ovF = useCallback(() => api.overview(), []);
  const ov = usePoll(evF, 20000);

  const d = ov.data as any;

  if (ov.error) return <BannerError mensaje={ov.error} />;
  if (ov.loading && !ov.data) return <SinDatos título="Cargando estado del sistema…" />;

  return (
    <div className="space-y-5">
      {/* ================= FRANJA DE ESTADO ================= */}
      <Panel
        detalle="Estado del sistema"
        riesgo={d?.estado?.nivel === "ALTO" ? "ALTO" : d?.estado?.estado === "MODERATE" ? "MEDIO" : "BAJO"}
        acción="revisar vigía"
      >
        <div className="flex flex-col lg:flex-row items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={d?.fantasma?.valor ?? 0} />
              </span>
              <span
                className={`mono texto-micro fuente-negrita ${nivel === "CRITICAL" ? "texto-critico" : nivel === "HIGH" ? "texto-aviso" : nivel === "MODERATE" ? "texto-amarillo-400" : "texto-calma"}`}
              >
                {nivel === "DESCONOCIDO" ? "sin lectura" : nivel === "LOW" ? "calma" : nivel === "MODERATE" ? "atención" : nivel === "HIGH" ? "avisar" : "protocolo"}
              </span>
            </div>
            <p className="mt-2 texto-meta texto-desvanecido">
              {d?.ciclo?.geo_signal || "Sin datos de telemetría"} · {d.ciclo?.geo_confidence ? `confianza ${Math.round(d.ciclo.geo_confidence * 100)}%` : ""}
            </p>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metrica
              detalle="Riesgo"
              riesgo={nivel === "ALTO" ? "ALTO" : nivel === "MEDIO" ? "MEDIO" : "BAJO"}
              acción="revisar vigía"
            />
            <Metrica
              detalle="Ganancia sobre azar"
              objetivo={d?.auditoria?.ganancia_asimetrica != null ? `${d.auditoria.ganancia_asimetrica.toFixed(2)}×` : "—"}
              riesgo={aporta ? "MEDIO" : "BAJO"}
              acción="revisar modelo"
            />
            <Metrica
              detalle="Cimática (Omega)"
              objetivo={d?.omega?.esquema ? `${d.omega.esquema.toFixed(1)}×` : "—"}
              riesgo="MEDIO"
              acción="ver detalles"
            />
            <Metrica
              detalle="Muro de 5 Eventos"
              objetivo={d?.pared?.muros_activos?.toString() ?? "0"}
              riesgo={muros > 3 ? "ALTO" : "BAJO"}
              acción="revisar muros"
            />
          </div>
        </div>
      </Panel>

      {/* ================= Mapa de Antecedentes ================= */}
      <Panel
        detalle="Mapa de antecedentes sísmicos"
        objetivo={`${d?.eventos_registrados?.length ?? 0} eventos`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        <div className="h-96">
          <MapaSísmico datos={d?.eventos_recientes ?? []} altura={300} />
        </div>
      </Panel>

      {/* ================= Firma Padre ================= */}
      <Panel
        detalle="Firma Padre"
        objetivo={`Firma: ${d?.firma_padre?.firma_hash?.slice(0, 16) ?? "—"}`}
        riesgo="MEDIO"
        acción="ver detalle"
      >
        <div className="flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="mono texto-micro texto-desvanecido">Firma padre:</span>
            <span className="mono texto-micro texto-desvanecido">{d?.firma_padre?.firma_hash?.slice(0, 16) ?? "—"}</span>
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="mono texto-micro texto-desvanecido">Fase:</span>
            <span className="mono texto-primal fuente-negrita">{d?.firma_padre?.fase ?? "—"}</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="mono texto-micro texto-desvanecido">Consolidación:</span>
            <span className="mono texto-meta texto-desvanecido">{d?.firma_padre?.consolidación?.toFixed(2) ?? "—"}%</span>
          </div>
        </div>
      </Panel>
    </div>
  );
}

function pct(v: unknown, dig = 1): string {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(dig)}%`;
}

function capitalizar(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
