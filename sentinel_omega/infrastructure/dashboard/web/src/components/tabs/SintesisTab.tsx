/**
 * SÍNTESIS — vista ejecutiva del sistema.
 *
 * Datos reales (contratos verificados contra :8787):
 *   /api/estado-vivo → JSON unificado del launcher: ciclo, auditoria,
 *                      senales (con lag), tono (cimático), muro_lags, GOES
 *   /api/bots        → items por bot (voto, asertividad, firmas)
 *   /api/juez        → items fase viva (para el flujo bot → veredicto)
 *   /api/modelos     → habilidad MEDIDA de los ONNX (AUC vs nulo por nodo)
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
  EscalaRiesgo,
  SegmentosMuro,
  nivelDe,
  colorNivel,
  accionNivel,
} from "@/components/ui/data";
import { SankeyDiagram } from "@/components/diagrams/SankeyDiagram";
import { fmtTs } from "@/lib/utils";

export function SintesisTab() {
  const evF = useCallback(() => api.estadoVivo(), []);
  const botsF = useCallback(() => api.bots(), []);
  const juezF = useCallback(() => api.juez(100, "viva"), []);
  const modelosF = useCallback(() => api.modelos(), []);

  const ev = usePoll(evF, 30000);
  const bots = usePoll(botsF, 30000);
  const juez = usePoll(juezF, 30000);
  const modelos = usePoll(modelosF, 60000);

  if (ev.error) return <BannerError mensaje={ev.error} />;
  if (ev.loading && !ev.data) return <SinDatos titulo="Leyendo estado vivo del sistema…" />;

  const d: any = ev.data ?? {};
  const ciclo: any = d.ciclo ?? {};
  const aud: any = d.auditoria ?? {};
  const tono: any = d.tono ?? {};
  const senales: any[] = d.senales ?? [];
  const muroLags: any = d.muro_lags ?? null;
  const cimaticaTop: any[] = d.cimatica_top ?? [];

  const fantasma = ciclo.fantasma != null ? Number(ciclo.fantasma) : null;
  const nivel = nivelDe(ciclo.nivel_riesgo);
  const muroActivas = ciclo.muro_walls_active != null ? Number(ciclo.muro_walls_active) : null;
  const muroBreach = Number(ciclo.muro_breach ?? 0) > 0;
  let tiposPrecursor: string[] = [];
  try {
    tiposPrecursor = ciclo.precursor_types ? JSON.parse(ciclo.precursor_types) : [];
  } catch {
    tiposPrecursor = [];
  }

  const aciertos = Number(aud.aciertos ?? 0);
  const fallos = Number(aud.fallos ?? 0);
  const falsosPositivos = Number(aud.falsos_positivos ?? 0);
  const ganancia = aud.ganancia != null ? Number(aud.ganancia) : null;
  const asertividad = aud.asertividad != null ? Number(aud.asertividad) : null;
  const asertividadMuda = aud.asertividad_muda != null ? Number(aud.asertividad_muda) : null;

  const B: any = bots.data ?? {};
  const bItems: any[] = B.items ?? [];

  const jItems: any[] = juez.data?.items ?? [];
  const conteo: Record<string, number> = {};
  jItems.forEach((r) => {
    const k = `${r.bot_name}→${r.resultado}`;
    conteo[k] = (conteo[k] || 0) + 1;
  });
  const sankeyNodos = [
    ...[...new Set(jItems.map((r) => r.bot_name))].map((b) => ({
      id: b,
      label: b,
      valor: jItems.filter((r) => r.bot_name === b).length,
    })),
    ...[...new Set(jItems.map((r) => r.resultado))].map((rr) => ({
      id: rr,
      label: rr,
      valor: jItems.filter((r) => r.resultado === rr).length,
    })),
  ];
  const sankeyEnlaces = Object.entries(conteo).map(([k, v]) => {
    const [origen, destino] = k.split("→");
    return { origen, destino, valor: v };
  });

  const m: any = modelos.data ?? {};
  const mItems: any[] = m.modelos ?? [];

  const lagTxt = muroLags?.dias_restante
    ? `${muroLags.dias_restante[0]}–${muroLags.dias_restante[1]} d (${muroLags.fecha_inicio} → ${muroLags.fecha_fin})`
    : null;

  return (
    <div className="space-y-5">
      <Panel
        titulo="Estado ahora"
        meta={
          ciclo.timestamp
            ? `ciclo ${fmtTs(Number(ciclo.timestamp))}${d.edad_s != null ? ` · edad ${Math.round(Number(d.edad_s) / 60)} min` : ""}`
            : "sin ciclo"
        }
        acento={nivel}
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            <div className="flex items-baseline gap-2">
              <span className="etiqueta">Fantasma</span>
              <span className="mono texto-principal fuente-negrita text-xl">
                <Cifra valor={fantasma} digits={2} />
              </span>
              <span className="mono texto-micro fuente-negrita" style={{ color: colorNivel(nivel) }}>
                {accionNivel(nivel)}
              </span>
              {d.goes_clase && (
                <span className="mono texto-micro texto-desvanecido">· GOES clase {d.goes_clase}</span>
              )}
            </div>
            <EscalaRiesgo valor={fantasma} max={50} umbrales={[15, 30]} />
            <p className="texto-meta texto-desvanecido">
              {ciclo.geo_signal
                ? `Señal geodinámica: ${ciclo.geo_signal}${ciclo.geo_confidence != null ? ` · confianza ${(Number(ciclo.geo_confidence) * 100).toFixed(0)}%` : ""}`
                : "Sin datos de telemetría"}
              {tiposPrecursor.length > 0 ? ` · precursores: ${tiposPrecursor.join(", ")}` : ""}
            </p>
            <div className="flex items-center gap-2">
              <span className="etiqueta">Muro</span>
              <div className="w-40">
                <SegmentosMuro activos={muroActivas} total={5} breach={muroBreach} />
              </div>
              <span className="mono texto-micro texto-desvanecido">
                {muroActivas ?? "—"} de 5{muroBreach ? " · BREACH" : ""}{lagTxt ? ` · convergencia en ${lagTxt}` : ""}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Metrica
              etiqueta="Ganancia (1× = no aporta)"
              valor={ganancia != null ? `${ganancia.toFixed(2)}×` : "—"}
              nivel={ganancia != null && ganancia > 1 ? "MODERATE" : "LOW"}
              contexto="del Juez, fase viva"
            />
            <Metrica
              etiqueta="Asertividad viva"
              valor={asertividad != null ? `${(asertividad * 100).toFixed(1)}%` : "—"}
              contexto={asertividadMuda != null ? `bot mudo: ${(asertividadMuda * 100).toFixed(1)}%` : undefined}
            />
            <Metrica etiqueta="Veredictos viva" valor={(aciertos + fallos + falsosPositivos).toLocaleString("es-MX")} />
            <Metrica
              etiqueta="GOES flux 24h"
              valor={d.goes_flux_max_24h != null ? Number(d.goes_flux_max_24h).toExponential(2) : "—"}
              contexto="rayos X máximos del día (W/m²)"
            />
          </div>
        </div>
      </Panel>

      <Panel
        titulo="Veredictos del Juez — fase viva"
        meta={`${aciertos.toLocaleString("es-MX")} aciertos · ${falsosPositivos.toLocaleString("es-MX")} falsas alarmas · ${fallos.toLocaleString("es-MX")} omisiones`}
        nota="La omisión pesa 10× más que la falsa alarma (pérdida asimétrica). El bot que nunca alarma también acierta la calma — lee la asertividad junto a su ganancia."
      >
        <BarraVeredictos aciertos={aciertos} falsosPositivos={falsosPositivos} fallos={fallos} />
      </Panel>

      <Panel
        titulo="Tono cimático de la ventana viva"
        meta={tono.ancla ? `ancla ${tono.ancla}` : "sin ancla"}
        nota={tono.construido_at ? `construido: ${tono.construido_at}` : undefined}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex items-baseline gap-2">
            <span className="etiqueta">Tono</span>
            <span className="mono texto-principal fuente-negrita text-xl">{tono.tono ?? "—"}</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(tono.dist ?? {}).map(([k, v]) => (
              <Metrica
                key={k}
                etiqueta={k}
                valor={<Cifra valor={v} digits={2} />}
                jerarquia="compacta"
                contexto="distancia al patrón"
              />
            ))}
          </div>
        </div>
      </Panel>

      <Panel titulo="Señales activas" meta={`${senales.length} con ancla vigente`}>
        <TablaDatos
          filas={senales}
          densa
          vacío="Sin señales activas"
          columnas={[
            { clave: "sitio", etiqueta: "Sitio" },
            { clave: "evento", etiqueta: "Evento" },
            { clave: "similitud", etiqueta: "Similitud", num: true, render: (r) => <Cifra valor={r.similitud} digits={3} /> },
            { clave: "recurrencia", etiqueta: "Recurrencia", num: true, render: (r) => (r.recurrencia != null ? String(r.recurrencia) : "—") },
            {
              clave: "lag_restante_h",
              etiqueta: "Lag restante (h)",
              num: true,
              render: (r) => <Cifra valor={r.lag_restante_h} digits={1} />,
            },
          ]}
        />
      </Panel>

      <Panel titulo="Flujo de consenso — bot → veredicto" meta={`últimos ${jItems.length} veredictos vivos`}>
        {jItems.length === 0 ? (
          <SinDatos titulo="Sin veredictos vivos recientes" />
        ) : (
          <SankeyDiagram nodos={sankeyNodos} enlaces={sankeyEnlaces} alto={240} />
        )}
      </Panel>

      <Panel titulo="Cimática — patrones más frecuentes" meta={`total ${d.cimatica_total ?? "—"}`}>
        <TablaDatos
          filas={cimaticaTop.slice(0, 8)}
          densa
          vacío="Sin patrones"
          columnas={[
            { clave: "event_class", etiqueta: "Clase" },
            { clave: "ambito", etiqueta: "Ámbito" },
            { clave: "frecuencia", etiqueta: "Frecuencia", num: true },
          ]}
        />
      </Panel>

      <Panel titulo="Estado de los bots (voto)" meta={`total ${bItems.length}`}>
        <TablaDatos
          filas={bItems}
          densa
          vacío="Sin datos de bots"
          columnas={[
            { clave: "bot_name", etiqueta: "Bot" },
            { clave: "peso_voto", etiqueta: "Voto", num: true, render: (r) => <Cifra valor={r.peso_voto} digits={3} /> },
            {
              clave: "asertividad_viva_individual",
              etiqueta: "Asert. viva",
              num: true,
              render: (r) => (
                <Cifra
                  valor={r.asertividad_viva_individual != null ? Number(r.asertividad_viva_individual) * 100 : null}
                  digits={1}
                  unidad="%"
                />
              ),
            },
            {
              clave: "firmas_exigibles",
              etiqueta: "Exigibles",
              num: true,
              render: (r) => {
                const tot = Number(r.firmas_consolidadas ?? 0);
                const ex = Number(r.firmas_exigibles ?? 0);
                return tot > 0 ? `${ex} / ${tot} (${((ex / tot) * 100).toFixed(0)}%)` : "—";
              },
            },
          ]}
        />
      </Panel>

      <Panel
        titulo="Modelos ONNX — habilidad medida"
        meta={m.medido_at ? `medido ${String(m.medido_at).slice(0, 10)}` : "sin medir"}
        nota="AUC contra el nulo por nodo, no contra 0.5: el nodo solo predice distinto cuando hay evento, y su tasa base ya es alta. Ningún modelo ha pasado la compuerta."
      >
        <TablaDatos
          filas={mItems}
          densa
          vacío="Sin modelos"
          columnas={[
            { clave: "bot", etiqueta: "Bot" },
            { clave: "kb", etiqueta: "Tamaño", num: true, render: (r) => (r.kb != null ? `${r.kb} KB` : "—") },
            { clave: "medido", etiqueta: "Medido", render: (r) => (r.medido ? "sí" : "sin medir") },
            { clave: "auc", etiqueta: "AUC", num: true, render: (r) => <Cifra valor={r.medido ? r.auc : null} digits={3} /> },
            { clave: "auc_nulo_por_nodo", etiqueta: "Nulo nodo", num: true, render: (r) => <Cifra valor={r.auc_nulo_por_nodo} digits={3} /> },
            {
              clave: "ganancia_sobre_nulo",
              etiqueta: "Ganancia",
              num: true,
              render: (r) => {
                if (!r.medido || r.ganancia_sobre_nulo == null) return "—";
                const g = Number(r.ganancia_sobre_nulo);
                return (
                  <span
                    className="mono texto-micro fuente-negrita"
                    style={{ color: g > 0 ? "var(--color-calma)" : "var(--color-critico)" }}
                  >
                    {g >= 0 ? "+" : ""}
                    {(g * 100).toFixed(1)}%
                  </span>
                );
              },
            },
          ]}
        />
      </Panel>
    </div>
  );
}
