/**
 * CIMÁTICA — superficie EXPLORE. La capa cimática completa del sistema:
 *
 *  - LA FIGURA: la clave de telemetría actual hecha imagen determinista
 *    (CimaticaFigura: FNV-1a → PRNG → anillos espejados tipo Chladni; la
 *    misma clave SIEMPRE dibuja la misma figura). La clave viva viene de
 *    /api/cimatica/ahora — NO es un placeholder.
 *  - EL TONO: la capa espectral de la tela SNT (audit 2026-10-21): el
 *    régimen de clima espacial de la ventana viva. Lee el tono, no la
 *    familia del evento — la víspera sísmica es climáticamente
 *    indistinguible del fondo quieto. Evidencia, no compuerta.
 *  - LOS PATRONES: tbl_cimatica_patrones vía /api/estado-vivo — el conteo
 *    de repetición. Un patrón frecuente NO es un patrón predictivo: eso
 *    lo decide el Juez (lift contra calma).
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, SinDatos, BannerError } from "@/components/ui/data";
import { CimaticaFigura } from "@/components/CimaticaFigura";
import { SimpleBars } from "@/components/charts/Sparkline";

const NOTA_TONO =
  "El tono lee el RÉGIMEN de clima espacial (quietud Kp/viento), no la familia del evento. " +
  "Las etiquetas son las vísperas del corpus; el vector de distancias es el payload. " +
  "Medido: familia 46.8% vs placebo 32.9% en LOO; concordancia viva documentada en el audit.";

export function CimaticaTab() {
  const caF = useCallback(() => api.cimaticaAhora(), []);
  const evF = useCallback(() => api.estadoVivo(), []);

  const ca = usePoll(caF, 30000);
  const ev = usePoll(evF, 30000);

  if (ca.error && ev.error) return <BannerError mensaje={ca.error} />;
  if (ev.loading && !ev.data) return <SinDatos titulo="Leyendo cimática…" />;

  const caData = (ca.data || {}) as Record<string, any>;
  const d = (ev.data || {}) as Record<string, any>;

  const clave = caData.current_clave ? String(caData.current_clave) : null;
  const bibliotecaN = caData.biblioteca_n != null ? Number(caData.biblioteca_n) : null;
  const total = d.cimatica_total != null ? Number(d.cimatica_total) : null;
  const edad = d.edad_s != null ? Number(d.edad_s) : null;
  const tono = (d.tono || {}) as Record<string, any>;
  const top = (d.cimatica_top || []) as Array<Record<string, any>>;

  const dists = Object.entries(tono.dist || {})
    .filter(([, v]) => v != null)
    .sort((a, b) => Number(a[1]) - Number(b[1]));

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica
          etiqueta="Patrones en DB"
          valor={total != null ? total.toLocaleString("es-MX") : "—"}
          contexto="tbl_cimatica_patrones · conteo de repetición"
        />
        <Metrica
          etiqueta="Biblioteca de figuras"
          valor={bibliotecaN != null ? bibliotecaN.toLocaleString("es-MX") : "—"}
          contexto="vísperas etiquetadas comparables"
          jerarquia="compacta"
        />
        <Metrica
          etiqueta="Tono espectral"
          valor={tono.tono ? String(tono.tono) : "—"}
          contexto={edad != null ? `ventana viva · frescura ${edad} s` : "ventana viva"}
          jerarquia="compacta"
        />
      </div>

      {/* Figura + tono */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          titulo="Figura cimática actual"
          meta="clave de telemetría → imagen determinista"
          nota="La misma clave SIEMPRE dibuja la misma figura — reconocible de reojo, como las placas de Chladni. Si la clave no cambia, la figura no cambia: es la semilla de la comparación contra la biblioteca. Color neutro a propósito: la figura es dato, no estado de riesgo."
        >
          <div className="flex flex-col items-center gap-4">
            <CimaticaFigura clave={clave} size={260} />
            {clave ? (
              <p className="mono break-all text-micro leading-relaxed text-muted">
                {clave.slice(0, 180)}
                {clave.length > 180 ? "…" : ""}
              </p>
            ) : (
              <p className="text-meta text-muted">
                Sin clave en el snapshot — esperando el próximo ciclo del launcher.
              </p>
            )}
          </div>
        </Panel>

        <Panel titulo="Tono espectral — la ventana viva" meta="capa espectral (tela SNT)" nota={NOTA_TONO}>
          <div className="space-y-4">
            <div className="flex items-baseline gap-2">
              <span className="etiqueta">Régimen actual</span>
              <span className="mono text-body font-semibold text-foreground">
                {tono.tono ? String(tono.tono) : "—"}
              </span>
            </div>
            {dists.length ? (
              <ul className="space-y-2">
                {dists.map(([f, v]) => (
                  <li key={f} className="flex items-baseline gap-3 text-meta">
                    <span className="mono w-24 shrink-0 text-muted">{f}</span>
                    <span className="mono font-semibold text-foreground">{Number(v).toFixed(2)}</span>
                    <span className="text-faint">distancia z</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-meta text-muted">Sin tono medido — centroides no construidos o ventana sin datos.</p>
            )}
          </div>
        </Panel>
      </div>

      {/* Top patrones */}
      <Panel
        titulo="Top patrones por frecuencia"
        meta={total != null ? `${total.toLocaleString("es-MX")} patrones en DB` : "tbl_cimatica_patrones"}
        nota="Un patrón frecuente NO es un patrón predictivo: la frecuencia mide repetición, no anticipación. Qué firma empareja eventos frente a calma lo mide el Juez (lift relativo), no este conteo."
      >
        {top.length ? (
          <>
            <SimpleBars
              data={top.slice(0, 8).map((p, i) => ({
                key: String(i),
                value: Number(p.frecuencia || 0),
                color: "var(--color-serie-1)",
                name: `${String(p.event_class || "—")} (${String(p.ambito || "—")})`,
              }))}
              xKey="key"
              yKey="value"
              bars={[{ key: "value", color: "var(--color-serie-1)", name: "frecuencia" }]}
              height={200}
              mostrarX
            />
            <ul className="mt-3 space-y-1.5">
              {top.slice(0, 8).map((p, i) => (
                <li key={i} className="flex items-baseline gap-2">
                  <span className="mono truncate text-body text-foreground">
                    {String(p.event_class || "—")} · {String(p.ambito || "—")}
                  </span>
                  <span className="mono ml-auto font-semibold text-foreground">
                    {Number(p.frecuencia || 0).toLocaleString("es-MX")}
                  </span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <SinDatos titulo="Sin patrones cimáticos" detalle="La tabla tbl_cimatica_patrones está vacía en este árbol." />
        )}
      </Panel>
    </div>
  );
}
