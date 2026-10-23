/**
 * REPORTES — reportes publicados y auditoría del Juez.
 *
 * /api/reportes → {present, dir, files[{name, bytes, mtime}], name, content}
 * /api/juez     → veredictos fase viva (counts + items)
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Cifra,
  BarraVeredictos,
  SinDatos,
  BannerError,
  TablaDatos,
} from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function ReportesTab() {
  const reporteF = useCallback(() => api.reportes(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);

  const reporte = usePoll(reporteF, 60000);
  const juez = usePoll(juezF, 30000);

  if (reporte.error) return <BannerError mensaje={reporte.error} />;
  if (reporte.loading && !reporte.data) return <SinDatos titulo="Cargando reportes…" />;

  const r: any = reporte.data ?? {};
  const files: any[] = r.files ?? [];

  const counts: any[] = juez.data?.counts ?? [];
  const nDe = (res: string) =>
    counts
      .filter((c) => c.fase === "viva" && c.resultado === res)
      .reduce((a, c) => a + Number(c.n ?? 0), 0);
  const aciertos = nDe("ACIERTO");
  const fallos = nDe("FALLO");
  const falsosPositivos = nDe("FALSO_POSITIVO");
  const jItems: any[] = juez.data?.items ?? [];

  return (
    <div className="space-y-5">
      <Panel
        titulo="Resumen de veredictos del Juez"
        meta={`${(aciertos + fallos + falsosPositivos).toLocaleString("es-MX")} veredictos vivos evaluados`}
        nota="La omisión pesa 10× más que la falsa alarma (pérdida asimétrica)."
      >
        <BarraVeredictos aciertos={aciertos} falsosPositivos={falsosPositivos} fallos={fallos} />
      </Panel>

      <Panel titulo="Últimos veredictos del Juez" meta={`mostrando ${Math.min(jItems.length, 12)} de ${jItems.length}`}>
        <TablaDatos
          filas={jItems.slice(0, 12)}
          densa
          vacío="Sin veredictos del Juez"
          columnas={[
            { clave: "bot_name", etiqueta: "Bot" },
            { clave: "prediccion", etiqueta: "Predicción" },
            { clave: "confianza", etiqueta: "Confianza", num: true, render: (row) => <Cifra valor={row.confianza} digits={2} /> },
            {
              clave: "resultado",
              etiqueta: "Resultado",
              render: (row) => (
                <span
                  className="mono texto-micro fuente-negrita"
                  style={{
                    color:
                      row.resultado === "ACIERTO"
                        ? "var(--color-calma)"
                        : row.resultado === "FALSO_POSITIVO"
                          ? "var(--color-aviso)"
                          : "var(--color-critico)",
                  }}
                >
                  {String(row.resultado ?? "—")}
                </span>
              ),
            },
            { clave: "resuelto_at", etiqueta: "Resuelto", render: (row) => String(row.resuelto_at ?? "—").slice(0, 16) },
          ]}
        />
      </Panel>

      <Panel
        titulo="Reportes disponibles"
        meta={`${files.length} archivos${r.dir ? ` · ${r.dir}` : ""}`}
        nota="El último reporte publicado es REPORTE.md; los cortes históricos viven en estado/historial/AAAA/MM/."
      >
        {files.length > 0 ? (
          <TablaDatos
            filas={files}
            densa
            vacío="Sin reportes"
            columnas={[
              { clave: "name", etiqueta: "Archivo" },
              {
                clave: "bytes",
                etiqueta: "Tamaño",
                num: true,
                render: (f) => (f.bytes != null ? `${(Number(f.bytes) / 1024).toFixed(1)} KB` : "—"),
              },
              {
                clave: "mtime",
                etiqueta: "Modificado",
                num: true,
                render: (f) => (f.mtime != null ? fmtTs(Number(f.mtime)) : "—"),
              },
            ]}
          />
        ) : (
          <SinDatos
            titulo="Sin reportes disponibles"
            detalle="Ejecute una corrida del reporte para generar archivos."
          />
        )}
      </Panel>
    </div>
  );
}
