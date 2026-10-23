/**
 * MODELOS — los 8 ONNX con su habilidad MEDIDA (compuerta de habilidad),
 * el estado de las firmas por bot, y el muro de lags cuando está activo.
 * Datos: /api/modelos, /api/firmas, /api/bots, /api/muro_lags.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError, TablaDatos } from "@/components/ui/data";
import { SimpleBars } from "@/components/charts/Sparkline";

export function ModelosTab() {
  const modelosF = useCallback(() => api.modelos(), []);
  const firmasF = useCallback(() => api.firmas(), []);
  const mlF = useCallback(() => api.muroLags(), []);

  const modelos = usePoll(modelosF, 60000);
  const firmas = usePoll(firmasF, 60000);
  const ml = usePoll(mlF, 30000);

  if (modelos.error && firmas.error) return <BannerError mensaje={modelos.error || firmas.error} />;

  const m = (modelos.data || {}) as Record<string, any>;
  const f = (firmas.data || {}) as Record<string, any>;
  const mlData = (ml.data || {}) as Record<string, any>;
  const mlActivo = mlData.activo === true;
  const restantes = (mlData.dias_restantes ?? []) as number[];

  const listaModelos = (m.modelos || []) as Array<Record<string, any>>;
  const byClase = (f.by_clase || []) as Array<Record<string, any>>;
  const totalFirmas = f.total != null ? Number(f.total) : null;

  return (
    <div className="space-y-5">
      {/* KPIs de arriba */}
      <div className="grid gap-4 md:grid-cols-4">
        <Metrica
          etiqueta="Firmas totales"
          valor={totalFirmas != null ? totalFirmas.toLocaleString("es-MX") : "—"}
          contexto="TBL_FIRMAS · toda la memoria"
        />
        <Metrica
          etiqueta="Modelos ONNX"
          valor={listaModelos.length > 0 ? String(listaModelos.length) : "—"}
          contexto="en disco (compuerta decide)"
          jerarquia="compacta"
        />
        <Metrica
          etiqueta="Muro de lags"
          valor={mlActivo ? "ACTIVO" : "inactivo"}
          contexto={mlActivo && restantes.length === 2 ? `faltan ~${restantes[0]}–${restantes[1]} d` : "sin ventana activa"}
          jerarquia="compacta"
        />
        <Metrica
          etiqueta="Habilidad medida"
          valor={m.medido_at ? String(m.medido_at).slice(0, 10) : "sin medir"}
          contexto="fecha de la última evaluación"
          jerarquia="compacta"
        />
      </div>

      {/* Compuerta de habilidad */}
      <Panel
        titulo="Compuerta de habilidad (ONNX)"
        meta={m.medido_at ? `medido ${String(m.medido_at).slice(0, 10)}` : "sin medir"}
        nota={
          "AUC es la habilidad medida fuera de muestra y Ganancia lo que añade sobre el modelo nulo por nodo " +
          "(la propia historia sísmica del nodo). Un .onnx en disco no es un modelo que acierte: " +
          "«sin medir» significa que su AUC nunca se calculó, no que esté bien."
        }
      >
        {modelos.error ? (
          <BannerError mensaje={modelos.error} />
        ) : !listaModelos.length ? (
          <SinDatos titulo="Sin metadato de modelos" />
        ) : (
          <TablaDatos
            filas={listaModelos}
            densa
            vacío="Sin modelos"
            columnas={[
              { clave: "bot", etiqueta: "Bot" },
              {
                clave: "estado",
                etiqueta: "Estado",
                render: (r) =>
                  !r.existe ? (
                    <span className="dato-ausente">sin modelo</span>
                  ) : !r.medido ? (
                    <span style={{ color: "var(--color-aviso)" }}>sin medir</span>
                  ) : r.aprueba ? (
                    <span style={{ color: "var(--color-calma)" }}>aprobado</span>
                  ) : (
                    <span style={{ color: "var(--color-critico)" }}>negado</span>
                  ),
              },
              { clave: "auc", etiqueta: "AUC", num: true, render: (r) => <Cifra valor={r.auc} digits={3} /> },
              { clave: "ganancia_sobre_nulo", etiqueta: "Ganancia", num: true, render: (r) => <Cifra valor={r.ganancia_sobre_nulo} digits={3} /> },
              { clave: "n", etiqueta: "Muestras", num: true, render: (r) => <Cifra valor={r.n} digits={0} /> },
              { clave: "kb", etiqueta: "Tamaño", num: true, render: (r) => (r.kb == null ? <Cifra valor={null} /> : `${r.kb} KB`) },
              {
                clave: "motivo",
                etiqueta: "Motivo",
                render: (r) =>
                  r.motivo ? <span className="text-muted">{String(r.motivo).slice(0, 80)}</span> : <span className="text-muted">—</span>,
              },
            ]}
          />
        )}
      </Panel>

      {/* Firmas por clase */}
      <Panel
        titulo="Firmas por clase de evento"
        meta={totalFirmas != null ? `${totalFirmas.toLocaleString("es-MX")} en TBL_FIRMAS` : "TBL_FIRMAS"}
        nota="Sólo las firmas consolidadas y EXIGIBLES (lift ≥2.0 contra calma) son conocimiento demostrado. Las demás son patrones que se repiten pero no discriminan."
      >
        {byClase.length ? (
          <>
            <SimpleBars
              data={byClase.slice(0, 10).map((r) => ({
                key: String(r.clase),
                value: Number(r.n),
                color: "var(--color-serie-1)",
                name: String(r.clase),
              }))}
              xKey="key"
              yKey="value"
              bars={[{ key: "value", color: "var(--color-serie-1)", name: "firmas" }]}
              height={180}
              mostrarX
            />
            <TablaDatos
              filas={byClase.slice(0, 10)}
              densa
              vacío="Sin firmas"
              columnas={[
                { clave: "clase", etiqueta: "Clase" },
                { clave: "n", etiqueta: "Firmas", num: true, render: (r) => <Cifra valor={r.n} digits={0} /> },
              ]}
            />
          </>
        ) : (
          <SinDatos titulo="Sin firmas" />
        )}
      </Panel>

      {/* Muro de lags si activo */}
      {mlActivo && (
        <Panel
          titulo="Muro de lags — ventana activa"
          meta={restantes.length === 2 ? `faltan ~${restantes[0]}–${restantes[1]} d` : ""}
          nota="Cuando el muro está activo, las firmas de víspera convergen hacia una ventana temporal específica por nodo."
        >
          <div className="grid gap-4 md:grid-cols-3">
            <Metrica etiqueta="Clases" valor={String(mlData.clases ?? "—")} contexto="lo que la ventana predice" />
            <Metrica etiqueta="Detectado" valor={mlData.detectado_en ? String(mlData.detectado_en) : "—"} contexto="ancla de la ventana" jerarquia="compacta" />
            <Metrica etiqueta="Vence" valor={mlData.fecha_fin ? String(mlData.fecha_fin) : "—"} contexto="fin de la ventana" jerarquia="compacta" />
          </div>
        </Panel>
      )}
    </div>
  );
}
