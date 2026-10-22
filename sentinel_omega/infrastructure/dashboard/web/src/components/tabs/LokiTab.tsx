/**
 * LokiTab - Resonancia de rotación solar
 * Analiza la resonancia de rotación solar (Carrington 26-29 días)
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";
import { fmtNum } from "@/lib/utils";

export function LokiTab() {
  const kpF = useCallback(() => api.loki_kp(), []);
  const kp = usePoll(kpF, 30000);

  const d = kp.data as any;

  if (kp.error) return <BannerError mensaje={kp.error} />;
  if (kp.loading && !kp.data) return <SinDatos título="Cargando datos de rotación solar..." />;

  return (
    <div className="space-y-5">
      {/* Resumen */}
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica
          detalle="Ganancia 3.4×"
          objetivo={d?.ganancia?.toFixed(2) ?? "—"}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Período de rotación"
          objetivo={`${d?.periodo_días?.toFixed(1) ?? "—"} días`}
          riesgo="BAJO"
          acción="ver detalle"
        />
        <Metrica
          detalle="Estado actual"
          objetivo={kpValor >= 5 ? "ACTIVO" : "INACTIVO"}
          riesgo={kpValor >= 5 ? "ALTO" : "BAJO"}
          acción="ver detalle"
        />
      </div>

      {/* Serie temporal de Kp */}
      <Panel
        detalle="Kp histórico (últimas 28 días)"
        objetivo={`Últimas ${kp_items.length} lecturas`}
        riesgo={kpValor >= 5 ? "ALTO" : "BAJO"}
        acción="ver detalle"
      >
        <div className="h-64">
          <LíneaSerie
            datos={kp_items.map((k: any) => ({ x: k.fecha, y: Number(k.kp_mean) }))}
            objetivo="Kp"
            altura={240}
            color="#ef4444"
            destacarÚltimo={true}
          />
        </div>
      </Panel>

      {/* Historial de rotación */}
      <Panel
        detalle="Historia de rotación"
        objetivo={`Últimos ${rotaciones.length} ciclos`}
        riesgo="BAJO"
        acción="ver detalle"
      >
        <div className="space-y-2">
          {kp_items.slice(0, 10).map((k, i) => (
            <div key={i} className="flex items-center gap-2 p-2 rounded-lg border border-border bg-surface-sunken">
              <span className="mono texto-micro texto-desvanecido w-20">{c.fecha}</span>
              <span className="mono texto-principal fuente-negrita">{c.kp_mean.toFixed(2)}</span>
              <span className={`mono texto-micro texto-desvanecido ${c.kp_mean >= 5 ? "texto-critico" : "texto-calma"}`}>
                {c.kp_mean >= 5 ? "Kp≥5" : "Estable"}
              </span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function pct(v: unknown, dig = 1): string {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(dig)}%`;
}
