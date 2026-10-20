import { useCallback, useMemo } from "react";
import { api, type Overview } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { AskBox } from "@/components/AskBox";
import { DataTable } from "@/components/DataTable";
import { LineSpark, SimplePie } from "@/components/charts/Sparkline";
import { Map2D } from "@/components/maps/Map2D";
import {
  Panel,
  Metrica,
  Cifra,
  EscalaRiesgo,
  SegmentosMuro,
  BarraVeredictos,
  SinDatos,
  BannerError,
  nivelDe,
  colorNivel,
  accionNivel,
  esAusente,
} from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

const flareEmoji = (cls: string) => cls === "X" ? "☀️" : cls === "M" ? "☀️" : cls === "C" ? "🌤️" : "";
const flareColor = (cls: string) => cls === "X" ? "var(--color-critico)" : cls === "M" ? "var(--color-aviso)" : cls === "C" ? "var(--color-atencion)" : "var(--color-faint)";

/**
 * PRINCIPAL — superficie MONITOR.
 *
 * Quien abre esta pestaña está vigilando un estado que cambia, no leyendo un
 * folleto. Por eso NO hay hero, ni tres tarjetas equivalentes, ni un número
 * gigante de adorno: hay una jerarquía de lectura.
 *
 * La composición es deliberada:
 *
 *   1. FRANJA DE ESTADO (lo que se lee de reojo desde la puerta): Fantasma
 *      sobre su escala real, el Muro como 5 segmentos, y la frase de qué
 *      hacer. Ocupa el ancho porque es lo único que importa si sólo miras
 *      dos segundos.
 *   2. HONESTIDAD DEL SISTEMA: la asertividad NUNCA va sola. Va pegada a la
 *      ganancia de Molchan y a la barra de veredictos, porque 97,7 % junto a
 *      0,84× significa "no aporta información", y el tablero tiene que hacer
 *      esa contradicción imposible de pasar por alto. Antes el 97,7 % vivía
 *      en una tarjeta verde y la ganancia en otra naranja del mismo tamaño:
 *      dos hechos contradictorios con igual peso visual.
 *   3. Contexto operativo (mapa, cimática, alertas) en densidad de trabajo.
 *
 * Regla de color respetada en todo el archivo: saturado = riesgo. Las series
 * de gráfica son neutras a propósito.
 */
