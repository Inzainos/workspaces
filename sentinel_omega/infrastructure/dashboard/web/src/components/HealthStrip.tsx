import { useCallback } from "react";
import { api, type Health, type ApiHealth } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { ChipFuente } from "@/components/ui/data";

/**
 * Barra de salud del encabezado.
 *
 * Dos cosas que este componente NO debe volver a hacer:
 *  - pintar OK en verde porque el archivo de la DB existe (el sistema estuvo
 *    90 h parado con el semáforo en verde);
 *  - mostrar solo las fuentes que el backend consiguió parsear. Hasta el
 *    2026-09-28 el endpoint se tragaba cinco de seis por un `except: pass`, y
 *    aquí se veían dos chips como si ese fuera el total.
 */
export function HealthStrip() {
  const fetcher = useCallback(() => api.health(), []);
  const { data, loading, error } = usePoll<Health>(fetcher, 20000);
  const fuentesFetcher = useCallback(() => api.healthApis(), []);
  const { data: fuentes } = usePoll<ApiHealth>(fuentesFetcher, 60000);

  if (loading && !data) {
    return <div className="text-meta text-muted">Cargando salud…</div>;
  }
  if (error) {
    return (
      <div
        className="rounded border px-2.5 py-1.5 text-meta"
        style={{
          borderColor: "color-mix(in oklch, var(--color-critico) 45%, transparent)",
          background: "var(--color-critico-dim)",
          color: "var(--color-critico)",
        }}
      >
        Health: {error}
      </div>
    );
  }

  const estado = String(data?.status ?? "");
  const ok = estado === "ok" && data?.db_exists;
  const parado = estado === "stale";
  const color = ok ? "var(--color-calma)" : parado ? "var(--color-aviso)" : "var(--color-critico)";
  const etiqueta = ok ? "EN VIVO" : parado ? "SIN CICLOS" : "DEGRADADO";
  const antig = data?.antiguedad_h;

  const entradas = Object.entries(fuentes || {});
  const congeladas = entradas.filter(([, f]) => String(f?.status).toUpperCase() === "CONGELADO");

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1">
        <span className="flex items-center gap-1.5 text-meta font-semibold" style={{ color }}>
          <span
            className={`h-1.5 w-1.5 rounded-full ${ok ? "pulso-vivo" : ""}`}
            style={{ background: color }}
          />
          {etiqueta}
        </span>
        <span className="mono text-meta text-muted">
          ciclo <span className="text-body">{data?.ciclos?.toLocaleString("es-MX") ?? "—"}</span>
        </span>
        {antig != null && (
          <span className="mono text-meta" style={{ color: parado ? "var(--color-aviso)" : "var(--color-faint)" }}>
            hace {antig < 1 ? `${Math.round(antig * 60)} min` : `${antig} h`}
          </span>
        )}
      </div>

      {entradas.length > 0 && (
        <div className="flex flex-wrap items-center justify-end gap-1">
          {entradas.map(([nombre, f]) => (
            <ChipFuente
              key={nombre}
              nombre={nombre}
              estado={String(f?.status || "")}
              edadH={f?.age_h ?? null}
              nota={(f as { nota?: string })?.nota}
            />
          ))}
        </div>
      )}

      {congeladas.length > 0 && (
        <div className="max-w-md text-right text-micro leading-snug" style={{ color: "var(--color-aviso)" }}>
          {congeladas.length === 1
            ? `${congeladas[0][0]} se refresca pero repite el mismo valor: la fuente no está midiendo.`
            : `${congeladas.length} fuentes repiten valor: se refrescan pero no miden.`}
        </div>
      )}
    </div>
  );
}
