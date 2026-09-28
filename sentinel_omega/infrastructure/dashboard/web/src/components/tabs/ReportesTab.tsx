import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, SinDatos } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

/**
 * REPORTES — superficie EXPLORE.
 *
 * Corrección de fondo respecto de la versión anterior: este tab afirmaba
 * «Correo — outbox tbl_correo_salida · activo» con un punto verde. Es falso
 * desde el 2026-09-15: `infrastructure/api/correo.py` se borró, las variables
 * SMTP están comentadas y CERO código lee esa tabla (verificado por grep el
 * 2026-09-28). `deploy/enviar_correos.py` despacha por Telegram pese a su
 * nombre. La tabla sobrevive como vestigio deliberado, no como canal.
 *
 * Un tablero que pinta en verde un canal muerto es peor que uno que no lo
 * menciona: alguien puede contar con que el aviso salió por ahí.
 */
export function ReportesTab() {
  const rep = usePoll(useCallback(() => api.reportes(), []), 60000);
  const tg = usePoll(useCallback(() => api.telegramStatus(), []), 60000);
  const files = rep.data?.files || [];
  const tgData = (tg.data || {}) as Record<string, unknown>;

  const rutina: [string, string, string][] = [
    ["REPORTE.md", "semáforo, percentiles, ventana temporal", "cada 2 h"],
    ["REPORTE_EJECUTIVO.md", "plantilla extendida · ventana de atención + countdown", "cada 6 h"],
    ["Comparativo diario", "hoy contra ayer · aciertos de 24 h · gráficas", "12am / 12pm"],
    ["Reporte semanal", "7 días · desempeño por bot · lectura rápida y glosario", "domingo 12:15"],
    ["Reporte mensual", "31 días · aciertos, cimática y glosario", "fin de mes"],
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <Panel
          titulo="Cadencia de reportes"
          meta="hora MX (UTC-6)"
          nota="Cada corte se guarda en estado/historial/AAAA/MM y nunca se sobrescribe. REPORTE.md es solo el último."
        >
          <ul className="divide-y divide-[color:var(--color-border)]">
            {rutina.map(([name, desc, when]) => (
              <li key={name} className="flex items-baseline justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <div className="mono text-body font-medium text-foreground">{name}</div>
                  <div className="text-meta text-muted">{desc}</div>
                </div>
                <span className="mono shrink-0 text-meta text-faint">{when}</span>
              </li>
            ))}
          </ul>
        </Panel>

        <div className="space-y-5">
          <Panel
            titulo="Canal de entrega"
            meta="único"
            nota="Fail-soft: sin credenciales el envío queda PENDIENTE. Nunca se marca como enviado algo que no salió."
          >
            <div className="space-y-3">
              <div className="flex items-center gap-2.5">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: tgData.configured ? "var(--color-calma)" : "var(--color-atencion)" }}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-body font-medium text-foreground">Telegram</div>
                  <div className="text-meta text-muted">resumen, gráficas y .md adjunto</div>
                </div>
                <span
                  className="mono shrink-0 text-meta"
                  style={{ color: tgData.configured ? "var(--color-calma)" : "var(--color-atencion)" }}
                >
                  {tgData.configured ? "activo" : "dry-run"}
                </span>
              </div>

              <div className="border-t border-border pt-3">
                <div className="flex items-center gap-2.5">
                  <span className="h-2 w-2 shrink-0 rounded-full bg-[color:var(--color-base-700)]" />
                  <div className="min-w-0 flex-1">
                    <div className="text-body font-medium text-muted line-through decoration-[color:var(--color-base-600)]">
                      Correo (SMTP)
                    </div>
                  </div>
                  <span className="mono shrink-0 text-meta text-faint">retirado</span>
                </div>
                <p className="mt-1.5 text-meta leading-relaxed text-muted">
                  Eliminado el 2026-09-15. <span className="mono">correo.py</span> se borró y las variables
                  SMTP están comentadas; <span className="mono">tbl_correo_salida</span> sigue en la base
                  pero ningún código la lee. <span className="mono">enviar_correos.py</span> despacha por
                  Telegram pese al nombre.
                </p>
              </div>
            </div>
          </Panel>

          <Panel titulo="Reentrenamiento ONNX" meta="desde la DB">
            <p className="text-meta leading-relaxed text-muted">
              Los modelos ONNX se reentrenan desde <span className="mono">TBL_FIRMAS</span> semanalmente.
              La base es la fuente de verdad; las redes se derivan de ella, nunca al revés.
            </p>
          </Panel>
        </div>
      </div>

      <Panel titulo="Archivos publicados" meta={`${files.length} en estado/`}>
        {files.length ? (
          <ul className="divide-y divide-[color:var(--color-border)]">
            {files.slice(0, 14).map((f) => (
              <li key={f.name} className="flex items-baseline justify-between gap-4 py-1.5 first:pt-0">
                <span className="mono truncate text-meta text-body">{f.name}</span>
                <span className="mono shrink-0 text-meta text-faint">
                  {(f.bytes / 1024).toFixed(1)} KB · {fmtTs(f.mtime)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <SinDatos titulo="Sin archivos" detalle="No hay carpeta estado/ en este árbol." />
        )}
      </Panel>

      <Panel
        titulo="Roy Vigilante"
        meta=".github/workflows/roy-vigilante.yml"
        nota="Corre un ciclo cada 2 h en GitHub Actions, sin servidor, y commitea los reportes a estado/."
      >
        <p className="text-body leading-relaxed text-body">
          El respaldo serverless del sistema: si la máquina local se cae, Roy sigue generando el corte
          cada dos horas desde Actions.
        </p>
      </Panel>
    </div>
  );
}
