/**
 * PresentacionTab - Página de presentación de Sentinel Omega
 */
import { useCallback } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Panel, Metrica, SinDatos, BannerError } from "@/components/ui/data";

export function PresentacionTab() {
  const datosF = useCallback(() => api.estado(), []);
  const estado = usePoll(datosF, 30000);


  if (estado.error) return <BannerError mensaje={estado.error} />;
  if (estado.loading && !estado.data) return <SinDatos titulo="Cargando estado del sistema..." />;

  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center gap-4 py-4">
        <div className="flex items-center justify-center gap-2">
          <div className="w-14 h-12 rounded-full bg-indigo-500/20 flex items-center justify-center">
            <svg width="28" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-acento)" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m12.78 1.41l-1.41 1.41M12 20l-1.41-1.41L12 12l1.41 1.41" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="mono texto-micro texto-desvanecido tracking-wider uppercase">SENTINEL OMEGA</span>
            <h1 className="texto-2xl fuente-negrita texto-principal">Plataforma de Detección de Anomalías Multi-Dominio</h1>
            <div className="texto-meta texto-desvanecido">
              Autor: Elán Zainos Corona (Fractal Core Research)
            </div>
          </div>
        </div>

        <div className="prose texto-meta max-w-none text-leading-relaxed">
          <p className="texto-principal fuente-negrita texto-lg">
            Sentinel Omega es una plataforma de detección de anomalías naturales multi-dominio que monitoriza cuatro dominios principales: espacio, tierra, atmósfera y financiero.
          </p>
          <p className="mt-4 texto-meta texto-desvanecido">
            El sistema utiliza 8 bots especializados (alfa1, alfa2, beta1, beta2, delta, omega, padre, loki) que analizan señales de diferentes dominios para detectar anomalías y generar alertas mediante el consenso del Padre y el Juez.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Panel
          titulo="Dominios Monitoreados"
          meta="4"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-start gap-2">
              <span className="mono texto-principal fuente-negrita">🌌</span>
              <span>Espacio</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-micro texto-desvanecido">Bz, viento solar, Kp, protones</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="mono texto-principal fuente-negrita">🌍</span>
              <span>Tierra</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">🌤️</span>
              <span className="mono texto-micro texto-desvanecido">Atmósfera</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="mono texto-principal fuente-negrita">📈</span>
              <span className="mono texto-micro texto-desvanecido">Financiero</span>
            </div>
          </div>
        </Panel>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Metrica etiqueta="Firmas nuevas" valor="39.138" contexto="aprendidas en el último entrenamiento" />
        <Metrica etiqueta="Firmas recurrentes" valor="985.592" contexto="incrementos de repetición" />
        <Metrica etiqueta="Memoria consolidada" valor="22.963" contexto="patrones reconocidos" />
      </div>
    </div>
  );
}