export function PrincipalTab() {
  const ovF = useCallback(() => api.overview(), []);
  const alF = useCallback(() => api.alertas(20), []);
  const ciF = useCallback(() => api.cimatica(30), []);
  const caF = useCallback(() => api.cimaticaAhora(), []);
  const nF = useCallback(() => api.nodos(), []);
  const sF = useCallback(() => api.sismos(4.5, 40), []);
  const cycF = useCallback(() => api.ciclos(60), []);
  const repF = useCallback(() => api.reportes(), []);
  const acF = useCallback(() => api.bots(), []);
  const telF = useCallback(() => api.telemetry(), []);

  const ov = usePoll<Overview>(ovF, 20000);
  const al = usePoll(alF, 20000);
  const ci = usePoll(ciF, 30000);
  const ca = usePoll(caF, 30000);
  const n = usePoll(nF, 60000);
  const s = usePoll(sF, 30000);
  const cyc = usePoll(cycF, 20000);
  const rep = usePoll(repF, 60000);
  const ac = usePoll(acF, 60000);
  const tel = usePoll(telF, 30000);

  const d = ov.data;
  const nivel = nivelDe(d?.fantasma?.nivel_riesgo);
  const breach = Boolean(d?.muro?.muro_breach);

  const acData = ac.data as Record<string, unknown> | undefined;
  const ganancia = acData?.ganancia_real != null ? Number(acData.ganancia_real) : null;
  const precision = acData?.precision_alarma != null ? Number(acData.precision_alarma) : null;
  const tasaBase = acData?.tasa_base != null ? Number(acData.tasa_base) : null;
  const veredictoGanancia = acData?.veredicto_ganancia ? String(acData.veredicto_ganancia) : null;
  const asertividad =
    acData?.asertividad_viva_global != null ? Number(acData.asertividad_viva_global) : null;

  // Los tres veredictos tienen que venir del MISMO universo o la proporción
  // miente. `aciertos_total`/`fallos_total` son la suma POR BOT de
  // TBL_PESOS_BOTS (cada ventana contada una vez por bot: 138.068), mientras
  // que los falsos positivos son del sistema (1.651). Dibujar una barra con
  // ambos daba un 0 % de falsas alarmas que es falso. `veredictos_sistema`
  // sale entero de viva_real.
  const vs = acData?.veredictos_sistema as
    | { aciertos?: number; falsos_positivos?: number; fallos?: number }
    | undefined;
  const aciertos = Number(vs?.aciertos ?? 0);
  const falsosPositivos = Number(vs?.falsos_positivos ?? 0);
  const fallos = Number(vs?.fallos ?? 0);
  const hayVeredictos = aciertos + falsosPositivos + fallos > 0;

  const aporta = ganancia != null && ganancia > 1;

  const nodes = useMemo(
    () =>
      (n.data || [])
        .map((nd) => ({
          lat: Number(nd.lat),
          lon: Number(nd.lon),
          tipo: String(nd.tipo || ""),
          label: String(nd.nombre || ""),
          highlight:
            String(nd.nombre || "").toLowerCase().includes("tlaxcala") && String(nd.tipo) === "real",
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [n.data],
  );
  const quakes = useMemo(
    () =>
      (s.data?.items || [])
        .map((q) => ({
          lat: Number(q.lat),
          lon: Number(q.lon),
          mag: Number(q.magnitude),
          label: String(q.region || ""),
        }))
        .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)),
    [s.data],
  );

  const serieFantasma = useMemo(
    () =>
      [...(cyc.data || [])]
        .reverse()
        .map((r, i) => ({ i, y: esAusente(r.fantasma) ? null : Number(r.fantasma) }))
        .filter((p) => p.y !== null),
    [cyc.data],
  );

  const risk = Object.entries(d?.risk_distribution || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }));

  const geo = ((al.data?.geo_alerts as Record<string, unknown>[]) || []).slice(0, 4);
  const breaches = ((al.data?.muro_breaches as Record<string, unknown>[]) || []).slice(0, 4);
  const hot = ((al.data?.hot_fantasma as Record<string, unknown>[]) || []).slice(0, 4);
  const flares = ((al.data?.flare_alerts as Record<string, unknown>[]) || []).slice(0, 4);
  const topAlertas = [
    ...geo.map((r) => ({ ...r, _kind: "geo" })),
    ...breaches.map((r) => ({ ...r, _kind: "muro" })),
    ...hot.map((r) => ({ ...r, _kind: "fantasma" })),
    ...flares.map((r) => ({ ...r, _kind: "flare", flare_class: r.flare_class })),
  ].slice(0, 8);

  const caData = (ca.data || {}) as Record<string, unknown>;
  const bibliotecaPresente = caData.biblioteca_presente === true;
  const repFiles = rep.data?.files || [];

  if (ov.error) return <BannerError mensaje={ov.error} />;
  if (ov.loading && !ov.data) return <SinDatos titulo="Leyendo estado del sistema…" />;

  return (
    <div className="space-y-5">
      {/* ================= 1. FRANJA DE ESTADO ================= */}
      <section
        className="overflow-hidden rounded-lg border bg-surface"
        style={{
          borderColor: `color-mix(in oklch, ${colorNivel(nivel)} 38%, var(--color-border))`,
          boxShadow: `inset 0 2px 0 0 ${colorNivel(nivel)}`,
        }}
      >
        <div className="grid gap-px bg-border lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)_minmax(0,1fr)]">
          {/* Fantasma: la cifra que manda */}
          <div className="bg-surface p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="etiqueta">Índice Fantasma</div>
                <div
                  className="mt-1 text-[length:var(--text-hero-num)] font-bold leading-[1.02] tracking-tight tnum"
                  style={{ color: colorNivel(nivel) }}
                >
                  <Cifra valor={d?.fantasma?.value} digits={2} />
                </div>
              </div>
              <span
                className="mono shrink-0 rounded border px-2 py-1 text-micro font-semibold uppercase"
                style={{
                  color: colorNivel(nivel),
                  borderColor: `color-mix(in oklch, ${colorNivel(nivel)} 45%, transparent)`,
                  background: `color-mix(in oklch, ${colorNivel(nivel)} 12%, transparent)`,
                }}
              >
                {nivel === "DESCONOCIDO" ? "sin lectura" : accionNivel(nivel)}
              </span>
            </div>
            <div className="mt-4">
              <EscalaRiesgo valor={d?.fantasma?.value ?? null} max={50} umbrales={[15, 30]} />
            </div>
            <p className="mt-2.5 text-meta leading-snug text-muted">
              Estado físico agregado del planeta, no un pronóstico de sismo.
              LOW &lt;5 · MODERATE 5–15 · HIGH 15–30 · CRITICAL ≥30.
            </p>
          </div>

          {/* Muro */}
          <div className="bg-surface p-5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="etiqueta">Muro de 5 eventos</span>
              <span
                className="mono text-micro font-semibold uppercase"
                style={{ color: breach ? "var(--color-critico)" : "var(--color-faint)" }}
              >
                {breach ? "roto" : "íntegro"}
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-[length:var(--text-metric)] font-semibold tnum text-foreground">
                {d?.muro?.walls_active ?? "—"}
              </span>
              <span className="text-body text-faint">/ 5 paredes</span>
            </div>
            <div className="mt-3">
              <SegmentosMuro activos={d?.muro?.walls_active} total={5} breach={breach} />
            </div>
            <dl className="mt-3.5 space-y-1 text-meta">
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Correlación</dt>
                <dd className="mono text-body">
                  <Cifra valor={d?.muro?.correlation_score} digits={2} />
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Etiqueta</dt>
                <dd className="mono text-body">{d?.muro?.risk_label || <span className="dato-ausente">—</span>}</dd>
              </div>
            </dl>
            <p className="mt-2.5 text-meta leading-snug text-muted">
              Se rompe con 3 de 5. Mide coincidencia entre dominios, no causa.
            </p>
          </div>

          {/* Telemetría del ciclo */}
          <div className="bg-surface p-5">
            <div className="etiqueta">Telemetría del ciclo</div>
            <dl className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-2.5">
              {[
                ["Kp", d?.fantasma?.kp, 2, ""],
                ["Bz", d?.fantasma?.bz_nT, 2, "nT"],
                ["Viento", d?.fantasma?.viento_km_s, 0, "km/s"],
                ["Schumann", d?.fantasma?.schumann_hz, 2, "Hz"],
              ].map(([label, val, dig, uni]) => (
                <div key={String(label)}>
                  <dt className="text-micro text-faint">{String(label)}</dt>
                  <dd className="mono text-[length:var(--text-read)] font-semibold text-foreground">
                    <Cifra valor={val} digits={Number(dig)} unidad={String(uni) || undefined} />
                  </dd>
                </div>
              ))}
            </dl>
            {/* GOES X-ray flare (Alfa-2) */}
            {(tel.data?.sources || []).map((src: any) => {
              if (src.id !== "goes") return null;
              const flux = src.processed?.value?.flux_max;
              const cls = src.processed?.value?.flux_class;
              if (flux == null || cls === "none") return null;
              return (
                <div key="goes" className="mt-3.5 flex items-center gap-2 border-t border-border pt-3">
                  <span className="text-muted text-micro">GOES X-ray</span>
                  <span
                    className="mono text-body font-semibold"
                    style={{ color: flareColor(cls) }}
                  >
                    {flareEmoji(cls)} Clase {cls} · {Number(flux).toExponential(1)} W/m²
                  </span>
                  <span className="text-micro text-faint ml-auto">
                    M→WATCH, X→ALERT
                  </span>
                </div>
              );
            })}
            <div className="mt-3.5 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-meta">
              <span className="text-muted">
                Nodos <span className="mono text-body">{d?.counts?.nodos ?? "—"}</span>
              </span>
              <span className="text-muted">
                Sismos ≥4.5 <span className="mono text-body">{d?.counts?.sismos_m45 ?? "—"}</span>
              </span>
            </div>
            {esAusente(d?.fantasma?.schumann_hz) && (
              <p className="mt-2 text-micro leading-snug" style={{ color: "var(--color-aviso)" }}>
                Schumann: la FRECUENCIA no se mide desde el 2026-10-09 (la «fórmula»
                7,83+act×0,02 era un derivado y se retiró) --- entra NULL. Lo medido en
                vivo es la actividad (intensidad del espectrograma).
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ================= 2. HONESTIDAD DEL SISTEMA ================= */}
      <Panel
        titulo="¿El sistema aporta información?"
        meta="viva_real · juez"
        nota={
          <>
            La <b className="text-body">asertividad</b> cuenta como acierto cada silencio en el que no
            pasó nada, y la calma es casi todo; además deja las falsas alarmas fuera del denominador.
            Por eso nunca se enseña sola. La <b className="text-body">ganancia</b> compara la precisión
            de la alarma contra la tasa base: <span className="mono">1×</span> significa que alertar
            siempre habría dado lo mismo.
          </>
        }
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="space-y-4">
            <Metrica
              etiqueta="Ganancia sobre alertar a ciegas"
              jerarquia="principal"
              valor={ganancia != null ? `${ganancia.toFixed(2)}×` : <span className="dato-ausente">—</span>}
              nivel={ganancia == null ? "DESCONOCIDO" : aporta ? "LOW" : "HIGH"}
              contexto={
                veredictoGanancia ? (
                  <span style={{ color: aporta ? undefined : "var(--color-aviso)" }}>{veredictoGanancia}</span>
                ) : (
                  "Precisión de la alarma ÷ tasa base."
                )
              }
            />
            <div className="grid grid-cols-2 gap-4 border-t border-border pt-3.5">
              <Metrica
                etiqueta="Precisión de alarma"
                jerarquia="compacta"
                valor={precision != null ? `${(precision * 100).toFixed(2)}%` : <span className="dato-ausente">—</span>}
                contexto="de lo que avisó, acertó"
              />
              <Metrica
                etiqueta="Tasa base"
                jerarquia="compacta"
                valor={tasaBase != null ? `${(tasaBase * 100).toFixed(2)}%` : <span className="dato-ausente">—</span>}
                contexto="pasa sin avisar nadie"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-baseline justify-between gap-3">
              <span className="etiqueta">Veredictos del sistema · fase viva</span>
              <span className="mono text-meta text-muted">
                asertividad{" "}
                <span className="font-semibold text-body">
                  {asertividad != null ? `${(asertividad * 100).toFixed(1)}%` : "—"}
                </span>
              </span>
            </div>
            {hayVeredictos ? (
              <BarraVeredictos aciertos={aciertos} falsosPositivos={falsosPositivos} fallos={fallos} />
            ) : (
              <p className="text-meta text-muted">Sin veredictos resueltos en la fase viva.</p>
            )}
            {!aporta && ganancia != null && (
              <p
                className="rounded border px-3 py-2 text-meta leading-relaxed"
                style={{
                  borderColor: "color-mix(in oklch, var(--color-aviso) 40%, transparent)",
                  background: "var(--color-aviso-dim)",
                  color: "var(--color-aviso)",
                }}
              >
                Lectura honesta: la asertividad alta y la ganancia por debajo de 1× no se contradicen
                — describen lo mismo desde dos ángulos. El sistema acierta casi siempre porque casi
                siempre está en calma; hoy sus alarmas todavía no superan a alertar a ciegas.
              </p>
            )}
          </div>
        </div>
      </Panel>

      {/* ================= 3. CONTEXTO OPERATIVO ================= */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel
          titulo="Fantasma en los últimos ciclos"
          meta={`${serieFantasma.length} ciclos`}
          nota="Los umbrales 15 y 30 van dibujados: una línea sin su escala no dice si el sistema está tranquilo o a punto de avisar."
        >
          {serieFantasma.length ? (
            <LineSpark
              data={serieFantasma}
              xKey="i"
              yKey="y"
              height={190}
              color="var(--color-serie-1)"
              referencias={[
                { valor: 15, color: "var(--color-aviso)", etiqueta: "15 avisar" },
                { valor: 30, color: "var(--color-critico)", etiqueta: "30 protocolo" },
              ]}
              dominio={[0, Math.max(32, ...serieFantasma.map((p) => Number(p.y)))]}
            />
          ) : (
            <SinDatos titulo="Sin ciclos para la serie" />
          )}
        </Panel>

        <Panel titulo="Distribución de riesgo" meta="histórico">
          {risk.length ? (
            <SimplePie
              data={risk.map((r) => ({
                ...r,
                color: colorNivel(nivelDe(r.name)),
              }))}
              height={190}
              centro={{
                valor: risk.reduce((a, b) => a + b.value, 0).toLocaleString("es-MX"),
                etiqueta: "ciclos",
              }}
            />
          ) : (
            <SinDatos titulo="Sin distribución" detalle="La DB no reporta reparto por nivel." />
          )}
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Panel
          titulo="Nodos y sismos recientes"
          meta="125 nodos · M≥4.5"
          nota="Mercator 2D de la topología UVG y los sismos del catálogo USGS. No es un mapa de alertas: ubica dónde mira el sistema."
        >
          <Map2D nodes={nodes} quakes={quakes} highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }} />
        </Panel>

        <Panel
          titulo="Cimática ahora"
          meta="tbl_cimatica_patrones"
          nota="La figura actual se compara contra la biblioteca histórica. Sin biblioteca no hay comparación posible: el conteo de patrones por sí solo no valida nada."
        >
          <div className="space-y-3.5">
            <Metrica
              etiqueta="Patrones aprendidos"
              valor={
                ci.data?.total != null
                  ? Number(ci.data.total).toLocaleString("es-MX")
                  : <span className="dato-ausente">—</span>
              }
              contexto="claves cimáticas registradas"
            />
            <div className="border-t border-border pt-3">
              <div className="etiqueta">Biblioteca de referencia</div>
              {bibliotecaPresente ? (
                <div className="mono mt-1 text-[length:var(--text-read)] font-semibold text-foreground">
                  {Number(caData.biblioteca_n ?? 0).toLocaleString("es-MX")} figuras
                </div>
              ) : (
                <div className="mt-1 text-meta leading-snug" style={{ color: "var(--color-aviso)" }}>
                  Tabla ausente en esta base — no es una biblioteca vacía, es que nunca se creó.
                </div>
              )}
            </div>
            {caData.current_clave ? (
              <div className="border-t border-border pt-3">
                <div className="etiqueta">Clave actual</div>
                <p className="mono mt-1 break-all text-micro leading-relaxed text-muted">
                  {String(caData.current_clave).slice(0, 180)}
                  {String(caData.current_clave).length > 180 ? "…" : ""}
                </p>
              </div>
            ) : null}
          </div>
        </Panel>
      </div>

      <Panel
        titulo="Alertas recientes"
        meta={topAlertas.length ? `${topAlertas.length} registros` : "sin actividad"}
      >
        <DataTable
          rows={topAlertas}
          densa
          empty="Sin alertas activas. En un sistema de precursores esto es lo normal, no un fallo."
          columns={[
            { key: "_kind", label: "Origen" },
            { key: "timestamp", label: "Cuándo", render: (r) => fmtTs(r.timestamp) },
            {
              key: "fantasma",
              label: "Fantasma",
              num: true,
              render: (r) => r._kind === "flare" ? <span className="dato-ausente">—</span> : <Cifra valor={r.fantasma} digits={2} />,
            },
            {
              key: "flare_class",
              label: "Clase",
              render: (r) => {
                if (r._kind !== "flare" || !r.flare_class) return <span className="dato-ausente">—</span>;
                const cls = String(r.flare_class);
                return (
                  <span className="mono font-semibold" style={{ color: flareColor(cls) }}>
                    {flareEmoji(cls)} {cls}
                  </span>
                );
              },
            },
            {
              key: "nivel_riesgo",
              label: "Nivel",
              render: (r) => {
                if (r._kind === "flare") {
                  const cls = String(r.flare_class || "");
                  return (
                    <span className="mono font-semibold" style={{ color: flareColor(cls) }}>
                      {cls === "X" ? "ALERT" : cls === "M" ? "WATCH" : "INFO"}
                    </span>
                  );
                }
                const nv = nivelDe(String(r.nivel_riesgo || r.risk_label || r.geo_signal || ""));
                const txt = String(r.nivel_riesgo || r.risk_label || r.geo_signal || "");
                if (!txt) return <span className="dato-ausente">—</span>;
                return (
                  <span className="mono" style={{ color: colorNivel(nv) }}>
                    {txt}
                  </span>
                );
              },
            },
          ]}
        />
      </Panel>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <Panel titulo="Reportes publicados" meta="estado/">
          {rep.data?.present && repFiles.length ? (
            <ul className="space-y-1.5">
              {repFiles.slice(0, 6).map((f) => (
                <li key={f.name} className="flex items-baseline justify-between gap-3 text-meta">
                  <span className="mono truncate text-body">{f.name}</span>
                  <span className="mono shrink-0 text-faint">{(f.bytes / 1024).toFixed(0)} KB</span>
                </li>
              ))}
            </ul>
          ) : (
            <SinDatos titulo="Sin reportes" detalle="No hay carpeta estado/ en este árbol." />
          )}
        </Panel>

        <Panel
          titulo="Preguntar al Concilio"
          meta="lee la DB en vivo"
          nota="Modelos locales (Ollama) con acceso de lectura a la base. Las respuestas citan lo que encuentran; no sustituyen al reporte del Juez."
        >
          <AskBox />
        </Panel>
      </div>
    </div>
  );
}
