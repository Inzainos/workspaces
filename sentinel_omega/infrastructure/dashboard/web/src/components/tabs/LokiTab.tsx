import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Kpi } from "@/components/Kpi";
import { DataTable } from "@/components/DataTable";
import { TabIntro, Caption } from "@/components/TabIntro";
import { Map2D } from "@/components/maps/Map2D";
import { Globe3D } from "@/components/maps/Globe3D";
import { LineSpark } from "@/components/charts/Sparkline";
import { EmptyState, ErrorBanner } from "@/components/EmptyState";
import { fmtNum, fmtTs, riskColor } from "@/lib/utils";

/**
 * Tab Loki — Resonancia del Ciclo Mayor (rediseño 2026-10-12).
 *
 * La teoría del operador (Campo Unificado Fractal) operacionalizada: el
 * sistema menor (tormentas geomagnéticas) resuena con el sistema mayor
 * (la rotación solar de Carrington, 27,275 d). Los números que se pintan
 * son los MEDIDOS contra 32 años (deploy/medir_loki_teoria.py): P(tormenta)
 * 0,94 % base → 3,19 % con antecedente hace 26-29 d (ganancia 3,4×).
 * La frecuencia de Schumann NO se mide desde el 2026-10-09: la señal es
 * la ACTIVIDAD.
 */
