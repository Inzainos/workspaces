/**
 * SintesisTab - Vista ejecutiva del sistema Sentinel Omega
 * Muestra métricas clave, estado de los bots, auditoría del juez y visualizaciones clave
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, BarraVeredictos, SinDatos, BannerError, TablaDatos, nivelDe, colorNivel, accionNivel, esAusente } from "@/components/ui/data";
import { SeñalesVivas } from "@/components/SeñalesVivas";
import { SankeyDiagram } from "@/components/diagrams/SankeyDiagram";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { fmtTs } from "@/lib/utils";
import { Gauge } from "@/components/charts/componentes";

export function SintesisTab() {
  const evF = useCallback(() => api.estadoVivo(), []);
  const botsF = useCallback(() => api.bots(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);
  const modelosF = useCallback(() => api.modelos(), []);

  const ev = usePoll(evF, 30000);
  const bots = usePoll(botsF, 30000);
  const juez = usePoll(juezF, 30000);
  const modelos = usePoll(modelosF, 60000);

  const d = (ev.data as any) ?? {};
  const aud = d?.auditoria || {};
  const ciclo = d?.ciclo || {};
  const senales = d?.senales || [];

  const aciertos = Number(aud.aciertos ?? 0);
  const fallos = Number(aud.fallos ?? 0);
  const falsosPositivos = Number(aud.falsos_positivos ?? 0);
  const ganancia = aud.ganancia != null ? Number(aud.ganancia) : null;
  const asertividad = aud.asertividad != null ? Number(aud.asertividad) : null;
  const asertividadMuda = aud.asertividad_muda != null ? Number(aud.asertividad_muda) : null;
  const fantasma = d?.ciclo?.fantasma != null ? Number(d.ciclo.fantasma) : null;
  const nivelRiesgo = d?.ciclo?.nivel_riesgo ?? null;
  const muroWalls = d?.ciclo?.muro_walls_active != null ? Number(d.ciclo.muro_walls_active) : null;
  const muroBreach = d?.ciclo?.muro_breach ?? false;

  const nivel = nivelDe(nivelRiesgo);
  const aporta = ganancia != null && ganancia > 1;

  // Preparar datos del Sankey: bots → Padre → Juez → veredicto
  const bItems = (bots.data?.items as Record<string, unknown>[]) || [];
  const totalBots = bItems.length;
  const botsConVoto = bItems.filter((r) => r.peso_voto != null && Number(r.peso_voto) > 0).length;
  const jueces = (juez.data?.items as Record<string, unknown>[]) || [];
  const juecesConVoto = jueces.filter((r) => r.peso_voto != null && Number(r.peso_voto) > 0).length;

  const aciertosJ = jueces.filter((r) => String(r.resultado || "").toUpperCase() === "ACIERTO").length;
  const fallosJ = jueces.filter((r) => String(r.resultado || "").toUpperCase() === "FALLO").length;
  const fpJ = jueces.filter((r) => String(r.resultado || "").toUpperCase() === "FALSO_POSITIVO").length;

  if (ev.error) return <BannerError mensaje={ev.error} />;
  if (ev.loading && !ev.data) return <SinDatos título="Leyendo estado vivo del sistema…" />;

  return (
    <div className="space-y-5">
      {/* ================= HEADER: estado ahora ================= */}
      <section className="rounded-lg border border-border bg-surface p-4">
        <div className="flex flex-col lg:flex-row items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">
                <Cifra valor={fantasma} />
              </span>
              <span
                className={`mono texto-micro fuente-negrita ${nivel === "CRITICAL" ? "texto-critico" : nivel === "HIGH" ? "texto-aviso" : nivel === "MODERATE" ? "texto-amarillo-400" : "texto-calma"}`}
              >
                {nivel === "DESCONOCIDO" ? "sin lectura" : nivel === "LOW" ? "calma" : nivel === "MODERATE" ? "atención" : nivel === "HIGH" ? "avisar" : "protocolo"}
              </span>
            </div>
            <p className="mt-2 texto-meta texto-desvanecido">
              {d.ciclo?.geo_signal || "Sin datos de telemetría"} · {d.ciclo?.geo_confidence ? `confianza ${Math.round(d.ciclo.geo_confidence * 100)}%` : ""}
            </p>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metrica
              detalle="Riesgo"
              riesgo={nivel === "ALTO" ? "ALTO" : nivel === "MEDIO" ? "MEDIO" : "BAJO"}
              acción="revisar"
            />
            <Metrica
              detalle="Ganancia"
              objetivo={ganancia != null ? `${ganancia.toFixed(2)}×` : "—"}
              riesgo={aporta ? "MEDIO" : "BAJO"}
              acción="quedarse"
            />
            <Metrica
              detalle="Asertividad viva"
              objetivo={asertividad != null ? `${(asertividad * 100).toFixed(1)}%` : "—"}
              riesgo="MEDIO"
              acción="revisar"
            />
            <Metrica
              detalle="Veredictos (vivo)"
              objetivo={juecesConVoto.toString()}
              riesgo={juecesConVoto > jueces.length / 2 ? "ALTO" : "BAJO"}
              acción="ver detalle"
            />
          </div>
        </div>
      </section>

      {/* ================= BARRA DE VEREDICTOS ================= */}
      <Panel
        detalle="Veredictos del Juez — fase viva"
        objetivo={`${aciertosJ} aciertos · ${fpJ} falsos positivos · ${fallosJ} fallos`}
        riesgo={falsosPositivos > aciertosJ ? "ALTO" : "BAJO"}
        acción="revisar modelos"
      >
        <BarraVeredictos aciertos={aciertosJ} falsosPositivos={fpJ} fallos={fallosJ} />
      </Panel>

      {/* ================= TONO CIMÁTICO ================= */}
      <Panel
        detalle="Cimática espectral — tono de la ventana viva"
        objetivo={d?.auditoria ? "últimos ciclos" : "sin datos"}
        riesgo={d?.tono?.tono === "sísmico" ? "MEDIO" : "BAJO"}
        acción="revisar patrón"
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="espacio-y-4">
            <div className="flex items-baseline gap-2">
              <span className="etiqueta">Tono actual</span>
              <span className={`mono texto-principal fuente-negrita ${d?.tono?.tono === "sísmico" ? "texto-aviso" : d?.tono?.tono === "volcánico" ? "texto-critico" : "texto-atencion"}`}>
                {d?.tono?.tono === "sísmico" ? "sísmica" : d?.tono?.tono === "volcánico" ? "volcánica" : d?.tono?.tono === "solar" ? "solar" : "—"}
              </span>
            </div>
            <div className="espacio-y-2">
              {Object.entries(d?.tono?.patrones || {}).map(([f, v]) => (
                <div key={f} className="flex items-básica gap-2 texto-meta">
                  <span className="mono encogido-0">{capitalizar(f)}:</span>
                  <span className="mono texto-principal fuente-negrita">{v != null ? v.toFixed(2) : "—"}</span>
                </div>
              ))}
              <p className="mt-2 texto-meta texto-desvanecido" style={{ fontSize: 12 }}>
                El tono lee el ritmo de clima espacial (fase y envolvente solar), no la fase lunar.
              </p>
            </div>
          </div>

          <div className="h-full">
            <SankeyDiagram
              nodos={[
                { nombre: "Omega", voto: d?.omega?.voto ?? 0 },
                { nombre: "Padre", valor: d?.padre?.pesos?.padre ?? 0 },
                { nombre: "Juez", valor: d?.juez?.aciertos ?? 0 },
                { nombre: "Córum", valor: juecesConVoto },
              ]}
              valores={[d?.omega?.peso ?? 0, d?.padre?.pesos?.padre ?? 0, d?.juez?.aciertos ?? 0, juecesConVoto]}
            />
          </div>
        </div>
      </Panel>

      {/* ================= SEÑALES VIVAS ================= */}
      {senales.length > 0 && (
        <Panel
          detalle="Señales activas"
          objetivo={`${senales.length} activas`}
          riesgo={senales.some((s) => s.nivel === "ALTO" || s.nivel === "CRITICAL") ? "ALTO" : "MEDIO"}
          acción="revisar señales activas"
        >
          <SeñalesVivas señales={senales as SeñalViva[]} tsSnapshot={Number(d.ts)} edadS={d.edad_s} />
        </Panel>
      )}

      {/* ================= TABLA DE BOTS ================= */}
      <Panel
        detalle="Estado de los bots (voto)"
        objetivo={`Total ${totalBots} · con voto ${botsConVoto}`}
      >
        <TablaDatos
          filas={bItems}
          densa
          vacío="Sin datos de bots"
          columnas={[
            { clave: "bot_nombre", nombre: "Bot" },
            { clave: "peso_voto", etiqueta: "Voto", num: true, render: (r) => <Cifra valor={r.peso_voto} dígitos={3} /> },
            { clave: "individual", etiqueta: "Individual", num: true, render: (r) => pct(r.individual) },
            { clave: "asertividad_viva_individual", etiqueta: "Viva", num: true, render: (r) => pct(r.asertividad_viva_individual) },
            { clave: "firmas_exigibles", etiqueta: "Exigibles", num: true, render: (r) => {
              const tot = Number(r.firmas_consolidadas ?? 0);
              const ex = Number(r.firmas_exigibles ?? 0);
              return tot > 0 ? `${ex} / ${tot} (${((ex / tot) * 100).toFixed(0)}%)` : "—";
            }},
          ]}
          páginaTamaño={12}
        />
      </Panel>

      {/* ================= MODELOS ================= */}
      <Panel
        detalle="Cimática (Omega)"
        objetivo={modelos.data?.medido_at ? `medido ${String(modelos.data.medido_at).slice(0, 10)}` : "sin medir"}
        riesgo="BAJO"
      >
        <div className="flex flex-col gap-4">
          {modelos.data?.modelos?.map((m: any) => (
            <div key={m.nombre} className="flex items-center gap-3 p-2 rounded-lg border border-border bg-surface-sunken">
              <span className="mono texto-principal fuente-negrita">{m.nombre}</span>
              <div className="flex items-center gap-2">
                <span className={`mono texto-micro ${m.aprobado ? "texto-esmeralda-400" : d?.firmas?.consolidadas?.value === 0 ? "texto-orange-400" : "texto-rose-400"}`}>
                  {m.aprobado ? "Aprobado" : m.jupiter?.fase_viva === "rechazado" ? "Rechazado" : "No verificado"}
                </span>
                <span className="mono texto-micro texto-desvanecido">
                  {m.asertividad_promedio?.toFixed(2) ?? "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function pct(v: unknown, dig = 1): string {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(dig)}%`;
}

function capitalizar(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function hayVeredictosJueces(jueces: Record<string, unknown>[]): boolean {
  return jueces.some((j) => String(j.resultado || "").toUpperCase() !== "PENDIENTE");
}
