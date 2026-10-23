/**
 * VIGILANCIA — salud de las fuentes de datos del sistema.
 *
 * /api/health/apis expone el estado real por fuente (LIVE / LOCF_ACTIVE /
 * STALE, edad en horas). El watchdog de SEGURIDAD es otro proyecto (/watchdog,
 * bot propio @IngZainos_bot) y no vive en esta API: aquí se vigila que las
 * fuentes que alimentan a Sentinel estén vivas.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  SinDatos,
  BannerError,
  TablaDatos,
} from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

const COLOR_ESTADO: Record<string, string> = {
  LIVE: "var(--color-calma)",
  LOCF_ACTIVE: "var(--color-atencion)",
  STALE: "var(--color-aviso)",
  DEAD: "var(--color-critico)",
};

export function WatchdogTab() {
  const saludF = useCallback(() => api.healthApis(), []);
  const salud = usePoll(saludF, 30000);

  if (salud.error) return <BannerError mensaje={salud.error} />;
  if (salud.loading && !salud.data) return <SinDatos titulo="Cargando salud de las fuentes…" />;

  const d: any = salud.data ?? {};
  const filas = Object.entries(d).map(([fuente, v]: [string, any]) => ({
    fuente,
    estado: String(v?.status ?? "—"),
    edad_h: v?.age_h != null ? Number(v.age_h) : null,
    muestras: v?.muestras != null ? Number(v.muestras) : null,
    ultimo_ts: v?.last_data_ts != null ? Number(v.last_data_ts) : null,
  }));

  const vivas = filas.filter((f) => f.estado === "LIVE").length;
  const locf = filas.filter((f) => f.estado === "LOCF_ACTIVE").length;
  const stales = filas.filter((f) => f.estado === "STALE" || f.estado === "DEAD").length;

  return (
    <div className="space-y-5">
      <Panel
        titulo="Salud de las fuentes de datos"
        meta={`${filas.length} fuentes`}
        nota="LIVE = dato fresco de la API. LOCF_ACTIVE = el ciclo corre con el último valor real conocido (LOCF). STALE = la fuente lleva horas sin responder. Un dato ausente se ve como ausente, nunca como cero."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <Metrica etiqueta="Fuentes vivas" valor={`${vivas}`} contexto="dato fresco de la API" />
          <Metrica etiqueta="Con LOCF activo" valor={`${locf}`} contexto="último valor real conocido" />
          <Metrica
            etiqueta="Rezagadas / muertas"
            valor={`${stales}`}
            contexto={stales > 0 ? "revisar conectividad de salida" : "todas responden"}
          />
        </div>
      </Panel>

      <Panel titulo="Detalle por fuente" meta={`${filas.length} fuentes vigiladas`}>
        <TablaDatos
          filas={filas}
          densa
          vacío="Sin datos de salud"
          columnas={[
            { clave: "fuente", etiqueta: "Fuente" },
            {
              clave: "estado",
              etiqueta: "Estado",
              render: (r) => (
                <span
                  className="mono texto-micro fuente-negrita"
                  style={{ color: COLOR_ESTADO[r.estado] ?? "var(--color-fuente-desvanecido)" }}
                >
                  {r.estado}
                </span>
              ),
            },
            { clave: "edad_h", etiqueta: "Edad (h)", num: true, render: (r) => <Cifra valor={r.edad_h} digits={1} /> },
            { clave: "muestras", etiqueta: "Muestras", num: true, render: (r) => (r.muestras != null ? String(r.muestras) : "—") },
            {
              clave: "ultimo_ts",
              etiqueta: "Último dato",
              num: true,
              render: (r) => (r.ultimo_ts != null ? fmtTs(r.ultimo_ts) : "—"),
            },
          ]}
        />
      </Panel>

      <Panel
        titulo="El watchdog de seguridad es otro proyecto"
        nota="La vigilancia de seguridad de la máquina (escaneos, cuarentena cifrada, red acotada) vive en /watchdog, con su propia base, su bot @IngZainos_bot y sus alertas. Este tablero solo vigila las fuentes de datos de Sentinel."
      >
        <p className="texto-meta texto-desvanecido">
          Para el estado del watchdog de seguridad: <code className="mono">sqlite3 /watchdog/data/watchdog.db "SELECT ts, finding_type, action FROM incidents ORDER BY id DESC LIMIT 5;"</code>
        </p>
      </Panel>
    </div>
  );
}
