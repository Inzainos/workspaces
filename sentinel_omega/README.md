# Sentinel Omega — Plataforma de Detección de Anomalías Multi-Dominio

**Pivote estratégico (2026-10-11, GO del operador):** el proyecto pasa de
"predecir sismos vía Schumann" a **"detectar y caracterizar anomalías
naturales en cuatro dominios: espacio, tierra, atmósfera y financiero"**.

## Qué hace (verificado con medición)

| Dominio | Qué detecta | Sensores | Estado |
|---|---|---|---|
| **Espacio** | Tormentas geomagnéticas (Kp≥5), grietas de escudo (Bz≤−10), viento solar extremo, lluvia de protones | NOAA SWPC, OMNI2 (30 años), GOES X-ray | **8.439 tormentas en historia · scanner vivo · 429 firmas Kp6** |
| **Tierra** | Enjambres sísmicos, sismicidad por nodo, actividad volcánica (SO2, VEI) | USGS FDSN, NASA MSVOLSO2L4 | **2 enjambres activos ahora · 756+223 firmas de erupciones** |
| **Atmósfera** | Presión anómala, niebla, química atmosférica (CO/SO2) | OpenWeatherMap (4 estaciones + 6 volcanes) | **Vivo cada ciclo** |
| **Financiero** | Estrés de mercado (VIX, FGI, volatilidad BTC) | Yahoo Finance, CoinGecko, Binance | **Vivo cada ciclo** |

## Qué NO hace (medido, no especulado)

- **NO predice sismos M4.5+ vía Schumann**: hipótesis central medida y
  cerrada en negativo en DOS estaciones independientes (Granada 2013-2017,
  Eskdalemuir 2025) — bitácoras 2026-10-09 §2 y 2026-10-11 §1-4.
- **NO tiene modelos ONNX aprobados**: la compuerta de habilidad negó a los
  siete (AUC ~0,5 vs nulo-por-nodo 0,899 — "dicen QUÉ nodo, no CUÁNDO").
- **NO mide la frecuencia Schumann en vivo**: retirada el 2026-10-09; solo
  la ACTIVIDAD (intensidad WPC de Tomsk).

## Lo que está listo para un experimento dirigido (Opción A)

La infraestructura de medición está construida y probada:

```
hipótesis nueva → deploy/medir_schumann_precursor.py como plantilla
  → barrido de ventana (24-336 h) + semillas (11) + controles de época
  → calibración con el modelo nulo al lado
  → respuesta honesta (aunque sea negativa)
```

Candidatos con física más plausible que Schumann para precursores sísmicos:
radón, resistividad eléctrica, migración de enjambres, cambios de
velocidad Vp/Vs.

## Arquitectura (9 bots + Padre + Juez, con lo muerto documentado)

Vivos:
- `alfa1` (espacio: Bz, Kp, viento, protones) — votante
- `beta1` (cimático: espectro Kp + actividad Schumann) — votante
- `beta2` (atmosférico: presión, química, niebla) — votante
- `delta` (financiero: VIX, FGI, BTC, tendencias — contexto, techo WATCH) — votante
- `omega` (ritmo cósmico: luna, Schumann-actividad, acoplamientos) — votante
- `padre` (consenso jerárquico con corroboración por familia) — árbitro
- `alfa2` (satélites: térmico por precedente + rayos X GOES clase M/X) — votante
- `loki` (fractal-bayesiano) — **rutas muertas por construcción** (documentado)

Retirados (medido, no especulado):
- `jupiter` (atención colectiva) — **fuera desde 2026-10-18**: 0 alertas en
  168 ciclos, 0 exigibles, kp redundante con alfa1; xray→alfa2, trends→delta

Muertos (medidos y documentados, no tocados):
- Frecuencia Schumann: retirada, NULL en toda la cadena
- ONNX: negados por la compuerta
- Loki: posterior ~1e-112, decorativo

## Auto-reparación (3 capas, 2026-10-11)

1. **Detección**: tests, journal, servicios, DB — timer cada 4 h
2. **Fix determinístico**: WAL grande → checkpoint; launcher caído → restart
3. **Fix vía Concilio**: codegemma escribe, verificador ejecuta (esqueleto)

Más **vigilante de rebuild**: cuando termina, verifica el log, sube
servicios, reancla timers, corre verificación — TODO sin intervención.

## Para el operador

El valor del proyecto ya no está en una predicción que no existe. Está en:
1. **La plataforma multi-dominio** — espacio + tierra + atmósfera + financiero
2. **La disciplina de medición honesta** — regla cero, modelo nulo, bitácoras
3. **El auto-diagnóstico y reparación** — un sistema que se vigila a sí mismo

Autor: Elán Zainos Corona (Fractal Core Research)
