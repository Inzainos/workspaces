/**
 * PRINCIPAL — tablero general del sistema.
 *
 * Datos reales de /api/overview (contrato verificado contra :8787):
 *   fantasma{value, nivel_riesgo, kp, bz_nT, viento_km_s, schumann_*}
 *   muro{walls_active, muro_breach, correlation_score, risk_label}
 *   counts{nodos, sismos_m45} · risk_distribution · cycle_alert_rate · health
 */
import { useCallback } from "react";
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
  const ov = usePoll(ovF, 20000);

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

  const fantasma = f.value != null ? Number(f.value) : null;
  const nivel = nivelDe(f.nivel_riesgo ?? ciclo.nivel_riesgo);
  const kp = f.kp != null ? Number(f.kp) : null;
  const bz = f.bz_nT != null ? Number(f.bz_nT) : null;
  const viento = f.viento_km_s != null ? Number(f.viento_km_s) : null;
  const schAct = f.schumann_activity != null ? Number(f.schumann_activity) : null;

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
    </div>
  );
}
