import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { DataTable } from "@/components/DataTable";
import { LineSpark, SimpleBars } from "@/components/charts/Sparkline";
import {
  Panel,
  Metrica,
  Cifra,
  BarraVeredictos,
  SinDatos,
  BannerError,
} from "@/components/ui/data";
import { fmtNum, fmtTs } from "@/lib/utils";

function pct(v: unknown, dig = 1) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(dig)}%`;
}

/**
 * MODELOS — superficie COMPARE.
 *
 * Aquí el usuario pesa nueve bots unos contra otros, así que la composición
 * es tabular y alineada: misma métrica, misma columna, mismo formato. Lo que
 * cambió respecto de la versión anterior:
 *
 *  - Se reemplazó el muro de nueve sparklines idénticas apiladas (una por
 *    bot, todas del mismo tamaño, imposibles de comparar entre sí) por una
 *    sola rejilla con eje común. Nueve gráficas iguales no son comparación,
 *    son repetición.
 *  - El MÉRITO pasa al frente. El peso de disciplina satura en 1.425 y deja
 *    de informar —cuatro bots empatados en el techo—, mientras el mérito sí
 *    discrimina porque paga los errores en la moneda del Juez.
 *  - Se añadió la barra de veredictos con falsos positivos incluidos, que es
 *    lo que la asertividad esconde.
 */
export function ModelosTab() {
  const bots = usePoll(useCallback(() => api.bots(), []), 30000);
  const sesgo = usePoll(useCallback(() => api.sesgo(), []), 60000);
  const learn = usePoll(useCallback(() => api.aprendizaje(), []), 60000);
  const firmas = usePoll(useCallback(() => api.firmas(), []), 60000);
  const ac = usePoll(useCallback(() => api.aciertos(200), []), 30000);
  const juez = usePoll(useCallback(() => api.juez(200, "viva"), []), 20000);
  const modelos = usePoll(useCallback(() => api.modelos(), []), 60000);

  if (bots.error) return <BannerError mensaje={bots.error} />;
  if (bots.loading && !bots.data) return <SinDatos titulo="Leyendo pesos y veredictos…" />;

  const b = bots.data as Record<string, unknown> | undefined;
  const items = (b?.items as Record<string, unknown>[]) || [];
  const sesgoItems = (sesgo.data?.items as Record<string, unknown>[]) || [];

  const insampleByBot: Record<string, number> = {};
  for (const r of sesgoItems) {
    const nm = String(r.bot || "");
    if (nm) insampleByBot[nm] = Number(r.recon_insample || 0);
  }

  const individual = (r: Record<string, unknown>) => {
    const a = Number(r.aciertos || 0);
    const f = Number(r.fallos || 0);
    return a + f > 0 ? a / (a + f) : null;
  };

  const series = learn.data?.series || {};
  const botsNames = Object.keys(series);
  const merged: Record<string, unknown>[] = [];
  if (botsNames.length) {
    const days = Array.from(new Set(botsNames.flatMap((n) => series[n].map((p) => p.dia)))).sort();
    for (const d of days) {
      const row: Record<string, unknown> = { dia: d };
      for (const nm of botsNames) {
        const pt = series[nm].find((p) => p.dia === d);
        row[nm] = pt?.asertividad_cum != null ? Number(pt.asertividad_cum) * 100 : null;
      }
      merged.push(row);
    }
  }

  const recent = (ac.data?.recent as Record<string, unknown>[]) || (juez.data?.items || []);
  const topAcierto = recent.filter((r) => String(r.resultado || "").toUpperCase() === "ACIERTO").slice(0, 5);
  const topFallo = recent.filter((r) => String(r.resultado || "").toUpperCase() === "FALLO").slice(0, 5);
  const byClase = (Array.isArray(firmas.data?.by_clase) ? firmas.data?.by_clase : []) as Record<string, unknown>[];

  // Universos distintos, y se rotulan como tales: `aciertos_total` es la suma
  // POR BOT (cada ventana contada una vez por cada bot que opinó), mientras
  // que `veredictos_sistema` son los veredictos del sistema en viva_real. Se
  // enseñan por separado; mezclarlos en una proporción da una barra falsa.
  const vs = (b?.veredictos_sistema || {}) as {
    aciertos?: number;
    falsos_positivos?: number;
    fallos?: number;
  };
  const sysA = Number(vs.aciertos ?? 0);
  const sysFP = Number(vs.falsos_positivos ?? 0);
  const sysF = Number(vs.fallos ?? 0);
  const hayVeredictos = sysA + sysFP + sysF > 0;
  const sumaBotsA = Number(b?.aciertos_total ?? 0);
  const sumaBotsF = Number(b?.fallos_total ?? 0);
  const ganancia = b?.ganancia_real != null ? Number(b.ganancia_real) : null;
  const conMerito = items.filter((r) => r.merito != null);
  // Mismo patrón que `vs` arriba: `api.bots()` devuelve
  // `Record<string, unknown>`, así que un objeto anidado hay que tiparlo al
  // leerlo o no se puede indexar.
  const voto = (b?.voto || {}) as {
    disponible?: boolean;
    por_merito_pedido?: boolean;
    meritos_aplicados?: number;
    competencias_aplicadas?: number;
    minimo_ventanas?: number;
    origen?: string;
  };

  return (
    <div className="space-y-5">
      {/* ---------- Resumen del consejo ---------- */}
      <Panel
        titulo="Rendimiento del consejo"
        meta="fase viva · en_vivo=1"
        nota="La asertividad global cuenta los silencios en calma y excluye las falsas alarmas del denominador; por eso va acompañada siempre de la ganancia y de la proporción real de veredictos."
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
          <div className="grid grid-cols-2 gap-4">
            <Metrica
              etiqueta="Asertividad viva"
              valor={pct(b?.asertividad_viva_global)}
              contexto="cuenta los silencios"
            />
            <Metrica
              etiqueta="Ganancia real"
              valor={ganancia != null ? `${ganancia.toFixed(2)}×` : "—"}
              nivel={ganancia == null ? "DESCONOCIDO" : ganancia > 1 ? "LOW" : "HIGH"}
              contexto="1× = no aporta"
            />
            <Metrica
              etiqueta="Viva del Padre"
              jerarquia="compacta"
              valor={pct((b?.padre as Record<string, unknown> | undefined)?.asertividad_viva_individual)}
              contexto="el único que puede avisar"
            />
            <Metrica
              etiqueta="Bot mudo"
              jerarquia="compacta"
              valor={pct(b?.asertividad_bot_mudo)}
              contexto="callarse siempre da esto"
            />
          </div>
          <div className="space-y-3 lg:border-l lg:border-border lg:pl-6">
            <span className="etiqueta">Reparto real de veredictos · viva_real</span>
            {hayVeredictos ? (
              <BarraVeredictos aciertos={sysA} falsosPositivos={sysFP} fallos={sysF} />
            ) : (
              <p className="text-meta text-muted">Sin veredictos resueltos.</p>
            )}
            <p className="border-t border-border pt-3 text-meta leading-relaxed text-muted">
              Suma por bot (TBL_PESOS_BOTS):{" "}
              <span className="mono text-body">{sumaBotsA.toLocaleString("es-MX")}</span> aciertos y{" "}
              <span className="mono text-body">{sumaBotsF.toLocaleString("es-MX")}</span> fallos. Es
              otro universo — cada ventana se cuenta una vez por cada bot que opinó — así que no se
              mezcla con la barra de arriba.
            </p>
          </div>
        </div>
      </Panel>

      {/* ---------- Mérito: el diferenciador ---------- */}
      {/* Cuando no hay mérito, el panel YA NO desaparece. Antes se ocultaba
          entero con `conMerito.length ? ... : null`, así que el tablero se veía
          igual con mérito medido y sin medirlo — y lleva sin medirse desde
          siempre, porque pide ≥50 ventanas de fase viva y hay 36. Es la regla 3
          del diseño: lo que no se midió tiene que verse distinto. */}
      <Panel
        titulo="Mérito contra el silencio"
        meta={conMerito.length ? "1.00 = no aporta nada" : "sin evidencia todavía"}
        nota="Cada bot paga sus errores en la moneda del Juez (omitir ×10, falsa alarma ×1) y se compara con lo que habría pagado callándose. Esta métrica discrimina donde el peso de disciplina ya no: el peso satura en su techo y varios bots quedan empatados arriba sin que eso signifique que sean iguales."
      >
        {conMerito.length ? (
          <SimpleBars
            data={conMerito.map((r) => ({ bot: r.bot_name, merito: Number(r.merito) }))}
            xKey="bot"
            bars={[{ key: "merito", color: "var(--color-serie-1)", name: "mérito" }]}
            height={180}
            mostrarX
          />
        ) : (
          <div className="text-sm text-muted space-y-1">
            <div className="dato-ausente">— sin mérito calculado para ningún bot</div>
            <div>
              Hace falta evidencia de la fase viva:{" "}
              <b className="text-body">
                ≥ {Number(voto.minimo_ventanas ?? 50)} ventanas por bot
              </b>
              {voto.meritos_aplicados != null ? (
                <> · aplicados ahora: <b className="text-body">{Number(voto.meritos_aplicados)}</b></>
              ) : null}
              . Hasta entonces el voto sale de{" "}
              <b className="text-body">{String(voto.origen ?? "el marcador almacenado")}</b>.
            </div>
            {b?.merito_error ? (
              <div className="text-riesgo-alto">Fallo al calcularlo: {String(b.merito_error)}</div>
            ) : null}
          </div>
        )}
      </Panel>

      {/* ---------- Tabla comparativa ---------- */}
      <Panel
        titulo="Los nueve, lado a lado"
        meta="TBL_PESOS_BOTS · snapshot"
        nota={
          <>
            <b className="text-body">Peso</b> es el MARCADOR (paseo multiplicativo, saturado
            arriba) y <b className="text-body">Voto</b> lo que el Padre aplica de verdad: si
            coinciden, el mérito no se pudo calcular y el voto cayó al marcador ·{" "}
            <b className="text-body">Exigibles</b> son las firmas consolidadas que emparejan
            eventos MÁS que calma, de las consolidadas totales ·{" "}
            <b className="text-body">Individual</b> es su propia tasa de acierto ·{" "}
            <b className="text-body">Histórica</b> el in-sample del entrenamiento ·{" "}
            <b className="text-body">Viva</b> lo verificado contra la realidad, que es la que cuenta.
            Los notificadores (alfa2) operan sin peso: avisan, no votan.
          </>
        }
      >
        <DataTable
          rows={items}
          pageSize={12}
          columns={[
            { key: "bot_name", label: "Bot" },
            { key: "peso", label: "Peso", num: true, render: (r) => <Cifra valor={r.peso} digits={3} /> },
            {
              key: "peso_voto",
              label: "Voto",
              num: true,
              render: (r) => <Cifra valor={r.peso_voto} digits={3} />,
            },
            { key: "merito", label: "Mérito", num: true, render: (r) => <Cifra valor={r.merito} digits={2} /> },
            {
              key: "firmas_exigibles",
              label: "Exigibles",
              num: true,
              render: (r) =>
                r.firmas_consolidadas == null ? (
                  <Cifra valor={null} />
                ) : (
                  <span className="tnum">
                    <Cifra valor={r.firmas_exigibles} digits={0} />
                    <span className="text-muted"> / {Number(r.firmas_consolidadas).toLocaleString("es-MX")}</span>
                  </span>
                ),
            },
            { key: "aciertos", label: "Aciertos", num: true, render: (r) => <Cifra valor={r.aciertos} digits={0} /> },
            { key: "fallos", label: "Fallos", num: true, render: (r) => <Cifra valor={r.fallos} digits={0} /> },
            { key: "individual", label: "Individual", num: true, render: (r) => pct(individual(r)) },
            { key: "historica", label: "Histórica", num: true, render: (r) => pct(insampleByBot[String(r.bot_name)]) },
            {
              key: "asertividad_viva_individual",
              label: "Viva",
              num: true,
              render: (r) => pct(r.asertividad_viva_individual),
            },
          ]}
        />
      </Panel>

      {/* ---------- La compuerta de habilidad de los ONNX ---------- */}
      {/* Hasta el 2026-10-08 ninguna superficie decía si un modelo pasó la
          compuerta: el digesto de Telegram ponía ✅ por `os.path.exists` y el
          tablero no lo mencionaba. Tres estados DISTINTOS, y por eso tres
          colores: aprobado, negado, y SIN MEDIR --- que no es ninguno de los
          dos (regla de diseño 3). */}
      <Panel
        titulo="Compuerta de habilidad (ONNX)"
        meta={
          modelos.data?.medido_at
            ? `models_meta.json · medido ${String(modelos.data.medido_at).slice(0, 10)}`
            : "models_meta.json"
        }
        nota={
          <>
            <b className="text-body">AUC</b> es la habilidad medida fuera de muestra y{" "}
            <b className="text-body">Ganancia</b> lo que añade sobre el modelo nulo por nodo
            (la propia historia sísmica del nodo). Un <b className="text-body">.onnx</b> en
            disco no es un modelo que acierte: «sin medir» significa que su AUC nunca se
            calculó, no que esté bien. {modelos.data?.nota || ""}
          </>
        }
      >
        {modelos.error ? (
          <BannerError mensaje={modelos.error} />
        ) : !modelos.data?.modelos?.length ? (
          <SinDatos titulo="Sin metadato de modelos" />
        ) : (
          <DataTable
            rows={modelos.data.modelos as unknown as Record<string, unknown>[]}
            pageSize={9}
            columns={[
              { key: "bot", label: "Bot" },
              {
                key: "estado",
                label: "Estado",
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
              { key: "auc", label: "AUC", num: true, render: (r) => <Cifra valor={r.auc} digits={3} /> },
              {
                key: "ganancia_sobre_nulo",
                label: "Ganancia",
                num: true,
                render: (r) => <Cifra valor={r.ganancia_sobre_nulo} digits={3} />,
              },
              { key: "n", label: "Muestras", num: true, render: (r) => <Cifra valor={r.n} digits={0} /> },
              {
                key: "kb",
                label: "Tamaño",
                num: true,
                render: (r) => (r.kb == null ? <Cifra valor={null} /> : `${r.kb} KB`),
              },
              {
                key: "mtime",
                label: "Escrito",
                render: (r) => (r.mtime ? String(r.mtime).slice(0, 10) : <Cifra valor={null} />),
              },
              {
                key: "motivo",
                label: "Motivo",
                render: (r) =>
                  r.motivo ? (
                    <span className="text-muted">{String(r.motivo).slice(0, 90)}</span>
                  ) : (
                    <span className="text-muted">—</span>
                  ),
              },
            ]}
          />
        )}
      </Panel>

      {/* ---------- Sesgo ---------- */}
      <Panel
        titulo="Reconocimiento, falsa alarma y GANANCIA"
        meta="tbl_sesgo_aprendizaje"
        nota={
          <>
            <b className="text-body">Causal</b> son los eventos que su memoria reconoce;{" "}
            <b className="text-body">f.alarma</b>, cuánta CALMA empareja igual. La{" "}
            <b className="text-body">ganancia</b> es la resta, y es el número que decide:
            reconocer el 95 % emparejando el 94,5 % es ganancia 0,005, o sea alarmismo, no
            aprendizaje. El <b className="text-body">sesgo</b> (in-sample − causal) solo mide
            memorización, y era lo único que se mostraba aquí hasta el 2026-10-07.
          </>
        }
      >
        {sesgoItems.length ? (
          <>
            <SimpleBars
              data={sesgoItems.map((r) => ({
                bot: r.bot,
                causal: r.recon_causal == null ? null : Number(r.recon_causal) * 100,
                falsa: r.falsa_alarma == null ? null : Number(r.falsa_alarma) * 100,
              }))}
              xKey="bot"
              bars={[
                { key: "causal", color: "var(--color-serie-1)", name: "reconoce eventos" },
                { key: "falsa", color: "var(--color-serie-3)", name: "empareja calma" },
              ]}
              height={180}
              mostrarX
            />
            <div className="mt-4">
              <DataTable
                rows={sesgoItems}
                densa
                empty="Sin sesgo"
                columns={[
                  { key: "bot", label: "Bot" },
                  { key: "n", label: "n", num: true },
                  { key: "recon_insample", label: "In-sample", num: true, render: (r) => fmtNum(r.recon_insample) },
                  { key: "recon_causal", label: "Causal", num: true, render: (r) => fmtNum(r.recon_causal) },
                  {
                    key: "falsa_alarma",
                    label: "f.alarma",
                    num: true,
                    render: (r) => fmtNum(r.falsa_alarma),
                  },
                  {
                    key: "ganancia",
                    label: "Ganancia",
                    num: true,
                    // Saturado = riesgo, y una ganancia que no despega ES el
                    // riesgo: significa que el reconocimiento alto no es
                    // aprendizaje. Es el unico color de esta tabla.
                    render: (r) =>
                      r.ganancia == null ? (
                        <Cifra valor={null} />
                      ) : (
                        <b className={Number(r.ganancia) <= 0.02 ? "text-riesgo-alto" : "text-body"}>
                          {fmtNum(r.ganancia)}
                        </b>
                      ),
                  },
                  {
                    key: "castigos",
                    label: "Castigos",
                    num: true,
                    render: (r) => <Cifra valor={r.castigos} digits={0} />,
                  },
                  { key: "sesgo", label: "Sesgo", num: true, render: (r) => fmtNum(r.sesgo) },
                ]}
              />
            </div>
          </>
        ) : (
          <SinDatos titulo="Sin tbl_sesgo_aprendizaje" detalle="En DEV a menudo no está la tabla de entrenamiento." />
        )}
      </Panel>

      {/* ---------- Curvas ---------- */}
      <Panel
        titulo="Curvas de aprendizaje"
        meta={String(learn.data?.source || "Juez viva, diaria")}
        nota={learn.data?.caption || "Serie real diaria, sin interpolar."}
      >
        {learn.data?.present && merged.length ? (
          <div className="grid gap-x-6 gap-y-5 md:grid-cols-2 xl:grid-cols-3">
            {botsNames.map((name) => {
              const pts = merged.map((r) => ({ dia: r.dia, y: r[name] })).filter((p) => p.y != null);
              const ult = pts.length ? Number(pts[pts.length - 1].y) : null;
              return (
                <div key={name}>
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-meta font-semibold text-foreground">{name}</span>
                    <span className="mono text-meta text-muted">
                      {ult != null ? `${ult.toFixed(1)}%` : "—"}
                    </span>
                  </div>
                  <div className="mt-1">
                    {pts.length ? (
                      <LineSpark
                        data={pts}
                        xKey="dia"
                        yKey="y"
                        height={92}
                        color="var(--color-serie-1)"
                        dominio={[0, 100]}
                      />
                    ) : (
                      <p className="py-6 text-center text-micro text-faint">sin días</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <SinDatos titulo="Sin historial diario aún" detalle="Aparece cuando la fase viva acumule días." />
        )}
      </Panel>

      {/* ---------- Firmas ---------- */}
      {byClase.length ? (
        <Panel
          titulo="Firmas por clase de evento"
          meta="TBL_FIRMAS"
          nota="Sólo las firmas consolidadas son exigibles; las nuevas y observadas están todavía en periodo de prueba."
        >
          <SimpleBars
            data={byClase.map((r) => ({ name: r.clase, n: r.n }))}
            xKey="name"
            bars={[{ key: "n", color: "var(--color-serie-1)", name: "firmas" }]}
            height={170}
            mostrarX
          />
        </Panel>
      ) : null}

      {/* ---------- Veredictos recientes ---------- */}
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel titulo="Aciertos recientes" meta="top 5">
          <DataTable
            rows={topAcierto}
            densa
            pageSize={5}
            empty="Sin ACIERTO en la ventana reciente"
            columns={[
              { key: "timestamp", label: "Cuándo", render: (r) => fmtTs(r.timestamp) },
              { key: "bot_name", label: "Bot" },
              { key: "prediccion", label: "Predicción" },
              { key: "confianza", label: "Conf.", num: true, render: (r) => <Cifra valor={r.confianza} digits={2} /> },
            ]}
          />
        </Panel>
        <Panel titulo="Fallos recientes" meta="top 5 · pesan 10×">
          <DataTable
            rows={topFallo}
            densa
            pageSize={5}
            empty="Sin FALLO en la ventana reciente"
            columns={[
              { key: "timestamp", label: "Cuándo", render: (r) => fmtTs(r.timestamp) },
              { key: "bot_name", label: "Bot" },
              { key: "prediccion", label: "Predicción" },
              { key: "confianza", label: "Conf.", num: true, render: (r) => <Cifra valor={r.confianza} digits={2} /> },
            ]}
          />
        </Panel>
      </div>

      {/* ---------- ONNX ---------- */}
      <div className="rounded-lg border border-dashed border-border bg-surface-sunken/40 px-4 py-4">
        <div className="text-body font-semibold text-foreground">ONNX — sin métricas persistidas</div>
        <p className="mt-2 max-w-[80ch] text-meta leading-relaxed text-muted">
          Hay código en <span className="mono">core/onnx_engine.py</span> y{" "}
          <span className="mono">models/train_onnx_from_db.py</span>, pero ninguna tabla SQLite guarda
          métricas de entrenamiento (loss, AUC, ruta del .onnx). Cuando se persistan, aparecerán aquí
          citando su tabla. No se dibujan curvas inventadas para llenar el hueco.
        </p>
      </div>
    </div>
  );
}
