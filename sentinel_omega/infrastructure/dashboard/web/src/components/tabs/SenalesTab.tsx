import { useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { LineSpark } from "@/components/charts/Sparkline";
import { Panel, Metrica, Cifra, SinDatos, esAusente } from "@/components/ui/data";

/**
 * SEÑALES — superficie MONITOR.
 *
 * Telemetría cruda por familia. Dos correcciones de fondo respecto de la
 * versión anterior:
 *
 *  - `Number(x ?? 0)` en las series. Ese patrón convertía «no tengo lectura»
 *    en un 0 perfectamente dibujable: la línea de Schumann caía a cero y
 *    parecía una medición real de 0 Hz. Es exactamente la regla dura 8 del
 *    proyecto (desconfía del default benigno). Ahora los nulos se FILTRAN de
 *    la serie y se dice cuántos faltaron.
 *  - La biblioteca cimática mostraba 0 cuando la tabla no existe. Ausente y
 *    vacía no son lo mismo y ya no se pintan igual.
 */
export function SenalesTab() {
  const sch = usePoll(useCallback(() => api.schumannVivo(120), []), 30000);
  const clima = usePoll(useCallback(() => api.climaEspacial(80), []), 30000);
  const delta = usePoll(useCallback(() => api.delta(80), []), 30000);
  const ci = usePoll(useCallback(() => api.cimatica(50), []), 40000);
  const ca = usePoll(useCallback(() => api.cimaticaAhora(), []), 40000);
  const salud = usePoll(useCallback(() => api.healthApis(), []), 60000);
  const tel = usePoll(useCallback(() => api.telemetry(), []), 30000);

  /** Serie sin inventar ceros: descarta nulos y reporta cuántos eran. */
  const serie = (filas: Record<string, unknown>[] | undefined, campo: string) => {
    const todas = filas || [];
    const pts = todas
      .map((r, i) => ({ i, v: r[campo] }))
      .filter((p) => !esAusente(p.v))
      .map((p) => ({ i: p.i, v: Number(p.v) }));
    return { pts, faltantes: todas.length - pts.length, total: todas.length };
  };

  const schS = serie(sch.data?.items, "schumann_hz");
  const climaItems = clima.data?.items || [];
  const bzS = serie(climaItems, "bz_promedio");
  const kpS = serie(climaItems, "kp_promedio");
  const deltaS = serie(delta.data?.delta, "composite_score");

  const schLatest = sch.data?.latest as Record<string, unknown> | undefined;
  const schEstado = String((salud.data?.beta1 as { status?: string } | undefined)?.status || "").toUpperCase();
  const schCongelado = schEstado === "CONGELADO";
  const schNota = (salud.data?.beta1 as { nota?: string } | undefined)?.nota;

  const caData = (ca.data || {}) as Record<string, unknown>;
  const bibliotecaPresente = caData.biblioteca_presente === true;

  const topPatrones = useMemo(
    () =>
      [...((ci.data?.items || []) as Record<string, unknown>[])]
        .sort((a, b) => Number(b.frecuencia) - Number(a.frecuencia))
        .slice(0, 6),
    [ci.data],
  );
  const maxFreq = Number(topPatrones[0]?.frecuencia ?? 1) || 1;

  return (
    <div className="space-y-5">
      {/* ---------- Schumann ---------- */}
      <Panel
        titulo="Beta-1 · Resonancia Schumann"
        meta="Tomsk · referencia 7.83 Hz"
        acento={schCongelado ? "HIGH" : undefined}
        nota={
          schCongelado
            ? "Esta fuente está sirviendo el mismo valor una y otra vez: la serie se refresca pero no mide. Mientras siga así, el precursor Schumann entra como NULL en el cálculo del Fantasma."
            : "El latido de referencia: el resto de señales se correlaciona contra él. Excitación >15 % suma confianza; >30 % con espectro Kp plano dispara WATCH."
        }
      >
        <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)]">
          <div>
            {schS.pts.length ? (
              <LineSpark
                data={schS.pts}
                xKey="i"
                yKey="v"
                height={130}
                color={schCongelado ? "var(--color-aviso)" : "var(--color-serie-1)"}
                referencias={[{ valor: 7.83, color: "var(--color-faint)", etiqueta: "7.83 ref" }]}
              />
            ) : (
              <SinDatos titulo="Sin serie Schumann viva" detalle="No hay lecturas válidas en la ventana." />
            )}
            {schCongelado && (
              <p className="mt-2 text-meta leading-snug" style={{ color: "var(--color-aviso)" }}>
                {schNota || "Serie plana: un solo valor repetido en toda la ventana."}
              </p>
            )}
          </div>
          <div className="space-y-3 lg:border-l lg:border-border lg:pl-5">
            <Metrica
              etiqueta="Frecuencia"
              valor={<Cifra valor={schLatest?.schumann_hz} digits={2} />}
              unidad="Hz"
              nivel={schCongelado ? "HIGH" : undefined}
              contexto={schCongelado ? "valor congelado, no medido" : "última lectura"}
            />
            <Metrica
              etiqueta="Excitación"
              jerarquia="compacta"
              valor={<Cifra valor={schLatest?.schumann_activity} digits={0} />}
              unidad="%"
            />
          </div>
        </div>
      </Panel>

      {/* ---------- Clima espacial + Delta ---------- */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          titulo="Alfa · Clima espacial"
          meta="NOAA SWPC"
          nota="Bz negativo (hacia el sur) abre la magnetósfera; Kp mide la tormenta geomagnética resultante."
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <div className="etiqueta">Bz (GSM)</div>
              <div className="mt-1.5">
                {bzS.pts.length ? (
                  <LineSpark
                    data={bzS.pts}
                    xKey="i"
                    yKey="v"
                    height={78}
                    color="var(--color-serie-2)"
                    referencias={[{ valor: 0, color: "var(--color-border-strong)" }]}
                  />
                ) : (
                  <p className="py-6 text-center text-meta text-faint">Sin lecturas</p>
                )}
              </div>
              {bzS.faltantes > 0 && (
                <p className="mt-1 text-micro text-faint">
                  {bzS.faltantes} de {bzS.total} sin dato (no se dibujan como cero)
                </p>
              )}
            </div>
            <div>
              <div className="etiqueta">Kp</div>
              <div className="mt-1.5">
                {kpS.pts.length ? (
                  <LineSpark data={kpS.pts} xKey="i" yKey="v" height={78} color="var(--color-serie-3)" dominio={[0, 9]} />
                ) : (
                  <p className="py-6 text-center text-meta text-faint">Sin lecturas</p>
                )}
              </div>
              {kpS.faltantes > 0 && (
                <p className="mt-1 text-micro text-faint">
                  {kpS.faltantes} de {kpS.total} sin dato
                </p>
              )}
            </div>
          </div>
        </Panel>

        <Panel
          titulo="Delta · Humor de los mercados"
          meta="BTC · VIX · tendencias"
          nota="El componente financiero entra como una señal precursora más, no como consejo de inversión. ALERT cuando el combinado supera 0.6."
        >
          <div className="etiqueta">Cross-coupling (composite)</div>
          <div className="mt-1.5">
            {deltaS.pts.length ? (
              <LineSpark
                data={deltaS.pts}
                xKey="i"
                yKey="v"
                height={130}
                color="var(--color-serie-1)"
                referencias={[{ valor: 0.6, color: "var(--color-aviso)", etiqueta: "0.6 alert" }]}
              />
            ) : (
              <SinDatos titulo="Sin serie delta" />
            )}
          </div>
          {deltaS.faltantes > 0 && (
            <p className="mt-1.5 text-micro text-faint">
              {deltaS.faltantes} de {deltaS.total} ciclos sin composite calculado
            </p>
          )}
        </Panel>
      </div>

      {/* ---------- Cimática ---------- */}
      <Panel
        titulo="Cimática — las formas del sistema"
        meta="tbl_cimatica_patrones"
        nota="Cada ciclo convierte el estado en una clave. Nueva → se guarda; repetida → +1 a su frecuencia. Si antecede a un evento real, se etiqueta con su clase. Un patrón frecuente no es un patrón predictivo: eso lo decide el Juez."
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Metrica
                etiqueta="Patrones en DB"
                valor={
                  ci.data?.total != null ? (
                    Number(ci.data.total).toLocaleString("es-MX")
                  ) : (
                    <span className="dato-ausente">—</span>
                  )
                }
              />
              <div>
                <div className="etiqueta">Biblioteca</div>
                {bibliotecaPresente ? (
                  <div className="mono mt-1 text-[length:var(--text-metric)] font-semibold text-foreground">
                    {Number(caData.biblioteca_n ?? 0).toLocaleString("es-MX")}
                  </div>
                ) : (
                  <div className="mt-1.5 text-meta leading-snug" style={{ color: "var(--color-aviso)" }}>
                    Tabla ausente en esta base — no es una biblioteca vacía.
                  </div>
                )}
              </div>
            </div>
            <div className="border-t border-border pt-3">
              <div className="etiqueta">Clave cimática actual</div>
              <p className="mono mt-1.5 break-all text-micro leading-relaxed text-muted">
                {String(caData.current_clave || "—")}
              </p>
            </div>
          </div>

          <div className="lg:border-l lg:border-border lg:pl-6">
            <div className="flex items-baseline justify-between">
              <span className="etiqueta">Patrones más vistos</span>
              <span className="etiqueta">frecuencia</span>
            </div>
            {topPatrones.length ? (
              <ul className="mt-3 space-y-2.5">
                {topPatrones.map((p, i) => (
                  <li key={i} className="grid grid-cols-[minmax(0,1fr)_72px_46px] items-center gap-2.5">
                    <span className="mono truncate text-micro text-body">
                      {p.nodo_nombre ? `${p.nodo_nombre} (Nodo ${p.id_nodo})` : (p.id_nodo ? `Nodo ${p.id_nodo}` : "gen")} · {String(p.event_class || "—")}
                    </span>
                    <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(Number(p.frecuencia) / maxFreq) * 100}%`,
                          background: "var(--color-serie-1)",
                        }}
                      />
                    </div>
                    <span className="mono text-right text-micro tabular-nums text-body">
                      {String(p.frecuencia)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-meta text-muted">Sin patrones cimáticos aún.</p>
            )}
          </div>
        </div>
      </Panel>

      {/* ---------- Alfa-2 Térmico (Sentinel-1/2 por precedente de zona) ---------- */}
      {(tel.data?.sources || []).map((src: any) => {
        if (src.id !== "copernicus") return null;
        const zones = src.processed?.value?.zones_with_anomalies || [];
        if (zones.length === 0) return null;
        return (
          <Panel
            key="alfa2-thermal"
            titulo="Alfa-2 · Anomalías térmicas por precedente de zona"
            meta="ESA Sentinel-1/2 · tbl_cobertura_satelital"
            nota="Alfa-2 detecta zonas donde la temperatura actual supera su PROPIO máximo histórico (no un z-score global). ≥1 zona → WATCH; ≥3 simultáneas → ALERT. Medido: 13 % de horas vivas no-neutral (2026-10-18)."
          >
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {zones.map((z: any, i: number) => (
                  <div
                    key={`${z.zona}-${i}`}
                    className="rounded-lg border bg-surface p-3"
                    style={{
                      borderColor: z.thermal_anomalies >= 3
                        ? "color-mix(in oklch, var(--color-critico) 40%, transparent)"
                        : "color-mix(in oklch, var(--color-aviso) 40%, transparent)",
                    }}
                  >
                    <div className="mono text-body font-semibold text-foreground">
                      {z.zona}
                    </div>
                    <div className="mt-1.5 grid grid-cols-2 gap-2 text-micro">
                      <span className="text-faint">Anomalías</span>
                      <span
                        className="mono text-right font-semibold"
                        style={{
                          color: z.thermal_anomalies >= 3
                            ? "var(--color-critico)"
                            : "var(--color-aviso)",
                        }}
                      >
                        {z.thermal_anomalies}
                      </span>
                      <span className="text-faint">Cobertura</span>
                      <span className="mono text-right text-body">
                        {Number(z.coverage_score).toFixed(2)}
                      </span>
                      <span className="text-faint col-span-2">Pases</span>
                      <span className="mono text-right text-body col-span-2">
                        {z.clear_passes} / {z.total_passes}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>
        );
      })}
    </div>
  );
}
