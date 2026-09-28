import { useCallback } from "react";
import { api, type Overview } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Cifra, Panel } from "@/components/ui/data";

/**
 * PRESENTACIÓN — superficie DECIDE/LEARN.
 *
 * Es la única pestaña donde un hero es la composición correcta: aquí alguien
 * llega sin contexto y hay que explicarle qué es esto antes de enseñarle un
 * número.
 *
 * Tres cosas que se corrigieron respecto de la versión anterior:
 *
 *  - Se quitó el CENTER-STACK. Todo iba centrado —titular, párrafo, chips,
 *    y luego cuatro cifras gigantes centradas— que es el patrón por defecto
 *    de plantilla, no una decisión. Ahora el hero está alineado a la
 *    izquierda sobre una rejilla asimétrica: el ojo entra por una esquina y
 *    baja, en vez de rebotar por el eje central.
 *  - Se quitaron los MONUMENT STATS. Cuatro números de 3xl en fila, todos del
 *    mismo tamaño, no establecen jerarquía: establecen ruido. Ahora la cifra
 *    que manda es la ganancia (la que de verdad dice si el sistema sirve) y
 *    el resto la acompaña en escala menor.
 *  - El degradado sobre el texto del titular se fue. Un gradiente de marca en
 *    tipografía es el tell #1 de diseño generado; el énfasis ahora es
 *    tipográfico y de color sólido.
 *
 * Regla de honestidad: si la API no da un número, va un guion. Nunca un
 * literal escrito a mano (este archivo ya tuvo un "96%" hardcodeado que
 * sobrevivió meses porque leía una clave que la API no devolvía).
 */
