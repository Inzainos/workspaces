/**
 * CIMÁTICA — superficie MONITOR.
 *
 * Panel de vibración: visualización de la firma actual de la cimática
 * y los patrones recurrentes más frecuentes.
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, Cifra, SinDatos, BannerError } from "@/components/ui/data";
import { CimaticaFigura } from "@/components/CimaticaFigura";
import { SimpleBars } from "@/components/charts/componentes";

export function CimaticaTab() {
  const evF = useCallback(() => api.estadoVivo(), []);
  const ev = usePoll(evF, 30000);

  const d = (ev.data as any) ?? {};
  const cimatica = d?.cimatica_top || [];
  const total = d?.cimatica_total ?? 0;
  const edad = d?.edad_s != null ? Number(d.edad_s) : null;
  const edadStr = edad != null ? `${edad} s` : "—";

  const top = cimatica.slice(0, 8);

  const notaFigura =
    "La misma clave siempre dibuja la misma figura. Si la clave no cambia, la figura no cambia: es determinista, no aleatoria. Los anillos concéntricos y el espejo vertical imitan las placas de Chladni; el tamaño del punto y el grosor de la línea son puramente geométricos, no representan riesgo. Sin clave actual no hay firma que observar (esperando al siguiente ciclo).";

  const notaTop =
    "Un patrón frecuente no es un patrón predictivo: lo que importa es si empareja eventos reales frente a calma (la vara del Padre). La frecuencia mide repetición, no anticipación.";

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica
          detalle="Patrones en DB"
          objetivo={total.toLocaleString("es-MX")}
          riesgo={total > 1000 ? "MEDIO" : "BAJO"}
          acción="revisar cimática"
        />
        <Metrica
          detalle="Top hoy"
          objetivo={top.length.toString()}
          riesgo="BAJO"
          acción="ver lista"
        />
        <Metrica
          detalle="Clave actual"
          objetivo="—"
          riesgo="BAJO"
          acción="esperar ciclo"
        />
      </div>

      {/* Firma cimática */}
      <Panel
        detalle="Firma cimática actual"
        objetivo={edadStr}
        riesgo="BAJO"
        acción="refrescar"
      >
        <div className="flex flex-col items-center gap-4">
          <CimaticaFigura clave="" tamaño={260} />
          <p className="texto-meta texto-desvanecido">
            La clave actual no está disponible en el estado vivo. El snapshot y las frecuencias de patrones siguen mostrándose abajo.
          </p>
        </div>
      </Panel>

      {/* Top patrones */}
      <Panel
        detalle="Top patrones (frecuencia)"
        objetivo={`total ${total.toLocaleString("es-MX")}`}
        riesgo="BAJO"
        acción="revisar patrón"
      >
        {top.length ? (
          <div className="space-y-3">
            <SimpleBars
              datos={top.map((p, i) => ({
                clave: String(i),
                valor: Number(p.frecuencia || 0),
                color: "var(--color-serie-1)",
                nombre: `${String(p.event_class || "—")} (${String(p.ambito || "—")})`,
              }))}
              claveClave="clave"
              valorClave="valor"
              altura={260}
              tipo="barra"
            />
            <div className="mt-3 espacio-y-1.5">
              {top.map((p, i) => (
                <div key={i} className="flex items-baseline gap-2">
                  <span className="mono texto-principal fuente-negrita">
                    {String(p.event_class || "—")} ({String(p.ambito || "—")})
                  </span>
                  <span className="mono texto-principal fuente-negrita">
                    {Number(p.frecuencia).toLocaleString("es-MX")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
            <SinDatos título="Sin patrones cimáticos" detalle="La tabla tbl_cimatica_patrones está vacía." />
          )}
        </Panel>

        {/* Nota */}
        <div className="redondeado-lg borde borde-desgastado bg-superficie-penumbra p-4">
          <p className="texto-meta texto-desvanecido">
            Nota: El patrón más frecuente no es necesariamente el más preditivo. Lo que importa es si empareja eventos reales frente a calma (la vara del Padre). La frecuencia mide repetición, no anticipación.
          </p>
        </div>
      </div>
  );
}
