import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { TabIntro, Caption } from "@/components/TabIntro";
import { fmtTs } from "@/lib/utils";

/** Tab Reportes — bitácora versionada + canales (correo/Telegram) + Roy. */
export function ReportesTab() {
  const rep = usePoll(useCallback(() => api.reportes(), []), 60000);
  const tg = usePoll(useCallback(() => api.telegramStatus(), []), 60000);
  const files = rep.data?.files || [];
  const tgData = (tg.data || {}) as Record<string, unknown>;

  const rutina = [
    ["REPORTE.md · estado del sistema", "semáforo, percentiles, ventana temporal", "cada 2 h"],
    ["REPORTE_EJECUTIVO.md", "plantilla extendida · ventana de atención + countdown", "cada 6 h"],
    ["Comparativo diario", "hoy vs ayer · aciertos 24 h · gráficas", "12am/12pm"],
    ["Reporte semanal", "7 días · desempeño por bot · lectura rápida + glosario", "dom 12:15"],
    ["Reporte mensual", "31 días · aciertos + cimática + glosario", "fin de mes"],
  ];

  return (
    <div className="space-y-6">
      <TabIntro title="Reportes — la bitácora versionada del sistema">
        <p>
          Los "ojos" de Sentinel: cada corte se guarda en <span className="mono">estado/historial/AAAA/MM</span> (hora MX,
          nunca se sobrescribe) y viaja por <b>correo</b> y <b>Telegram</b>. Roy Vigilante (GitHub Actions) los genera 24/7
          sin servidor.
        </p>
      </TabIntro>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        {/* Cadencia + archivos */}
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-3 text-sm font-medium">Reportes por cadencia</div>
          <div className="divide-y divide-white/5">
            {rutina.map(([name, desc, when]) => (
              <div key={name} className="flex items-center justify-between py-2.5">
                <div className="flex flex-col gap-0.5">
                  <span className="text-[13px] font-medium">{name}</span>
                  <span className="text-xs text-muted">{desc}</span>
                </div>
                <span className="mono text-[11px] text-muted">{when}</span>
              </div>
            ))}
          </div>
          {files.length ? (
            <div className="mt-4">
              <div className="mono mb-1 text-[11px] uppercase tracking-wide text-muted">archivos en estado/</div>
              <ul className="space-y-0.5">
                {files.slice(0, 6).map((f) => (
                  <li key={f.name} className="mono flex justify-between text-[11px] text-muted">
                    <span className="truncate">{f.name}</span>
                    <span>{(f.bytes / 1024).toFixed(1)} KB · {fmtTs(f.mtime)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        {/* Canales + ONNX */}
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="mb-3 text-sm font-medium">Canales de entrega</div>
            <div className="space-y-2 text-[12.5px]">
              <div className="flex items-center gap-2.5">
                <span className="h-2 w-2 rounded-full bg-success" />
                <span>Correo — outbox <span className="mono">tbl_correo_salida</span></span>
                <span className="mono ml-auto text-[10.5px] text-success">activo</span>
              </div>
              <div className="flex items-center gap-2.5">
                <span className={`h-2 w-2 rounded-full ${tgData.configured ? "bg-success" : "bg-warning"}`} />
                <span>Telegram — resumen + gráficas + .md</span>
                <span className={`mono ml-auto text-[10.5px] ${tgData.configured ? "text-success" : "text-warning"}`}>
                  {tgData.configured ? "activo" : "dry-run"}
                </span>
              </div>
            </div>
            <Caption>Fail-soft: sin credenciales el envío queda PENDIENTE, nunca se finge enviado.</Caption>
          </div>
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-sm font-medium">Reentrenamiento ONNX</span>
              <span className="mono text-[11px] uppercase text-muted">desde la DB</span>
            </div>
            <p className="text-xs leading-relaxed text-muted">
              Los 7 modelos ONNX se reentrenan desde <span className="mono">TBL_FIRMAS</span> semanalmente. La DB es la
              fuente de verdad; las redes se derivan de ella.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3.5 rounded-lg border border-border bg-panel px-5 py-4">
        <div className="grid h-9 w-9 place-items-center rounded-lg" style={{ background: "rgba(16,185,129,0.12)" }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4" /><circle cx="12" cy="12" r="3" /></svg>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[13.5px] font-semibold">Roy Vigilante — 24/7 en GitHub Actions</span>
          <span className="text-xs text-muted">
            Corre un ciclo cada 2 h sin servidor, commitea los reportes a <span className="mono">estado/</span> y despacha
            el correo.
          </span>
        </div>
      </div>
    </div>
  );
}
