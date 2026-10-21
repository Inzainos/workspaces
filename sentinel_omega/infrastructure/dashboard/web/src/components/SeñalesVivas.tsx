import { useEffect, useState } from "react";
import { Panel, SinDatos, Cifra } from "@/components/ui/data";

/**
 * SEÑALES VIVAS CON COUNTDOWN — la superficie que faltaba (2026-10-20).
 *
 * Pedido del operador: cada señal con su sitio (nombre → nodo → coords),
 * evento y el LAG RESTÁNDOSE mientras la señal persiste. El ancla la
 * calcula el backend (primera detección continua, core/nodos.py); el
 * cliente solo hace TICK — el número baja solo, cada segundo, sin
 * re-poll (Krug: feedback continuo, Nielsen #1).
 *
 * Colores por URGENCIA (sistema de diseño: saturado = riesgo):
 *   >72 h calma · 24–72 h atención · <24 h aviso · vencida neutra.
 */

export type SeñalViva = {
  sitio: string;
  id_nodo: number;
  evento: string;
  similitud: number | null;
  recurrencia: number | null;
  lag_inicial_h: number | null;
  lag_restante_h: number | null;
  ancla_ts: number | null;
};

const colorLag = (rest: number) =>
  rest <= 0
    ? "var(--color-faint)"
    : rest < 24
      ? "var(--color-aviso)"
      : rest < 72
        ? "var(--color-atencion)"
        : "var(--color-calma)";

function formatoLag(rest: number): { num: string; sub: string } {
  if (rest <= 0) {
    return { num: `vencida hace ${Math.round(-rest)} h`, sub: "la ventana pasó sin evento" };
  }
  const d = rest / 24;
  return {
    num: `~${Math.round(rest)} h`,
    sub: d >= 1 ? `(${d.toFixed(1)} d)` : "menos de un día",
  };
}

export function SeñalesVivas({
  señales,
  tsSnapshot,
  edadS,
}: {
  señales: SeñalViva[];
  tsSnapshot: number;
  edadS: number | null;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  if (!señales.length) {
    return (
      <Panel
        titulo="Señales vivas · lag restándose"
        meta="sin señales"
        nota="La memoria no empareja el presente contra firmas de víspera ahora mismo. Sin emparejamiento no hay countdown — no se inventa ventana."
      >
        <SinDatos titulo="Ninguna señal de firma activa" />
      </Panel>
    );
  }

  return (
    <Panel
      titulo="Señales vivas · lag restándose"
      meta={`${señales.length} señal(es) · frescura ${edadS != null ? `${edadS} s` : "—"}`}
      nota="Cada tarjeta: el sitio primero (nombre → nodo → coordenadas), el evento que su firma suele preceder, y el LAG restante — el tiempo que la historia dice que falta, restándose desde la PRIMERA detección continua, no desde el último ciclo. «Sin lag medido» = la firma nunca demostró anticipar (regla de dato del tablero)."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {señales.map((s, i) => {
          const rest =
            s.lag_restante_h != null
              ? s.lag_restante_h - (now / 1000 - tsSnapshot) / 3600
              : null;
          return (
            <div
              key={`${s.id_nodo}-${s.evento}-${i}`}
              className="relative overflow-hidden rounded-lg border bg-surface p-3.5 pl-4"
              style={{
                borderColor:
                  rest != null && rest > 0 && rest < 24
                    ? "color-mix(in oklch, var(--color-aviso) 40%, var(--color-border))"
                    : undefined,
              }}
            >
              <span
                className="absolute inset-y-0 left-0 w-[3px]"
                style={{
                  background: rest != null ? colorLag(rest) : "var(--color-border-strong)",
                }}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <div className="truncate text-body font-semibold text-foreground" title={s.sitio}>
                  {s.sitio}
                </div>
                <div className="mt-0.5 flex items-baseline gap-2">
                  <span
                    className="mono text-micro font-bold uppercase tracking-wider"
                    style={{ color: rest != null && rest < 24 && rest > 0 ? "var(--color-aviso)" : "var(--color-muted)" }}
                  >
                    {s.evento}
                  </span>
                  <span className="text-micro text-faint tnum">
                    parecido <Cifra valor={s.similitud} digits={2} /> · vista{" "}
                    {s.recurrencia != null ? `${s.recurrencia}×` : "—"}
                  </span>
                </div>
                <div className="mt-2.5 flex items-baseline gap-2">
                  {rest != null ? (
                    <>
                      <span
                        className="mono text-[length:var(--text-metric)] font-bold tnum"
                        style={{ color: colorLag(rest) }}
                      >
                        {formatoLag(rest).num}
                      </span>
                      <span className="text-micro text-faint">
                        {formatoLag(rest).sub}
                      </span>
                    </>
                  ) : (
                    <span className="text-meta" style={{ color: "var(--color-faint)" }}>
                      sin lag medido — el patrón no demostró anticipar
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
