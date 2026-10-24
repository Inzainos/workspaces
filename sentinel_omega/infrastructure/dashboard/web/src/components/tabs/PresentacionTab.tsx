/**
 * PRESENTACIÓN — la única superficie donde un hero es correcto.
 *
 * Antes era un folleto estático con números inventados (39.138 firmas
 * "nuevas", 985.592 "recurrentes"). Ahora: QUIÉN es el sistema y QUÉ
 * está midiendo AHORA, con datos reales de /api/overview y /api/firmas.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  BannerError,
  nivelDe,
  colorNivel,
  accionNivel,
} from "@/components/ui/data";
import { Map2D } from "@/components/maps/Map2D";

const DOMINIOS = [
  { icono: "🛰️", nombre: "Espacio", detalle: "Bz, Kp, viento solar, GOES X-ray, Schumann (actividad)" },
  { icono: "🌍", nombre: "Tierra", detalle: "Sismos USGS M4.5+, enjambres, cobertura satelital" },
  { icono: "🌫️", nombre: "Atmósfera", detalle: "Presión, SO₂, niebla, forecast 5d/3h (observacional)" },
  { icono: "📊", nombre: "Financiero", detalle: "VIX, FGI, BTC — contexto con techo WATCH, nunca ALERT" },
];

const BOTS = [
  { nombre: "alfa1", dominio: "Clima espacial", detalle: "Bz, Kp, viento, protones" },
  { nombre: "alfa2", dominio: "Satélites", detalle: "ESA térmico + GOES X-ray" },
  { nombre: "beta1", dominio: "Cimática", detalle: "Espectro Kp + Schumann-actividad" },
  { nombre: "beta2", dominio: "Atmósfera", detalle: "Presión, SO₂, niebla" },
  { nombre: "delta", dominio: "Financiero", detalle: "VIX, FGI, BTC, tendencias" },
  { nombre: "omega", dominio: "Ritmo cósmico", detalle: "Luna, Schumann, acoplamientos" },
  { nombre: "loki", dominio: "Rotación solar", detalle: "Carrington 26-29d, ganancia 3.4×" },
  { nombre: "padre", dominio: "Consenso", detalle: "Árbitro entre familias" },
];

export function PresentacionTab() {
  const ovF = useCallback(() => api.overview(), []);
  const firmasF = useCallback(() => api.firmas(), []);
  const nodosF = useCallback(() => api.nodos(), []);
  const sismosF = useCallback(() => api.sismos(4.5, 40), []);

  const ov = usePoll(ovF, 30000);
  const firmas = usePoll(firmasF, 60000);
  const nodos = usePoll(nodosF, 60000);
  const sismos = usePoll(sismosF, 30000);

  if (ov.error) return <BannerError mensaje={ov.error} />;

  const d = (ov.data || {}) as Record<string, any>;
  const fdata = (firmas.data || {}) as Record<string, any>;
  const nivel = nivelDe(d.fantasma?.nivel_riesgo);
  const totalFirmas = fdata.total != null ? Number(fdata.total) : null;
  const byClase = (fdata.by_clase || []) as Array<Record<string, any>>;

  const nodes = (nodos.data || []).map((nd: any) => ({
    lat: Number(nd.lat),
    lon: Number(nd.lon),
    tipo: String(nd.tipo || ""),
    label: String(nd.nombre || ""),
    sat: nd.saturacion != null ? Number(nd.saturacion) : undefined,
    medido: nd.saturacion != null,
    highlight: String(nd.nombre || "").toLowerCase().includes("tlaxcala"),
  })).filter((p: any) => Number.isFinite(p.lat) && Number.isFinite(p.lon));

  const quakes = (sismos.data?.items || []).map((q: any) => ({
    lat: Number(q.lat),
    lon: Number(q.lon),
    mag: Number(q.magnitude),
    label: String(q.region || ""),
    depthKm: q.depth_km != null ? Number(q.depth_km) : undefined,
    ts: q.timestamp != null ? Number(q.timestamp) : undefined,
  })).filter((p: any) => Number.isFinite(p.lat) && Number.isFinite(p.lon));

  return (
    <div className="space-y-6">
      {/* HERO: quién es el sistema y qué está midiendo AHORA */}
      <section
        className="rounded-xl border bg-surface p-6"
        style={{
          borderColor: `color-mix(in oklch, ${colorNivel(nivel)} 35%, var(--color-border))`,
          boxShadow: `inset 0 3px 0 0 ${colorNivel(nivel)}`,
        }}
      >
        <div className="flex flex-col lg:flex-row items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-muted uppercase tracking-wider">
              Sentinel Omega · Fractal Core Research
            </div>
            <h1 className="mt-2 text-3xl font-bold text-foreground">
              Detección de anomalías naturales multi-dominio
            </h1>
            <p className="mt-3 text-sm text-muted leading-relaxed max-w-[60ch]">
              8 bots especializados monitorean espacio, tierra, atmósfera y financiero.
              El Padre consensúa entre familias; el Juez audita contra realidad.
              <b className="text-foreground"> Lectura, no predicción.</b>
            </p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-xs text-muted">Estado ahora</div>
            <div className="mt-1 text-5xl font-bold tnum" style={{ color: colorNivel(nivel) }}>
              <Cifra valor={d.fantasma?.value} digits={2} />
            </div>
            <div
              className="mono mt-1 inline-block rounded border px-3 py-1 text-xs font-bold uppercase"
              style={{
                color: colorNivel(nivel),
                borderColor: `color-mix(in oklch, ${colorNivel(nivel)} 45%, transparent)`,
                background: `color-mix(in oklch, ${colorNivel(nivel)} 12%, transparent)`,
              }}
            >
              {nivel === "DESCONOCIDO" ? "sin lectura" : accionNivel(nivel)}
            </div>
            {d.muro && (
              <div className="mt-3 text-xs text-muted">
                Muro: <b className="text-foreground">{d.muro.walls_active ?? "—"}</b> de 5
                {d.muro.muro_breach ? " · ROTO" : ""}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Mapa con silueta de continentes */}
      <Panel
        titulo="Malla UVG-125 y sismos recientes"
        meta={sismos.data?.total_matching != null ? `${sismos.data.total_matching.toLocaleString("es-MX")} sismos M≥4.5` : "M≥4.5"}
        nota="Mercator con costas de continentes, 125 nodos de topología y sismos del catálogo USGS con color por magnitud. No es un mapa de alertas: ubica dónde mira el sistema."
      >
        <Map2D nodes={nodes} quakes={quakes} highlight={{ lat: 19.31, lon: -98.23, label: "Tlaxcala" }} />
      </Panel>

      {/* Los 4 dominios */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {DOMINIOS.map((dom) => (
          <div key={dom.nombre} className="rounded-lg border border-border bg-surface-sunken/40 p-4">
            <div className="text-2xl">{dom.icono}</div>
            <div className="mt-2 font-bold text-foreground">{dom.nombre}</div>
            <div className="mt-1 text-xs text-muted leading-snug">{dom.detalle}</div>
          </div>
        ))}
      </div>

      {/* Los 8 bots */}
      <Panel
        titulo="Los 8 bots del sistema"
        meta="cada uno con su dominio y su memoria"
        nota="Alfa-1 y Alfa-2 vigilan el espacio; Beta-1 y Beta-2 la cimática y atmósfera; Delta el humor financiero; Omega el ritmo cósmico; Loki la resonancia solar. El Padre consensúa."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {BOTS.map((bot) => (
            <div key={bot.nombre} className="rounded-lg border border-border/60 bg-surface-sunken/40 p-3">
              <div className="flex items-baseline gap-2">
                <span className="mono font-bold text-foreground">{bot.nombre}</span>
                <span className="text-xs text-faint">{bot.dominio}</span>
              </div>
              <div className="mt-1 text-xs text-muted">{bot.detalle}</div>
            </div>
          ))}
        </div>
      </Panel>

      {/* La memoria: firmas reales */}
      <Panel
        titulo="La memoria del sistema"
        meta={totalFirmas != null ? `${totalFirmas.toLocaleString("es-MX")} firmas en TBL_FIRMAS` : "TBL_FIRMAS"}
        nota="Sólo las firmas que discriminan eventos frente a calma (lift ≥2.0) son conocimiento exigible. El resto son patrones que se repiten sin decir nada."
      >
        <div className="grid gap-4 md:grid-cols-4">
          <Metrica
            etiqueta="Firmas totales"
            valor={totalFirmas != null ? totalFirmas.toLocaleString("es-MX") : "—"}
            contexto="toda la memoria aprendida"
          />
          <Metrica
            etiqueta="Clases de evento"
            valor={byClase.length > 0 ? String(byClase.length) : "—"}
            contexto="tipos de evento que la memoria reconoce"
            jerarquia="compacta"
          />
          <Metrica
            etiqueta="Ciclos registrados"
            valor={d.counts?.nodos != null ? String(d.counts.nodos) : "—"}
            contexto="nodos de topología viva"
            jerarquia="compacta"
          />
          <Metrica
            etiqueta="Sismos en ventana"
            valor={sismos.data?.total_matching != null ? sismos.data.total_matching.toLocaleString("es-MX") : "—"}
            contexto="M≥4.5 en el catálogo"
            jerarquia="compacta"
          />
        </div>
      </Panel>

      {/* Lo que NO hace */}
      <div className="rounded-lg border border-dashed border-border bg-surface-sunken/40 p-4">
        <p className="text-sm text-muted">
          <strong className="text-foreground">Lo que este sistema NO hace (medido, no especulado):</strong>{" "}
          NO predice sismos vía Schumann (cerrado en negativo en 2 estaciones). NO tiene modelos ONNX aprobados
          (la compuerta negó a los 7: AUC ~0.5 vs nulo-por-nodo 0.899). NO mide la frecuencia Schumann en vivo
          (retirada 2026-10-09; sólo la actividad). Lo que SÍ hace: mide honestamente, con su modelo nulo al lado.
        </p>
      </div>
    </div>
  );
}
