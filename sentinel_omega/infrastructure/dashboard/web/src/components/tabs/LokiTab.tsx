/**
 * LOKI — resonancia de rotación solar (Carrington 26-29 días).
 *
 * Realidad de datos: la API expone el Kp ACTUAL (/api/overview.fantasma.kp)
 * y las estadísticas del bot loki (/api/bots, filtrado client-side porque el
 * parámetro bot= no filtra). NO expone el estado de la ventana de resonancia
 * 26-29d — eso se muestra como no disponible, no se inventa.
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
  nivelDe,
} from "@/components/ui/data";

export function LokiTab() {
  const ovF = useCallback(() => api.overview(), []);
  const botsF = useCallback(() => api.bots(), []);
  const juezF = useCallback(() => api.juez(50, "viva"), []);

  const ov = usePoll(ovF, 30000);
  const bots = usePoll(botsF, 60000);
  const juez = usePoll(juezF, 30000);

  if (ov.error) return <BannerError mensaje={ov.error} />;
  if (ov.loading && !ov.data) return <SinDatos titulo="Cargando datos de rotación solar…" />;

  const f: any = ov.data?.fantasma ?? {};
  const kp = f.kp != null ? Number(f.kp) : null;
  const bz = f.bz_nT != null ? Number(f.bz_nT) : null;

  const loki: any = ((bots.data?.items ?? []) as any[]).find((b) => b.bot_name === "loki") ?? null;

  const jItems: any[] = juez.data?.items ?? [];
  const lokiVeredictos = jItems.filter((r) => r.bot_name === "loki");
  const lokiAciertos = lokiVeredictos.filter((r) => r.resultado === "ACIERTO").length;
  const lokiFallos = lokiVeredictos.filter((r) => r.resultado === "FALLO").length;
  const lokiFp = lokiVeredictos.filter((r) => r.resultado === "FALSO_POSITIVO").length;

  const kpNivel = kp == null ? nivelDe(null) : kp >= 5 ? nivelDe("HIGH") : kp >= 4 ? nivelDe("MODERATE") : nivelDe("LOW");

  return (
    <div className="space-y-5">
      <Panel
        titulo="Resonancia de rotación solar — Loki"
        meta={kp != null ? `Kp actual ${kp.toFixed(2)}` : "sin Kp"}
        acento={kpNivel}
        nota="Mecanismo (medido sobre 32 años): una tormenta Kp≥5 antecede una tormenta recurrente 26-29 días después — un ciclo de Carrington. Ganancia 3.4×. Loki solo sube la confianza cuando la ventana de resonancia confirma; jamás la baja."
      >
        <div className="grid gap-4 md:grid-cols-4">
          <Metrica
            etiqueta="Kp actual"
            valor={<Cifra valor={kp} digits={2} />}
            contexto={kp != null && kp >= 5 ? "tormenta en curso" : kp != null && kp >= 4 ? "inquietud" : "calma"}
          />
          <Metrica etiqueta="Bz (nT)" valor={<Cifra valor={bz} digits={2} />} />
          <Metrica
            etiqueta="Voto de Loki"
            valor={loki?.peso_voto != null ? Number(loki.peso_voto).toFixed(3) : "—"}
            contexto="peso aplicado por el Padre"
          />
          <Metrica
            etiqueta="Asertividad viva"
            valor={
              loki?.asertividad_viva_individual != null
                ? `${(Number(loki.asertividad_viva_individual) * 100).toFixed(1)}%`
                : "—"
            }
            contexto={loki?.n != null ? `n=${Number(loki.n).toLocaleString("es-MX")} veredictos` : undefined}
          />
        </div>
      </Panel>

      <Panel
        titulo="Veredictos recientes de Loki (fase viva)"
        meta={`${lokiVeredictos.length} en la última tanda`}
      >
        <TablaDatos
          filas={lokiVeredictos.slice(0, 12)}
          densa
          vacío="Sin veredictos recientes de Loki"
          columnas={[
            { clave: "prediccion", etiqueta: "Predicción" },
            { clave: "confianza", etiqueta: "Confianza", num: true, render: (r) => <Cifra valor={r.confianza} digits={2} /> },
            {
              clave: "resultado",
              etiqueta: "Resultado",
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
        <p className="mt-3 texto-micro texto-desvanecido">
          Tanda reciente: {lokiAciertos} aciertos · {lokiFp} falsas alarmas · {lokiFallos} omisiones.
        </p>
      </Panel>

      <Panel titulo="Firmas de Loki" meta={loki?.updated_at ? `actualizado ${String(loki.updated_at).slice(0, 16)}` : "—"}>
        <div className="grid gap-4 md:grid-cols-2">
          <Metrica
            etiqueta="Consolidadas"
            valor={loki?.firmas_consolidadas != null ? Number(loki.firmas_consolidadas).toLocaleString("es-MX") : "—"}
          />
          <Metrica
            etiqueta="Exigibles"
            valor={
              loki?.firmas_exigibles != null
                ? `${Number(loki.firmas_exigibles).toLocaleString("es-MX")} (${loki.pct_exigibles != null ? (Number(loki.pct_exigibles) * 100).toFixed(1) : "—"}%)`
                : "—"
            }
            contexto="exigible = discrimina eventos frente a calma (lift ≥ 2.0)"
          />
        </div>
      </Panel>
    </div>
  );
}
