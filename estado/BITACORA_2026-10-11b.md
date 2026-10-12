# Bitácora técnica — Sentinel Omega · 2026-10-11 (tarde)

**El pivote estratégico: el proyecto deja de perseguir lo que no existe
y se convierte en lo que ya es.** El operador dio el GO: «B y C en
paralelo, A como experimento dirigido». La plataforma multi-dominio
(espacio + tierra + atmósfera + financiero) ya funciona — solo estaba
mirando al otro lado.

| | |
|---|---|
| Rama | `local/recuperacion-datos-2026-09`, con push |
| Rebuild | Completo y verificado: 40.726 firmas, 13.972 exigibles, cero rasgos Schumann |
| Servicios | Todos arriba, auto-fix y vigilante de rebuild armados |

---

## 1. La Opción B: la plataforma que YA existe

La pregunta que abre el pivote: **¿qué detecta BIEN el sistema hoy?**
La medición contra 30 años de historia:

| Dominio | Señal | En la DB | Firmas | Scanner vivo |
|---|---|---|---|---|
| Espacio | Tormentas Kp≥5 | **8.439** horas | 429 Kp6 | `_scan_tormenta_solar` ✓ |
| Espacio | Grietas Bz≤−10 | **1.738** horas | — | `GRIETA` en alertas ✓ |
| Espacio | Kp≥8 extremas | **258** horas | — | ✓ |
| Volcánico | Erupciones VEI≥3 | — | **756** | SO2 + air_quality ✓ |
| Volcánico | VEI≥4 | — | **223** | ✓ |
| Sísmico | Enjambres activos | **2 ahora mismo** | 20.130+ | `_scan_seismic_cluster` ✓ |
| Sísmico | Sismicidad por nodo | 191.592 eventos | 34.497 M4/M5 | ✓ |
| Financiero | Estrés de mercado | vivo cada ciclo | 718 | techo WATCH ✓ |
| Atmósfera | Presión/química/niebla | vivo cada ciclo | 2.047 | ✓ |

**El dato decisivo: hubo una tormenta Kp=9 AYER** (2026-10-10 23:00) y el
sistema la vio. Con 30 años de historia, sensores vivos, firmas entrenadas
y scanner con las rutas, la plataforma multi-dominio **ya existe**. El
proyecto estaba intentando ser un predictor de sismos cuando su
arquitectura real es un detector multi-dominio de anomalías naturales.

## 2. La Opción C: validar lo que corre

### 2.1 El 46 % de exigibles, descompuesto

La cifra parece alta (13.972 de 23.266) pero el REPARTO dice la verdad:

| Bot | Exigibles | ¿Por qué? |
|---|---|---|
| **padre** | **11.271** | 100 % dependen de `sismo_*_win` (Omori). CERO sin rasgo sísmico. Es un mapa de peligrosidad, no detección de precursores. |
| **beta1** | **2.394** | El único con señal real (AUC 0.802, lift 32.6×) |
| delta | 4 | Marginal |
| beta2 | 1 | Marginal |
| alfa1, omega, loki, jupiter, alfa2 | **0** | Concordante con la compuerta (AUC ~0.5) |

**Sin el padre: 2.399 exigibles** — mucho más cerca de los 982 originales.
El 46 % es un espejo de Omori, no de precursores. La medición de
`exigibles SIN rasgo sísmico = 0` lo cierra.

El REPARTO concuerda con la compuerta ONNX (medición independiente):
los bots con exigibles > 0 son los que la compuerta no niega por ruido.

### 2.2 El consenso familiar en producción

Recién estrenado (opción B del operador): corroboración por familia
`schumann_cymatics` (beta1 O beta2 activos). Necesita tiempo de producción
para medir si el tier ALERT dispara. El WATCH sigue siendo la vía real.

## 3. La Opción A: la plantilla del experimento dirigido

`docs/EXPERIMENTO_DIRIGIDO.md` — las lecciones de la medición Schumann
convertidas en pasos reutilizables:

1. Declara la hipótesis ANTES de mirar datos
2. El modelo nulo va al lado del número
3. Barrido de semillas (once)
4. El control más barato antes de la explicación elaborada

Con candidatos de física más plausible que Schumann: radón,
resistividad, migración de enjambres, Vp/Vs, infrasonido.

## 4. Auto-reparación: las tres capas vivas

| Capa | Qué hace | Estado |
|---|---|---|
| 1. Detección | Tests, journal, servicios, DB — timer 4 h | Activo, verificado |
| 2. Fix determinístico | WAL→checkpoint, launcher→restart, timer→reanclar | Activo |
| 3. Fix vía Concilio | codegemma escribe, verificador ejecuta | Esqueleto, GO pendiente |

Más el **vigilante de rebuild**: detecta que terminó, verifica log, sube
servicios, reancla timers, corre post-rebuild — TODO sin intervención.

## 5. La identidad del proyecto, actualizada

`sentinel_omega/README.md` reescrito: **"Plataforma de Detección de
Anomalías Multi-Dominio"**. Qué hace (verificado), qué NO hace (medido),
lo que está listo para experimentos dirigidos, y los vivos/muertos
documentados.

## 6. Qué sigue

- **B**: dejar que el sistema corra como plataforma multi-dominio y medir
  qué produce en tiempo real (tormentas solares, enjambres, erupciones).
- **C**: validar el consenso familiar con tiempo de producción; medir si
  el tier ALERT dispara con la nueva compuerta.
- **A**: cuando surja una señal candidata nueva (radón, resistividad),
  la plantilla está lista en `docs/EXPERIMENTO_DIRIGIDO.md`.
