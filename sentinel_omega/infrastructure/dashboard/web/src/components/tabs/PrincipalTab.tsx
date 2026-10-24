/**
 * PRINCIPAL — tablero general del sistema.
 *
 * Datos reales de DOS endpoints verificados contra :8787:
 *   /api/overview → fantasma, muro, counts, risk_distribution, health
 *   /api/estado-vivo → GOES X-ray, térmico alfa2, señales con countdown,
 *                     Schumann-actividad, auditoría (ganancia)
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import {
  Panel,
  Metrica,
  Cifra,
  SinDatos,
  BannerError,
  TablaDatos,
  EscalaRiesgo,
  SegmentosMuro,
  nivelDe,
  colorNivel,
  accionNivel,
} from "@/components/ui/data";
import { fmtTs } from "@/lib/utils";

export function PrincipalTab() {
  const ovF = useCallback(() => api.overview(), []);
  const evF = useCallback(() => api.estadoVivo(), []);
  const ov = usePoll(ovF, 20000);
  const ev = usePoll(evF, 30000);

  // Countdown que se resta en vivo (tick client-side cada segundo)
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  if (ov.error) return <BannerError mensaje={ov.error} />;
  if (ov.loading && !ov.data) return <SinDatos titulo="Cargando estado del sistema…" />;

  const d: any = ov.data ?? {};
  const f: any = d.fantasma ?? {};
  const muro: any = d.muro ?? {};
  const ciclo: any = d.ciclo ?? {};
  const counts: any = d.counts ?? {};
  const risk: any = d.risk_distribution ?? {};
  const calert: any = d.cycle_alert_rate ?? {};
  const health: any = d.health ?? {};

  // estado-vivo: GOES, térmico, señales, Schumann-actividad, auditoría
  const evd: any = ev.data ?? {};
  const goesClase = evd.goes_clase ?? null;
  const goesFlux = evd.goes_flux_max_24h != null ? Number(evd.goes_flux_max_24h) : null;
  const termico = evd.termico ?? null;
  const senales: any[] = evd.senales ?? [];
  const telemetria: any = evd.telemetria ?? {};
  const schAct = telemetria.schumann_activity != null ? Number(telemetria.schumann_activity) : (f.schumann_activity != null ? Number(f.schumann_activity) : null);
  const auditoria: any = evd.auditoria ?? {};
  const ganancia = auditoria.ganancia != null ? Number(auditoria.ganancia) : null;
  const evTs = evd.ts != null ? Number(evd.ts) : Date.now() / 1000;

  const fantasma = f.value != null ? Number(f.value) : null;
  const nivel = nivelDe(f.nivel_riesgo ?? ciclo.nivel_riesgo);
  const kp = f.kp != null ? Number(f.kp) : null;
  const bz = f.bz_nT != null ? Number(f.bz_nT) : null;
  const viento = f.viento_km_s != null ? Number(f.viento_km_s) : null;

  const riesgoFilas = [
    { nivel: "CRITICAL", n: Number(risk.CRITICAL ?? 0) },
    { nivel: "HIGH", n: Number(risk.HIGH ?? 0) },
    { nivel: "MODERATE", n: Number(risk.MODERATE ?? 0) },
    { nivel: "LOW", n: Number(risk.LOW ?? 0) },
  ];

  return (
    <div className="space-y-5">
      <Panel
        titulo="Estado del sistema"
        meta={health.last_cycle_ts ? `último ciclo ${fmtTs(Number(health.last_cycle_ts))}` : "sin ciclo"}
        acento={nivel}
        nota="La frecuencia Schumann NO se mide desde el 2026-10-09; solo la actividad (intensidad del espectrograma de Tomsk). El hueco honesto se muestra como «sin medir», no como cero."
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
              {health.stale && (
                <span className="mono texto-micro texto-desvanecido" title={`edad ${health.stale_seconds}s`}>
                  · telemetría con rezago
                </span>
              )}
            </div>
            <EscalaRiesgo valor={fantasma} max={50} umbrales={[15, 30]} />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-1">
              <Metrica etiqueta="Kp" valor={<Cifra valor={kp} digits={2} />} />
              <Metrica etiqueta="Bz (nT)" valor={<Cifra valor={bz} digits={2} />} />
              <Metrica etiqueta="Viento solar" valor={<Cifra valor={viento} digits={0} unidad="km/s" />} />
              <Metrica
                etiqueta="Actividad Schumann"
                valor={<Cifra valor={schAct} digits={1} unidad="%" />}
                contexto={f.schumann_hz == null ? "Hz sin medir (retirado 2026-10-09)" : undefined}
              />
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="etiqueta">Muro de 5 Eventos</span>
              <div className="w-40">
                <SegmentosMuro
                  activos={muro.walls_active != null ? Number(muro.walls_active) : null}
                  total={5}
                  breach={Boolean(muro.muro_breach)}
                />
              </div>
              <span className="mono texto-micro texto-desvanecido">
                {muro.walls_active ?? "—"} de 5 · {muro.risk_label ?? "—"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Metrica
                etiqueta="Nodos vigilados"
                valor={counts.nodos != null ? String(counts.nodos) : "—"}
              />
              <Metrica
                etiqueta="Sismos M4.5+"
                valor={counts.sismos_m45 != null ? Number(counts.sismos_m45).toLocaleString("es-MX") : "—"}
              />
              <Metrica
                etiqueta="Ciclos con ALERT"
                valor={
                  calert.total_cycles
                    ? `${calert.alert_cycles} de ${Number(calert.total_cycles).toLocaleString("es-MX")}`
                    : "—"
                }
                contexto="tasa de alerta 0 % = el sistema no alarmó en vivo"
              />
              <Metrica
                etiqueta="Fantasma promedio"
                valor={<Cifra valor={calert.avg_fantasma} digits={2} />}
                contexto="promedio histórico de ciclos"
              />
            </div>
          </div>
        </div>
      </Panel>

      <Panel
        titulo="Distribución de riesgo — ciclos históricos"
        meta={`${riesgoFilas.reduce((a, r) => a + r.n, 0).toLocaleString("es-MX")} ciclos clasificados`}
      >
        <TablaDatos
          filas={riesgoFilas}
          densa
          vacío="Sin distribución"
          columnas={[
            {
              clave: "nivel",
              etiqueta: "Nivel",
              render: (r) => (
                <span className="mono texto-micro fuente-negrita" style={{ color: colorNivel(nivelDe(r.nivel)) }}>
                  {r.nivel}
                </span>
              ),
            },
            {
              clave: "n",
              etiqueta: "Ciclos",
              num: true,
              render: (r) => Number(r.n).toLocaleString("es-MX"),
            },
          ]}
        />
      </Panel>

      {/* GOES X-ray + Térmico Alfa-2 (sólo si hay algo que reportar) */}
      {(goesClase || (termico && termico.zonas > 0)) && (
        <div className="grid gap-5 lg:grid-cols-2">
          {goesClase && (
            <Panel
              titulo="GOES X-ray — Fulguración solar"
              meta={`clase ${goesClase}`}
              acento={goesClase === "X" ? "CRITICAL" : goesClase === "M" ? "HIGH" : undefined}
              nota="NOAA: M→WATCH, X→ALERT (desde 2026-10-18, el bot satelital alfa-2). Una fulguración M/X puede preceder una CME que llegue a la Tierra en 24–72 h."
            >
              <div className="flex items-center gap-4">
                <span
                  className="text-4xl font-bold"
                  style={{
                    color: goesClase === "X" ? "var(--color-critico)" : goesClase === "M" ? "var(--color-aviso)" : "var(--color-atencion)",
                  }}
                >
                  ☀️ {goesClase}
                </span>
                <div>
                  <div className="mono text-sm text-foreground">
                    flux máx 24 h: {goesFlux != null ? goesFlux.toExponential(1) : "—"} W/m²
                  </div>
                  <div className="text-xs text-muted">
                    {goesClase === "X" ? "ALERT — protocolo" : goesClase === "M" ? "WATCH — vigilancia" : "actividad normal"}
                  </div>
                </div>
              </div>
            </Panel>
          )}
          {termico && termico.zonas > 0 && (
            <Panel
              titulo="Alfa-2 · Térmico por precedente de zona"
              meta={`${termico.zonas} zona(s) sin precedente`}
              acento={termico.zonas >= 3 ? "CRITICAL" : "HIGH"}
              nota="Zona con temperatura actual por encima de su PROPIO máximo histórico. ≥1 zona → WATCH, ≥3 simultáneas → ALERT."
            >
              <div className="flex items-center gap-4">
                <span
                  className="text-3xl font-bold"
                  style={{ color: termico.zonas >= 3 ? "var(--color-critico)" : "var(--color-aviso)" }}
                >
                  🛰️ {termico.zonas}
                </span>
                <div className="text-sm text-muted">
                  zona(s) con anomalía térmica
                  <br />
                  máximo detectado: {termico.max ?? "—"}
                </div>
              </div>
            </Panel>
          )}
        </div>
      )}

      {/* Señales vivas con countdown */}
      {senales.length > 0 && (
        <Panel
          titulo="Señales vivas — firmas emparejadas con countdown"
          meta={`${senales.length} señal(es) · ancla en la primera detección continua`}
          nota="Cada tarjeta: sitio completo (nombre → nodo → coords), el evento que su firma suele preceder, y el LAG restante restándose en vivo desde el ancla del padre. «Sin lag medido» = la firma nunca demostró anticipar."
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {senales.map((s: any, i: number) => {
              const restH =
                s.lag_restante_h != null
                  ? Number(s.lag_restante_h) - (now / 1000 - evTs) / 3600
                  : null;
              const colorLag =
                restH == null || restH <= 0
                  ? "var(--color-faint)"
                  : restH < 24
                    ? "var(--color-aviso)"
                    : restH < 72
                      ? "var(--color-atencion)"
                      : "var(--color-calma)";
              return (
                <div
                  key={`${s.id_nodo}-${s.evento}-${i}`}
                  className="relative overflow-hidden rounded-lg border bg-surface p-3 pl-4"
                  style={{
                    borderColor:
                      restH != null && restH > 0 && restH < 24
                        ? "color-mix(in oklch, var(--color-aviso) 40%, var(--color-border))"
                        : "var(--color-border)",
                  }}
                >
                  <span
                    className="absolute inset-y-0 left-0 w-[3px]"
                    style={{ background: colorLag }}
                    aria-hidden="true"
                  />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-foreground" title={s.sitio}>
                      {s.sitio}
                    </div>
                    <div className="mt-0.5 flex items-baseline gap-2">
                      <span className="mono text-[0.7rem] font-bold uppercase tracking-wider text-muted">
                        {s.evento}
                      </span>
                      <span className="text-[0.7rem] text-faint tnum">
                        parecido <Cifra valor={s.similitud} digits={2} /> · visto{" "}
                        {s.recurrencia != null ? `${s.recurrencia}×` : "—"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      {restH != null ? (
                        <>
                          <span className="mono text-lg font-bold tnum" style={{ color: colorLag }}>
                            ~{Math.round(restH)} h
                          </span>
                          <span className="text-[0.7rem] text-faint">
                            ({(restH / 24).toFixed(1)} d)
                          </span>
                        </>
                      ) : (
                        <span className="text-sm italic text-faint">
                          sin lag medido — no demostró anticipar
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* Auditoría: la vara honesta */}
      {ganancia != null && (
        <Panel
          titulo="¿El sistema aporta información?"
          meta="fase viva · lagging"
          nota="La asertividad cuenta como acierto cada silencio en calma (y la calma es casi todo). La ganancia compara la precisión de la alarma contra la tasa base: 1× significa que alertar siempre habría dado lo mismo. Nunca se muestran solas."
        >
          <div className="grid gap-4 md:grid-cols-4">
            <Metrica
              etiqueta="Ganancia sobre alertar a ciegas"
              valor={`${ganancia.toFixed(2)}×`}
              contexto="1× = no aporta"
              nivel={ganancia > 1 ? "LOW" : "HIGH"}
            />
            <Metrica
              etiqueta="Aciertos (viva)"
              valor={auditoria.aciertos != null ? Number(auditoria.aciertos).toLocaleString("es-MX") : "—"}
              contexto="incluye silencios en calma"
              jerarquia="compacta"
            />
            <Metrica
              etiqueta="Falsas alarmas (viva)"
              valor={auditoria.falsos_positivos != null ? Number(auditoria.falsos_positivos).toLocaleString("es-MX") : "—"}
              contexto="avisó y no pasó nada"
              jerarquia="compacta"
            />
            <Metrica
              etiqueta="Omisiones (viva)"
              valor={auditoria.fallos != null ? Number(auditoria.fallos).toLocaleString("es-MX") : "—"}
              contexto="pasó algo y no avisó — pesa 10×"
              jerarquia="compacta"
            />
          </div>
        </Panel>
      )}
    </div>
  );
}
