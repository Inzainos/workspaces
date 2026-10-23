/**
 * PADRE + JUEZ — el árbitro y el auditor.
 *
 * Padre: consenso jerárquico entre familias (pesos de /api/bots, incluida la
 * fila padre). Juez: compara predicción con realidad (/api/juez fase viva).
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

export function PadreJuezTab() {
  const padreF = useCallback(() => api.bots(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);

  const padre = usePoll(padreF, 30000);
  const juez = usePoll(juezF, 30000);

  if (padre.error) return <BannerError mensaje={padre.error} />;
  if (padre.loading && !padre.data) return <SinDatos titulo="Cargando bots del Padre…" />;

  const B: any = padre.data ?? {};
  const items: any[] = B.items ?? [];
  const filaPadre: any = B.padre ?? items.find((b) => b.bot_name === "padre") ?? null;
  const sinPadre = items.filter((b) => b.bot_name !== "padre");

  const counts: any[] = juez.data?.counts ?? [];
  const nDe = (res: string) =>
    counts
      .filter((c) => c.fase === "viva" && c.resultado === res)
      .reduce((a, c) => a + Number(c.n ?? 0), 0);
  const aciertosJ = nDe("ACIERTO");
  const fallosJ = nDe("FALLO");
  const fpJ = nDe("FALSO_POSITIVO");

  return (
    <div className="space-y-5">
      <Panel
        titulo="Padre — consenso jerárquico"
        meta={`${sinPadre.length} bots votantes`}
        nota={B.pesos_nota ? String(B.pesos_nota) : undefined}
      >
        <div className="grid gap-4 md:grid-cols-4">
          <Metrica
            etiqueta="Voto del Padre"
            valor={filaPadre?.peso_voto != null ? Number(filaPadre.peso_voto).toFixed(3) : "—"}
            contexto="peso que aplica el Padre al consenso"
          />
          <Metrica
            etiqueta="Asertividad viva (Padre)"
            valor={
              filaPadre?.asertividad_viva_individual != null
                ? `${(Number(filaPadre.asertividad_viva_individual) * 100).toFixed(1)}%`
                : "—"
            }
            contexto={filaPadre?.n != null ? `n=${Number(filaPadre.n).toLocaleString("es-MX")}` : undefined}
          />
          <Metrica
            etiqueta="Firmas del Padre"
            valor={
              filaPadre?.firmas_consolidadas != null
                ? `${Number(filaPadre.firmas_exigibles ?? 0).toLocaleString("es-MX")} exigibles / ${Number(filaPadre.firmas_consolidadas).toLocaleString("es-MX")}`
                : "—"
            }
          />
          <Metrica
            etiqueta="Umbral rentable"
            valor={B.umbral_alarma_rentable != null ? String(B.umbral_alarma_rentable) : "—"}
            contexto={B.veredicto_ganancia != null ? `ganancia ${B.veredicto_ganancia}` : undefined}
          />
        </div>
      </Panel>

      <Panel
        titulo="Juez — real vs predicción (fase viva)"
        nota="El Juez nunca predice: audita. La omisión pesa 10× más que la falsa alarma."
      >
        <BarraVeredictos aciertos={aciertosJ} falsosPositivos={fpJ} fallos={fallosJ} />
      </Panel>

      <Panel titulo="Pesos de credibilidad por bot" meta={`total ${items.length}`}>
        <TablaDatos
          filas={items}
          densa
          vacío="Sin bots"
          columnas={[
            { clave: "bot_name", etiqueta: "Bot" },
            { clave: "peso", etiqueta: "Marcador", num: true, render: (r) => <Cifra valor={r.peso} digits={3} /> },
            { clave: "peso_voto", etiqueta: "Voto", num: true, render: (r) => <Cifra valor={r.peso_voto} digits={3} /> },
            {
              clave: "asertividad_viva_individual",
              etiqueta: "Asert. viva",
              num: true,
              render: (r) => (
                <Cifra
                  valor={
                    r.asertividad_viva_individual != null
                      ? Number(r.asertividad_viva_individual) * 100
                      : null
                  }
                  digits={1}
                  unidad="%"
                />
              ),
            },
            { clave: "aciertos", etiqueta: "Aciertos", num: true, render: (r) => Number(r.aciertos ?? 0).toLocaleString("es-MX") },
            { clave: "fallos", etiqueta: "Fallos", num: true, render: (r) => Number(r.fallos ?? 0).toLocaleString("es-MX") },
            { clave: "updated_at", etiqueta: "Actualizado", render: (r) => String(r.updated_at ?? "—").slice(0, 16) },
          ]}
        />
      </Panel>
    </div>
  );
}