export function LokiTab() {
  const uF = useCallback(() => api.unificado(), []);
  const nF = useCallback(() => api.nodos(), []);
  const sF = useCallback(() => api.sismos(4.5, 80), []);
  const cF = useCallback(() => api.consenso(40), []);
  const lF = useCallback(() => api.layers(), []);

  const u = usePoll(uF, 20000);
  const n = usePoll(nF, 30000);
  const s = usePoll(sF, 30000);
  const c = usePoll(cF, 20000);
  const layers = usePoll(lF, 20000);

  const d = u.data || {};
  const fant = (d.fantasma || {}) as Record<string, unknown>;
  const muro = (d.muro || {}) as Record<string, unknown>;
  const tlax = (d.tlaxcala || {}) as Record<string, unknown>;
  const row = (tlax.row || {}) as Record<string, unknown>;
  const lat = Number(row.lat ?? tlax.spec_lat ?? 19.31);
  const lon = Number(row.lon ?? tlax.spec_lon ?? -98.23);

  const loki = (d.loki || {}) as Record<string, any>;
  const res = (loki.resonancia || null) as Record<string, any> | null;
  const post = (loki.posterior || {}) as Record<string, number>;
  const ultimo = (loki.ultimo || null) as Record<string, any> | null;
  const schAct = fant.schumann_activity;

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
  const quakes = (s.data?.items || [])
    .map((q) => ({
      lat: Number(q.lat),
      lon: Number(q.lon),
      mag: Number(q.magnitude),
      label: String(q.region || ""),
    }))
    .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon));

  const agents = ((layers.data?.agents as Record<string, unknown>[]) || []);
  const lokiLayer = agents.find((a) => String(a.label || a.bot_name || "").toLowerCase().includes("loki"));

  const cycles = ((c.data?.cycles as Record<string, unknown>[]) || []);
  const fantasmaSeries = [...cycles]
    .reverse()
    .map((r, i) => ({ i, y: Number(r.fantasma ?? 0) }));
  const botsConsenso = ((c.data?.bots as Record<string, unknown>[]) || []);

  if (u.error) return <ErrorBanner message={u.error} />;
  if (u.loading && !u.data) return <EmptyState title="Cargando Loki / Resonancia del Ciclo Mayor…" />;

  const nivel = String(fant.nivel_riesgo || "—");
  // El posterior que APLICA ahora: colapso (resonancia+grieta) > resonancia > base.
  const pAhora =
    res?.activa ? (post.resonancia != null ? post.resonancia : post.base) : post.base;

  const resTxt =
    res == null
      ? "SIN MEDIR"
      : res.activa
        ? `ACTIVA · hace ${res.dias_desde} d`
        : "inactiva";
  const vector = muro.muro_breach
    ? `El Muro está roto (${muro.walls_active}/5). Fantasma ${fmtNum(fant.value)} (${nivel}). Esto pide revisión humana.`
    : `Consenso: Fantasma ${fmtNum(fant.value)} (${nivel}), Muro ${muro.walls_active ?? "—"}/5. Loki vigila la resonancia del ciclo mayor; el resto es medición viva.`;

  return (
    <div className="space-y-4">
      <TabIntro title="Loki — Resonancia del Ciclo Mayor">
        <p>
          El sistema menor (tormentas geomagnéticas) resuena con el sistema mayor: la rotación
          solar de Carrington ({fmtNum(loki.rotacion_carrington_d, 3)} d) devuelve los agujeros
          coronales recurrentes. Nodo de observación: Tlaxcala 19.31 N, 98.23 W (node_id=11).
        </p>
        <p>
          Los porcentajes son <b>medidos contra 32 años</b> (1994-2025), no pronósticos: la
          ventana de resonancia dispara el 3,2 % de los días con ganancia 3,4× sobre la base.
        </p>
      </TabIntro>

      <div className="grid gap-3 md:grid-cols-4">
        <Kpi
          label="RESONANCIA"
          value={resTxt}
          accent={res?.activa ? "text-accent" : undefined}
          hint={res == null ? "sin antecedente medido (regla 7)" : "ventana 26-29 d tras tormenta Kp≥5"}
        />
        <Kpi
          label="P(TORMENTA HOY)"
          value={pAhora != null ? `${(pAhora * 100).toFixed(2)}%` : "—"}
          hint={`base ${(post.base ?? 0) * 100}% · con resonancia ${(post.resonancia ?? 0) * 100}%`}
        />
        <Kpi
          label="ÚLTIMA TORMENTA"
          value={res?.ultima_tormenta_dias != null ? `hace ${res.ultima_tormenta_dias} d` : "—"}
          hint="Kp≥5 en la tabla horaria (medido, no live)"
        />
        <Kpi
          label="FANTASMA"
          value={fmtNum(fant.value)}
          accent={riskColor(String(fant.nivel_riesgo))}
          hint={nivel}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <Kpi
          label="ROTACIÓN CARRINGTON"
          value={`${fmtNum(loki.rotacion_carrington_d, 3)} d`}
          hint="constante astronómica, no dato vivo"
        />
        <Kpi
          label="SCHUMANN"
          value={schAct != null ? `${fmtNum(schAct, 1)} %` : "—"}
          hint="actividad medida · frecuencia SIN MEDIR (retiro 2026-10-09)"
        />
        <Kpi
          label="TLAXCALA"
          value={`${fmtNum(lat, 2)} N, ${fmtNum(Math.abs(lon), 2)} W`}
          hint={String(row.nombre || "spec")}
        />
        <Kpi label="CIMÁTICA" value={String(d.cimatica_total ?? "—")} hint="patrones acumulados" />
      </div>

      <div className="rounded-lg border border-accent/40 bg-accent/10 px-4 py-3 text-sm">{vector}</div>

      <div className="rounded-lg border border-border px-4 py-3">
        <div className="text-xs text-muted">Capa Loki (última predicción viva)</div>
        <div className="text-lg font-semibold">{String(ultimo?.prediccion || lokiLayer?.prediccion || "SIN_DATOS")}</div>
        <div className="text-xs text-muted">
          conf {fmtNum(ultimo?.confianza ?? lokiLayer?.confianza)} · {fmtTs(ultimo?.timestamp ?? lokiLayer?.timestamp)}
        </div>
        {ultimo?.reasoning ? (
          <p className="mt-2 text-sm text-body/90">{String(ultimo.reasoning)}</p>
        ) : null}
        <Caption>
          La resonancia y el posterior son del CICLO (tabla horaria medida); la predicción, del
          Juez fase viva. El «Posterior Bayes» es la probabilidad real condicional, no un
          φ-alignment.
        </Caption>
      </div>

      <h4 className="text-sm font-medium">Consenso — timeline de ciclos</h4>
      {fantasmaSeries.length ? (
        <LineSpark data={fantasmaSeries} xKey="i" yKey="y" height={120} />
      ) : (
        <EmptyState title="Sin ciclos en /api/consenso" detail={String(c.error || "")} />
      )}
      <DataTable
        rows={cycles.slice(0, 20)}
        empty="Sin ciclos"
        columns={[
          { key: "timestamp", label: "Tiempo", render: (r) => fmtTs(r.timestamp) },
          { key: "fantasma", label: "Fantasma", render: (r) => fmtNum(r.fantasma) },
          { key: "nivel_riesgo", label: "Riesgo" },
          { key: "muro_walls_active", label: "Muro" },
          { key: "geo_signal", label: "Geo" },
          { key: "geo_consensus", label: "Consenso" },
        ]}
      />
      <DataTable
        rows={botsConsenso}
        empty="Sin pesos en consenso"
        columns={[
          { key: "bot_name", label: "Bot" },
          { key: "peso", label: "Peso", render: (r) => fmtNum(r.peso) },
          {
            key: "asertividad_viva",
            label: "Viva %",
            render: (r) =>
              r.asertividad_viva != null ? `${(Number(r.asertividad_viva) * 100).toFixed(1)}%` : "—",
          },
          { key: "n", label: "n" },
        ]}
      />
      <Caption>{String(c.data?.caption || d.caption || "")}</Caption>

      <Map2D nodes={nodes} quakes={quakes} highlight={{ lat, lon, label: "Tlaxcala" }} />
      <Globe3D nodes={nodes} quakes={quakes} />
    </div>
  );
}
