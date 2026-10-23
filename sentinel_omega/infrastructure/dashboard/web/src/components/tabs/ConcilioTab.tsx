/**
 * CONCILIO — su salud como pieza del ecosistema, desde datos REALES.
 *
 * El estado interno del Concilio (modelos, cola de alertas, /task) vive en
 * SU propia web (:8002, consensus-web) — este tab no lo duplica ni lo
 * inventa. Aquí se ve lo que la API de Sentinel puede ver de verdad:
 * la salud del sistema (/api/health) y el estado de las fuentes
 * (/api/health/apis), incluyendo las que el Concilio sirve.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, SinDatos, BannerError } from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

const ESTADO_COLOR: Record<string, string> = {
  LIVE: "var(--color-calma)",
  LOCF_ACTIVE: "var(--color-atencion)",
  CONGELADO: "var(--color-aviso)",
  STALE: "var(--color-critico)",
};

export function ConcilioTab() {
  const healthF = useCallback(() => api.health(), []);
  const apisF = useCallback(() => api.healthApis(), []);
  const health = usePoll(healthF, 30000);
  const apis = usePoll(apisF, 30000);

  if (health.error && apis.error) return <BannerError mensaje={health.error || apis.error} />;
  if (health.loading && !health.data) return <SinDatos titulo="Leyendo salud del ecosistema…" />;

  const h = (health.data || {}) as Record<string, any>;
  const fuentes = Object.entries((apis.data || {}) as Record<string, any>);

  return (
    <div className="space-y-5">
      <Panel
        titulo="Salud del sistema"
        meta={h.status ? String(h.status) : "—"}
        nota="El sistema del ecosistema (launcher + DB + ciclo) visto desde /api/health. El detalle operativo del Concilio —modelos cargados, cola de alertas, /task— vive en su propia interfaz (:8002) y NO se duplica aquí: eso sería inventar estado que esta API no mide."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <Metrica
            etiqueta="Estado"
            valor={h.status ? String(h.status) : "—"}
            contexto={h.lectura ? String(h.lectura) : "lectura del health"}
          />
          <Metrica
            etiqueta="Último ciclo"
            valor={h.last_cycle_ts ? fmtTs(h.last_cycle_ts) : "—"}
            contexto="launcher vivo"
            jerarquia="compacta"
          />
          <Metrica
            etiqueta="Antigüedad"
            valor={h.antiguedad_h != null ? `${Number(h.antiguedad_h).toFixed(1)} h` : "—"}
            contexto="del último ciclo real"
            jerarquia="compacta"
          />
        </div>
      </Panel>

      <Panel
        titulo="Estado de las fuentes"
        meta={`${fuentes.length} fuentes`}
        nota="LIVE = sirviendo dato fresco · LOCF = reenviado desde caché real · CONGELADO = se refresca pero repite el mismo valor (frescura ≠ validez) · DESCONOCIDO = ilegible, nunca se omite."
      >
        {fuentes.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {fuentes.map(([nombre, f]) => {
              const info = f as Record<string, any>;
              const estado = String(info.status || "DESCONOCIDO");
              return (
                <div key={nombre} className="rounded-lg border border-border bg-surface-sunken/40 p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="mono text-body font-semibold text-foreground">{nombre}</span>
                    <span
                      className="mono text-micro font-semibold uppercase"
                      style={{ color: ESTADO_COLOR[estado] || "var(--color-faint)" }}
                    >
                      {estado}
                    </span>
                  </div>
                  <div className="mt-1.5 text-meta text-muted">
                    edad: {info.age_h != null ? `${Number(info.age_h).toFixed(1)} h` : "—"}
                  </div>
                  {info.nota ? (
                    <div className="mt-1 text-micro leading-snug text-faint">{String(info.nota).slice(0, 120)}</div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <SinDatos titulo="Sin estado de fuentes" />
        )}
      </Panel>

      <div className="rounded-lg border border-dashed border-border bg-surface-sunken/40 p-4">
        <p className="text-sm text-muted">
          <strong className="text-foreground">El Concilio completo vive en su propio proyecto:</strong>{" "}
          <span className="mono">consensus-expert-agent</span> — web local{" "}
          <span className="mono">:8002/mini</span>, Mini App por Telegram, modelos Ollama en{" "}
          <span className="mono">:11434</span>. Este tab es su salud desde Sentinel, no un espejo.
        </p>
      </div>
    </div>
  );
}
