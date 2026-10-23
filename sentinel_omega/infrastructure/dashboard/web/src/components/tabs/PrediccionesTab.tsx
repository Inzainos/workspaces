/**
 * PREDICCIONES — predicciones del motor contra la realidad.
 *
 * La superficie real de "predicciones" en este sistema es el Juez:
 * cada bot emite una predicción con confianza, el Juez la compara con la
 * verdad (catálogo USGS / calma) y produce un veredicto. Datos de /api/juez.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  BarraVeredictos,
  SinDatos,
  BannerError,
  TablaDatos,
} from "@/components/ui/data";

export function PrediccionesTab() {
  const juezF = useCallback(() => api.juez(80, "viva"), []);
  const juez = usePoll(juezF, 30000);

  if (juez.error) return <BannerError mensaje={juez.error} />;
  if (juez.loading && !juez.data) return <SinDatos titulo="Cargando predicciones…" />;

  const counts: any[] = juez.data?.counts ?? [];
  const nDe = (res: string) =>
    counts
      .filter((c) => c.fase === "viva" && c.resultado === res)
      .reduce((a, c) => a + Number(c.n ?? 0), 0);
  const aciertos = nDe("ACIERTO");
  const fallos = nDe("FALLO");
  const falsosPositivos = nDe("FALSO_POSITIVO");
  const total = aciertos + fallos + falsosPositivos;

  const items: any[] = juez.data?.items ?? [];
  const conAlerta = items.filter((r) => String(r.prediccion ?? "").toLowerCase() !== "neutral");

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica
          etiqueta="Veredictos vivos"
          valor={total.toLocaleString("es-MX")}
          contexto="fase viva completa, no solo la última tanda"
        />
        <Metrica
          etiqueta="Aciertos"
          valor={aciertos.toLocaleString("es-MX")}
          contexto="incluye los silencios en calma"
        />
        <Metrica
          etiqueta="Falsas alarmas"
          valor={falsosPositivos.toLocaleString("es-MX")}
          contexto={`omisiones: ${fallos.toLocaleString("es-MX")} — pesan 10×`}
        />
      </div>

      <Panel titulo="Veredictos del Juez — fase viva" nota="Predicción vs realidad. La calma es el ~97% del tiempo: un sistema que nunca alarma también «acierta» — la vara es la ganancia sobre ese bot mudo, no el porcentaje crudo.">
        <BarraVeredictos aciertos={aciertos} falsosPositivos={falsosPositivos} fallos={fallos} />
      </Panel>

      <Panel
        titulo="Últimas predicciones emitidas"
        meta={`${items.length} recientes · ${conAlerta.length} con aviso (no neutral)`}
      >
        <TablaDatos
          filas={items}
          densa
          vacío="Sin predicciones recientes"
          columnas={[
            { clave: "bot_name", etiqueta: "Bot" },
            {
              clave: "prediccion",
              etiqueta: "Predicción",
              render: (r) => (
                <span
                  className="mono texto-micro fuente-negrita"
                  style={{
                    color: String(r.prediccion ?? "").toLowerCase() !== "neutral" ? "var(--color-aviso)" : "var(--color-fuente-desvanecido)",
                  }}
                >
                  {String(r.prediccion ?? "—")}
                </span>
              ),
            },
            { clave: "confianza", etiqueta: "Confianza", num: true, render: (r) => <Cifra valor={r.confianza} digits={2} /> },
            {
              clave: "verdad",
              etiqueta: "Realidad",
              render: (r) => (
                <span className="texto-micro texto-desvanecido" title={String(r.verdad ?? "—")}>
                  {String(r.verdad ?? "—").slice(0, 60)}
                </span>
              ),
            },
            {
              clave: "resultado",
              etiqueta: "Veredicto",
              render: (r) => (
                <span
                  className="mono texto-micro fuente-negrita"
                  style={{
                    color:
                      r.resultado === "ACIERTO"
                        ? "var(--color-calma)"
                        : r.resultado === "FALSO_POSITIVO"
                          ? "var(--color-aviso)"
                          : "var(--color-critico)",
                  }}
                >
                  {String(r.resultado ?? "—")}
                </span>
              ),
            },
            { clave: "resuelto_at", etiqueta: "Resuelto", render: (r) => String(r.resuelto_at ?? "—").slice(0, 16) },
          ]}
        />
      </Panel>
    </div>
  );
}