export function PresentacionTab() {
  const ov = usePoll<Overview>(useCallback(() => api.overview(), []), 60000);
  const cyc = usePoll(useCallback(() => api.ciclos(1), []), 60000);
  const ci = usePoll(useCallback(() => api.cimatica(1), []), 60000);
  const bots = usePoll(useCallback(() => api.bots(), []), 60000);

  const b = bots.data as Record<string, unknown> | undefined;
  const ganancia = b?.ganancia_real != null ? Number(b.ganancia_real) : null;
  const asert = b?.asertividad_viva_global != null ? Number(b.asertividad_viva_global) : null;
  const mudo = b?.asertividad_bot_mudo != null ? Number(b.asertividad_bot_mudo) : null;
  const veredicto = b?.veredicto_ganancia ? String(b.veredicto_ganancia) : null;
  const aporta = ganancia != null && ganancia > 1;

  const cicloId =
    (cyc.data?.[0]?.id as number | undefined) ?? (ov.data?.ciclo?.id as number | undefined);
  const patrones = ci.data?.total != null ? Number(ci.data.total) : null;

  return (
    <div className="space-y-5">
      {/* ---------- Hero: asimétrico, alineado a la izquierda ---------- */}
      <section className="overflow-hidden rounded-lg border border-border bg-surface">
        <div className="grid gap-px bg-border lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
          <div className="bg-surface px-7 py-10 lg:px-9 lg:py-12">
            <span className="etiqueta">Fractal Core Research · sucesor de TITAN V32/V46/V53</span>
            <h1
              className="mt-4 max-w-[19ch] text-[2.6rem] font-bold leading-[1.08] tracking-tight text-foreground lg:text-[3.1rem]"
              style={{ textWrap: "balance" }}
            >
              El planeta avisa antes de un evento.
            </h1>
            <p
              className="mt-5 max-w-[58ch] text-[length:var(--text-read)] leading-relaxed text-body"
              style={{ textWrap: "pretty" }}
            >
              Sentinel Omega vigila las señales físicas de la Tierra —campo magnético solar,
              resonancia Schumann, sismos, desgasificación volcánica, hasta el humor de los
              mercados— y reconoce <b className="text-foreground">precursores</b>: las condiciones
              que en 32 años de registro aparecieron en los días previos a eventos naturales
              fuertes.
            </p>
            <p className="mt-3 max-w-[58ch] text-meta leading-relaxed text-muted">
              No anuncia epicentros ni fechas. Estima cuándo un estado se parece a los que
              precedieron a algo, y sube la vigilancia.
            </p>
          </div>

          {/* Columna derecha: datos de escala, no adornos */}
          <div className="flex flex-col justify-center gap-5 bg-surface px-7 py-10 lg:px-8">
            {[
              ["Memoria", "32 años", "1994 → hoy, resolución horaria"],
              ["Topología", "125 nodos", "75 reales + 50 Ghost (UVG)"],
              ["Consejo", "8 + 2", "bots votantes, Padre y Juez"],
            ].map(([k, v, sub]) => (
              <div key={k} className="border-l-2 border-border pl-3.5">
                <div className="etiqueta">{k}</div>
                <div className="mono mt-0.5 text-[length:var(--text-read)] font-semibold text-foreground">
                  {v}
                </div>
                <div className="mt-0.5 text-meta text-muted">{sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Qué sí / qué no ---------- */}
      <div className="grid gap-5 md:grid-cols-2">
        <Panel titulo="Qué sí hace">
          <ul className="space-y-2.5 text-body leading-relaxed text-body">
            <li>
              Reconoce cuando el estado físico del presente <b className="text-foreground">se parece</b> a
              los días previos a eventos pasados.
            </li>
            <li>Estima una <b className="text-foreground">ventana temporal</b> — cuándo podría ocurrir.</li>
            <li>
              Aprende de cada acierto y cada error: el Juez audita contra el catálogo real del USGS y
              castiga a los bots que fallan.
            </li>
          </ul>
        </Panel>
        <Panel titulo="Qué no hace">
          <ul className="space-y-2.5 text-body leading-relaxed text-body">
            <li>No es un oráculo: no anuncia epicentro, magnitud ni hora con certeza.</li>
            <li>
              No inventa datos. Si una fuente cae, el valor es <span className="mono">NULL</span> — nunca
              un número plausible de relleno.
            </li>
            <li>No es consejo de inversión, aunque lea los mercados como una señal más.</li>
          </ul>
        </Panel>
      </div>

      {/* ---------- Cómo funciona ---------- */}
      <Panel titulo="Cómo funciona" meta="cuatro pasos por ciclo">
        <ol className="grid gap-x-6 gap-y-5 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["01", "Escucha", "8 agentes leen NOAA, USGS, ESA, Tomsk y mercados en cada ciclo, nodo por nodo."],
            ["02", "Reconoce", "Compara contra la memoria de 32 años: 15 tipos de precursor y 5 muros vigilan la coincidencia."],
            ["03", "Consensúa", "El Padre cruza familias, pesa credibilidad por mérito y estima cuánto falta."],
            ["04", "Aprende", "El Juez compara con la realidad y disciplina: omitir un evento pesa 10× más que una falsa alarma."],
          ].map(([num, titulo, cuerpo]) => (
            <li key={num} className="border-t border-border pt-3">
              <div className="flex items-baseline gap-2">
                <span className="mono text-micro font-semibold" style={{ color: "var(--color-accent)" }}>
                  {num}
                </span>
                <span className="text-body font-semibold text-foreground">{titulo}</span>
              </div>
              <p className="mt-1.5 text-meta leading-relaxed text-muted" style={{ textWrap: "pretty" }}>
                {cuerpo}
              </p>
            </li>
          ))}
        </ol>
      </Panel>

      {/* ---------- Estado real: una cifra manda ---------- */}
      <Panel
        titulo="Dónde está hoy"
        meta="medido, no prometido"
        nota="Estos números salen de la auditoría del Juez sobre la fase viva. Se publican tal cual, incluso cuando no favorecen al sistema: un tablero de precursores que sólo enseña sus aciertos no sirve para decidir nada."
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
          <div>
            <div className="etiqueta">Ganancia sobre alertar a ciegas</div>
            <div
              className="mt-1.5 text-[length:var(--text-hero-num)] font-bold leading-none tracking-tight tnum"
              style={{ color: aporta ? "var(--color-calma)" : "var(--color-aviso)" }}
            >
              {ganancia != null ? `${ganancia.toFixed(2)}×` : <span className="dato-ausente">—</span>}
            </div>
            <p
              className="mt-2.5 max-w-[42ch] text-meta leading-relaxed"
              style={{ color: aporta ? "var(--color-muted)" : "var(--color-aviso)" }}
            >
              {veredicto ??
                "Compara la precisión de la alarma contra la tasa base. 1× significa que alertar siempre habría rendido igual."}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-x-6 gap-y-4 self-center border-l border-border pl-6">
            <div>
              <div className="etiqueta">Asertividad viva</div>
              <div className="mono mt-1 text-[length:var(--text-metric)] font-semibold text-foreground">
                {asert != null ? `${(asert * 100).toFixed(1)}%` : <span className="dato-ausente">—</span>}
              </div>
              <div className="mt-0.5 text-micro leading-snug text-faint">
                {mudo != null
                  ? `un bot mudo saca ${(mudo * 100).toFixed(1)}%`
                  : "cuenta los silencios en calma"}
              </div>
            </div>
            <div>
              <div className="etiqueta">Ciclos corridos</div>
              <div className="mono mt-1 text-[length:var(--text-metric)] font-semibold text-foreground">
                {cicloId != null ? Number(cicloId).toLocaleString("es-MX") : <span className="dato-ausente">—</span>}
              </div>
              <div className="mt-0.5 text-micro text-faint">desde el arranque</div>
            </div>
            <div className="col-span-2 border-t border-border pt-3">
              <div className="etiqueta">Patrones cimáticos aprendidos</div>
              <div className="mono mt-1 text-[length:var(--text-read)] font-semibold text-foreground">
                <Cifra valor={patrones} digits={0} />
              </div>
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
