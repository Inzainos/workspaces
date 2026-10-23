/**
 * PADRÓN — superficie HONESTA: sin dato, se dice sin dato.
 *
 * El padrón electoral vive en su PROPIO proyecto (padron_afiliados_app:
 * Streamlit 11 pestañas + SQLite propio) y la API de Sentinel NO sirve
 * sus datos — ningún endpoint de :8787 los conoce. Inventar aquí una
 * tabla de afiliados sería la regla 2 violada (cero datos sintéticos).
 * Lo que este tab ofrece de verdad: el estado de la DB de Sentinel como
 * sistema y el PUNTERO al proyecto real.
 */
import { Panel, Metrica, SinDatos } from "@/components/ui/data";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { useCallback } from "react";

export function PadrónTab() {
  const healthF = useCallback(() => api.health(), []);
  const health = usePoll(healthF, 60000);
  const h = (health.data || {}) as Record<string, any>;

  return (
    <div className="space-y-5">
      <Panel
        titulo="Padrón de Afiliados — vive en su propio proyecto"
        meta="padron_afiliados_app"
        nota="Este tab no consulta datos electorales: la API de Sentinel no los sirve y fabricarlos rompería la regla de cero datos sintéticos. La fuente real es el proyecto independiente con su dashboard Streamlit (:8502) y su SQLite propio."
      >
        <div className="grid gap-4 md:grid-cols-3">
          <Metrica
            etiqueta="Proyecto"
            valor="padron_afiliados_app"
            contexto="repo git independiente · v1.0.0 esqueleto"
          />
          <Metrica
            etiqueta="Dashboard real"
            valor=":8502 (Streamlit)"
            contexto="11 pestañas · análisis demográfico, cohortes, cimática"
            jerarquia="compacta"
          />
          <Metrica
            etiqueta="Datos"
            valor="SQLite propio"
            contexto="6 tablas + vista de estadísticas"
            jerarquia="compacta"
          />
        </div>
      </Panel>

      <Panel
        titulo="Por qué aquí no hay cifras del padrón"
        meta="regla dura 2 y 7"
        nota="Faltante = NULL. La ausencia de un endpoint de padrón en Sentinel es un hecho, no un hueco que llenar con números plausibles. Si el operador decide integrar el padrón a esta API, este tab será el primero en consumirla."
      >
        <SinDatos
          titulo="Sin datos de padrón en esta API"
          detalle="El padrón electoral no vive en la DB de Sentinel ni en ninguno de sus endpoints verificados."
        />
      </Panel>

      <Panel titulo="Lo único real que puedo decir desde aquí" meta="/api/health">
        <div className="grid gap-4 md:grid-cols-2">
          <Metrica
            etiqueta="Salud de Sentinel"
            valor={h.status ? String(h.status) : "—"}
            contexto="el ecosistema que aloja este tablero"
          />
          <Metrica
            etiqueta="Ciclos registrados"
            valor={h.ciclos != null ? Number(h.ciclos).toLocaleString("es-MX") : "—"}
            contexto="TBL_CICLOS — la memoria del sistema"
            jerarquia="compacta"
          />
        </div>
      </Panel>
    </div>
  );
}
