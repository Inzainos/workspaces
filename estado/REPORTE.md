# 🌍 Sentinel Omega — Estado del Sistema

**Generado:** 2026-09-19 18:12 UTC (12:12 UTC-6)

> **¿Qué es esto?** Sentinel Omega es un sistema que vigila señales físicas del planeta (campo magnético solar, resonancia de la Tierra, actividad sísmica, gases volcánicos, incluso el nerviosismo de los mercados) buscando *precursores*: condiciones que en 32 años de historia han aparecido **antes** de eventos naturales fuertes. No predice con certeza — reconoce parecidos con el pasado y avisa cuando el presente se parece demasiado a los días previos a un evento. Este reporte es una foto de lo que el sistema ve ahora.

## 📡 Último ciclo — lo que el sistema midió hace un momento

> El **Fantasma** es el termómetro principal: combina en un solo número la agitación del campo magnético, el viento solar y la resonancia de la Tierra. Verde 🟢 <5 = calma · Amarillo 🟡 5-15 · Naranja 🟠 15-30 · Rojo 🔴 ≥30 = condiciones muy cargadas. El **Muro de los 5** son cinco frentes de vigilancia (tierra, atmósfera, océano, sol, mercados); si 3 o más se activan a la vez, distintos dominios físicos están alterados al mismo tiempo — eso casi nunca es coincidencia.

| Métrica | Valor | Lectura |
|---|---|---|
| Fantasma | 🟠 **19.6** `▓▓▓░░░░░░░` | actividad alta |
| Consenso de los 6 bots | NO_SIGNAL (0%) | evaluando |
| Muro de los 5 frentes | 1/5 activos | estable — sin convergencia crítica |
| Precursores detectados | 1 | ["SEISMIC_CLUSTER"] |
| Hora de la medición | 2026-09-16 12:22 UTC | |

## 🚦 Semáforo — reglas fijas del nivel de riesgo

> Estas reglas son **cuantitativas y fijas** (revisables por versión, no por ciclo): con los números de arriba cualquiera puede inferir el nivel sin interpretación subjetiva. La fila marcada ➡ es la que dispara hoy.

| Nivel | Regla (se evalúa de abajo hacia arriba) | Acción interna |
|---|---|---|
| 🔴 ROJO | Muro ≥3/5 (breach) **y** Fantasma ≥30 | Escalamiento interno |
| 🟠 NARANJA | Muro ≥3/5 (breach) **o** (Fantasma ≥15 y firma ≥85%) | Revisión manual inmediata |
| ➡ 🟡 AMARILLO | Fantasma 5–15 **o** firma ≥80% | Vigilancia reforzada |
| 🔵 AZUL | Fantasma <5 con detecciones o muros 1–2 | Seguimiento ampliado |
| 🟢 VERDE | Fantasma <5, muro 0/5, sin firmas ≥80% | Monitoreo base |

**Nivel del corte: 🟡 AMARILLO** — con Fantasma 19.6, muro 1/5 y firma máxima —.

## 📈 Operación reciente — hoy vs cómo solía estar

> La foto de arriba, puesta en contexto: ¿este corte está por encima, en el promedio o por debajo de la actividad usual de las últimas semanas? El **percentil** dice qué fracción de los cortes recientes fue igual o menor que hoy (P75 = hoy es más alto que el 75% del último mes).

| Métrica | Actual | Prom. 7d | Prom. 30d | Máx 30d | Percentil |
|---|---:|---:|---:|---:|---:|
| Fantasma | 19.6 | 20.7 | 17.7 | 62.3 | P77 |
| Muro de los 5 | 1 | 1.5 | 1.6 | 3 | P47 |
| Silent Trigger | inactivo | 50% ciclos | 49% ciclos | — | — |
| Asertividad viva | 94% | 88% | — | — | — |

*Los promedios de 30 días combinan los ciclos conservados y el resumen diario del barrido (lo compactado no se pierde, se resume).*

## 🎯 ¿Le ganamos a alertar siempre? — línea base de Molchan

> La prueba de honestidad definitiva: un bot sin cerebro que alerta SIEMPRE acierta cada vez que hay un sismo cerca de la malla en la ventana de 72 h. Su tasa de acierto es la **tasa base**. Solo si el sistema supera esa tasa hay habilidad real; si no, el número bonito es geografía, no predicción.

| Métrica | Valor |
|---|---:|
| Ventanas evaluadas (viva) | 15984 |
| Ventanas con evento real (tasa base) | 0% |
| Asertividad del sistema | 94% |
| **Ganancia** (sistema ÷ tasa base) | 208.10× |

**Veredicto:** ✅ GANANCIA REAL: el sistema aporta información

*Con 50 nodos reales y radio de 5°, casi toda ventana de 72 h tiene un M4.5+ cerca de algún nodo: para ganar de verdad, las predicciones tendrán que volverse específicas por nodo, no globales.*

## 🔭 Detecciones recientes — las señales individuales

> Cada fila es una señal concreta que el escáner encontró en los datos: una perturbación magnética, un enjambre sísmico, un pico de gas volcánico… La **confianza** dice qué tan clara fue la señal (no la probabilidad de un evento). Una detección aislada es normal; varias juntas de tipos distintos es lo que sube el riesgo.

| Precursor | Confianza | Zona |
|---|---|---|
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |

## ⏱ Anticipación — con cuánto tiempo suele avisar

> Medido sobre el histórico: ¿cuántos días **antes** del evento ya era reconocible su firma? No es un cronómetro exacto — es el promedio de lo que ha pasado. El hallazgo contraintuitivo: **los eventos más grandes avisan con más tiempo**. Un M7 se 'carga' durante más días que un M5.

| Evento | Aviso promedio | Máximo | Mínimo | Casos medidos |
|---|---|---|---|---|
| ERUPCION_VEI3 | **8.4 días** | 14.0 d | 1.0 d | 75 |
| ERUPCION_VEI4 | **5.9 días** | 14.0 d | 1.0 d | 29 |
| SISMO_M4 | **8.1 días** | 14.0 d | 1.0 d | 117 |
| SISMO_M5 | **7.7 días** | 14.0 d | 1.0 d | 115 |
| SISMO_M6 | **9.3 días** | 14.0 d | 1.0 d | 146 |
| SISMO_M7 | **11.6 días** | 14.0 d | 3.0 d | 41 |

*Medición in-sample sobre 32 años de histórico; la ventana de estudio llega a 14 días, así que los máximos pueden estar recortados.*

## 🔍 ¿Qué acelera o retrasa un evento?

> Comparamos las firmas que avisaron con **poco** tiempo (rápidas) contra las que avisaron con **mucho** (lentas). El patrón que salió: cuando hay tormenta geomagnética, el evento llega pronto — *la tormenta precipita*. Cuando el espacio está en calma, la corteza se carga despacio y avisa con más días — *la calma carga*.

| Variable | En firmas rápidas | En firmas lentas | Qué indica |
|---|---|---|---|
| Tormenta geomagnética en las últimas 72h | 0.82 | 0.08 | más presente cuando el evento llega PRONTO |
| Índice Kp máximo (tormenta geomagnética) | 1.78 | 0.23 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ en la ventana (kilotones) | 202.95 | 27.38 | más presente cuando el evento llega PRONTO |
| Erupciones registradas en la ventana | 4.18 | 1.43 | más presente cuando el evento llega PRONTO |
| Índice Kp promedio | 0.18 | 0.06 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ (90 días) | 538.62 | 350.51 | más presente cuando el evento llega PRONTO |

*Rápidas = tercio de firmas con menor anticipación; lentas = tercio con mayor.*

## 🧠 Memoria entrenada — lo que el sistema ya aprendió

> El sistema son **7 bots especializados**: `alfa1` vigila el clima espacial (30 años), `beta1` la resonancia Schumann — el latido electromagnético de la Tierra (30 años), `alfa2` los satélites Sentinel (aprende en vivo, sin backcast), `beta2` la desgasificación volcánica y la atmósfera (14 años), `delta` el humor de los mercados (10 años), `jupiter` la atención colectiva sobre tormentas solares (en vivo), y `padre` arbitra entre todos. Cada uno guarda sus propias **firmas** (patrones de vísperas de evento). El **peso** es su credibilidad ante el padre: 1.00 = normal; baja cuando falla y se recupera cuando acierta; puede superar 1.00 solo si detectó algo que el padre dejó pasar. `alfa2` y `jupiter` acumulan sus firmas desde los ciclos operativos, no desde el backcast histórico.

| Bot | Firmas aprendidas | Veces confirmadas | Credibilidad |
|---|---|---|---|
| alfa1 | 348 | 196,180 | 1.22 `▓▓▓▓▓░` |
| beta1 | 862 | 196,180 | 1.35 `▓▓▓▓▓░` |
| beta2 | 787 | 92,130 | 1.22 `▓▓▓▓▓░` |
| delta | 676 | 65,394 | 1.10 `▓▓▓▓░░` |
| omega | 356 | 196,174 | 1.29 `▓▓▓▓▓░` |
| padre | 5,036 | 196,179 | 0.68 `▓▓▓░░░` |
| alfa2 | _en vivo · esperando cobertura satelital_ | — | 1.00 `▓▓▓▓░░` |
| jupiter | _en vivo · atención colectiva_ | — | 1.00 `▓▓▓▓░░` |

## 🎯 Asertividad — ¿qué tan bien le ha ido?

> Tres formas de medir lo mismo. **Histórica**: al repasar los 32 años de datos como examen, ¿reconoció las vísperas de los eventos que ya sabemos que ocurrieron? **Viva**: desde que opera en tiempo real, cada aviso queda registrado y un auditor independiente (el Juez) lo califica 72 horas después contra los sismos que realmente ocurrieron — sin trampa posible. **7 días**: lo mismo, pero solo la última semana. La viva empieza en '—' hasta que las primeras ventanas de 72h se cierran.

| Métrica | Valor |
|---|---|
| **Histórica** (examen sobre 32 años) | 97.9% |
| **Viva** (operación real, auditada) | 93.7% |
| **Últimos 7 días** (viva) | 88.5% |

### Por bot

| Bot | Histórica | Viva | Viva 7d | Credibilidad |
|---|---|---|---|---|
| alfa1 | 97.3% | 73.6% | 30.9% | 1.22 |
| alfa2 | 100.0% | 99.5% | 100.0% | 1.00 |
| beta1 | 98.8% | 92.8% | 92.6% | 1.35 |
| beta2 | 97.2% | 99.5% | 100.0% | 1.22 |
| delta | 99.5% | 99.5% | 100.0% | 1.10 |
| jupiter | 66.3% | 89.6% | 87.7% | 1.00 |
| loki | 100.0% | 99.5% | 100.0% | 1.00 |
| omega | 98.4% | 97.1% | 92.6% | 1.29 |
| padre | 97.8% | 92.3% | 92.6% | 0.68 |

*La histórica mide reconocimiento de patrones dentro de los mismos datos con que se entrenó (por eso es tan alta). La viva es la prueba honesta: predicciones a futuro calificadas contra la realidad.*

## 🪞 Realidad vs fantasía — el sesgo de aprendizaje

> La asertividad histórica alta es *in-sample*: el bot reconoce las firmas con las que se entrenó (comodidad). La columna **Causal (real)** mide lo honesto: ¿reconoció el evento con la memoria que ya tenía **antes** de que ocurriera? El **sesgo** es la diferencia — cuánto de esa competencia era fantasía. Aunque el número real sea más bajo, es la verdad.

| Bot | In-sample | **Causal (real)** | Sesgo (fantasía) |
|---|---|---|---|
| beta2 | 98.2% | **50.3%** | +48.0% ⚠️ |
| delta | 99.4% | **87.4%** | +11.9% |
| beta1 | 100.0% | **99.5%** | +0.5% ✅ |
| alfa1 | 100.0% | **99.7%** | +0.3% ✅ |
| omega | 100.0% | **99.7%** | +0.3% ✅ |
| padre | 100.0% | **99.7%** | +0.3% ✅ |

*Sesgo < 5% = el bot generaliza de verdad. Sesgo alto = su competencia era comodidad in-sample; su decisión real es más floja de lo que aparentaba.*

## 🗺 Correlaciones aprendidas — qué precede a cada evento

> Mapa de calor: qué tan elevada está cada variable en los **14 días previos** a cada tipo de evento comparado con su nivel habitual. 🔴≥2× · 🟠≥1.5× · 🟡≥1.2× · ⬜~normal · 🔵↓bajo. Un 🔴 en 'SO₂' para 'ERUPCION_VEI4' significa que justo antes de esas erupciones el SO₂ estaba el doble de lo normal. Un 🔵 en 'Kp' para 'SISMO_M7' confirma el Silent Trigger: los grandes sismos a veces ocurren en calma geomagnética.

| Variable | 🌋VEIVEI3 | 🌋VEIVEI4 | 🌋VEIVEI5 | M3_obs | M4 | M5 | M6 | M7 | ☀️KpKp6 | ☀️KpKp7 | ☀️KpKp9 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gas volcánico SO₂ en la ventana (kilot | ⬜1.0 | 🔴2.4 | 🔴2.2 | 🔴15.0 | ⬜1.0 | ⬜1.0 | ⬜1.1 | 🔵0.8 | 🔵0.7 | 🔵0.6 | 🔵0.8 |
| Rendimiento de Bitcoin en la ventana | 🟠1.8 | 🔴3.3 | 🔵-4.3 |   —   | ⬜1.0 | ⬜0.9 | ⬜1.1 | ⬜1.1 |   —   | 🔵-1.8 | 🟠1.7 |
| Tormenta geomagnética en las últimas 7 | ⬜0.8 | 🔵0.5 | 🔵0.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.9 | 🔴4.0 | 🔴2.5 | 🔴3.8 |
| Índice Kp promedio | 🔵0.6 | ⬜0.9 | 🔵0.1 | 🔵0.1 | ⬜1.0 | ⬜1.0 | ⬜0.9 | ⬜1.0 | 🔴3.2 | 🟠1.7 | 🔴2.0 |
| Índice Kp máximo (tormenta geomagnétic | 🔵0.7 | ⬜1.0 | 🔵0.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | 🔴2.6 | 🟠1.7 | 🟠1.7 |
| Erupciones registradas en la ventana | 🟡1.3 | 🟡1.3 | 🟠1.5 | 🔴2.5 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | 🔵0.6 | ⬜0.9 | 🔵0.6 |
| Gas volcánico SO₂ (90 días) | ⬜1.0 | 🟡1.4 | 🟠1.6 | 🔴2.4 | ⬜1.0 | ⬜1.0 | ⬜1.1 | ⬜1.0 | 🟡1.2 | ⬜1.0 | ⬜0.9 |
| Erupciones (90 días) | ⬜1.1 | ⬜0.8 | 🔴2.2 | 🔵0.4 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.9 | ⬜0.8 | ⬜0.9 | ⬜1.1 |

## 🏆 Top 10 patrones del sistema

> Los **patrones más vistos** en 32 años de historia: firmas que el sistema reconoció más veces antes de un evento. Cuantas más repeticiones, más confiable es el patrón como señal. El **aviso** es el tiempo de anticipación típico que esa firma da antes del evento.

| # | Evento | Bot | Zona / Nodo | Veces | Estado | Aviso |
|---|---|---|---|---|---|---|
| 1 | 🌎 **SISMO_M4** | omega | Ghost Scotia Arc | 29,166 | ✅ consolidada | — |
| 2 | 🌎 **SISMO_M4** | omega | Papua NG | 12,226 | ✅ consolidada | — |
| 3 | 🌎 **SISMO_M4** | omega | Alaska Subducción | 10,889 | ✅ consolidada | — |
| 4 | 🌎 **SISMO_M5** | omega | Italia Apeninos | 10,721 | ✅ consolidada | — |
| 5 | 🌎 **SISMO_M4** | alfa1 | Ghost Mid-Atlantic S | 10,034 | ✅ consolidada | — |
| 6 | 🌎 **SISMO_M4** | alfa1 | Filipinas | 9,891 | ✅ consolidada | — |
| 7 | 🌎 **SISMO_M4** | alfa1 | Papua NG | 9,465 | ✅ consolidada | — |
| 8 | 🌎 **SISMO_M4** | alfa1 | Ghost Sulawesi | 9,314 | ✅ consolidada | — |
| 9 | 🌎 **SISMO_M4** | alfa1 | Filipinas | 9,075 | ✅ consolidada | — |
| 10 | 🌎 **SISMO_M4** | omega | Ghost Nankai-Tokai | 8,199 | ✅ consolidada | — |

## 📊 Patrones por tipo de evento — top 5 por clase

> Para cada tipo de evento que el sistema ha aprendido, las 5 firmas más consolidadas: los patrones más reconocibles que preceden a ese tipo de evento. La **zona** es el nodo de la malla UVG-125 donde se aprendió la firma.

### 🌋 ERUPCION_VEI3

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | Baja California Sur (24.1, -110.0) | 198 | ✅ consolidada | — |
| omega | Grecia Helénica (37.0, 22.0) | 145 | ✅ consolidada | — |
| beta1 | Baja California Sur (24.1, -110.0) | 111 | ✅ consolidada | — |
| omega | Baja California Sur (24.1, -110.0) | 105 | ✅ consolidada | — |
| alfa1 | Baja California Sur (24.1, -110.0) | 102 | ✅ consolidada | — |

### 🌋 ERUPCION_VEI4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Baja California Sur (24.1, -110.0) | 52 | ✅ consolidada | — |
| omega | Ghost Oaxaca Interior (16.8, -96.5) | 52 | ✅ consolidada | — |
| omega | Perú Subducción (-12.0, -77.0) | 45 | ✅ consolidada | — |
| beta1 | Baja California Sur (24.1, -110.0) | 41 | ✅ consolidada | — |
| beta1 | Ghost Vanuatu (-16.0, 168.0) | 32 | ✅ consolidada | — |

### 🌋 ERUPCION_VEI5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Grecia Helénica (37.0, 22.0) | 2 | 🆕 observada | — |
| alfa1 | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
| beta1 | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
| padre | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
| alfa1 | Islandia Rift (65.0, -18.0) | 1 | 🆕 nueva | — |

### 🌎 SISMO_M3_obs

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | GeoBat San Andreas Creep (36.0, -120.5) | 1 | 🆕 nueva | — |
| beta1 | GeoBat San Andreas Creep (36.0, -120.5) | 1 | 🆕 nueva | — |
| omega | GeoBat San Andreas Creep (36.0, -120.5) | 1 | 🆕 nueva | — |
| padre | GeoBat San Andreas Creep (36.0, -120.5) | 1 | 🆕 nueva | — |

### 🌎 SISMO_M4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Scotia Arc (-57.0, -30.0) | 29,166 | ✅ consolidada | — |
| omega | Papua NG (-6.0, 147.0) | 12,226 | ✅ consolidada | — |
| omega | Alaska Subducción (61.0, -150.0) | 10,889 | ✅ consolidada | — |
| alfa1 | Ghost Mid-Atlantic S (10.0, -40.0) | 10,034 | ✅ consolidada | — |
| alfa1 | Filipinas (14.5, 121.0) | 9,891 | ✅ consolidada | — |

### 🌎 SISMO_M5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Italia Apeninos (42.0, 13.0) | 10,721 | ✅ consolidada | — |
| omega | Ghost Mariana (15.0, 147.0) | 5,438 | ✅ consolidada | — |
| alfa1 | Centroamérica (13.0, -88.0) | 4,110 | ✅ consolidada | — |
| omega | Ghost Sunda Strait (-6.5, 105.5) | 4,006 | ✅ consolidada | — |
| alfa1 | Ghost Banda Sea (-5.0, 130.0) | 3,530 | ✅ consolidada | — |

### 🌎 SISMO_M6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Grecia Helénica (37.0, 22.0) | 689 | ✅ consolidada | — |
| omega | Ghost Perú-Chile (-18.0, -72.0) | 655 | ✅ consolidada | — |
| alfa1 | Ghost Kamchatka-Kuril (48.0, 153.0) | 474 | ✅ consolidada | — |
| alfa1 | Centroamérica (13.0, -88.0) | 433 | ✅ consolidada | — |
| alfa1 | Ghost Nankai-Tokai (34.5, 138.0) | 432 | ✅ consolidada | — |

### 🌎 SISMO_M7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | GeoBat Japón Nankai Fluidos (33.5, 136.0) | 111 | ✅ consolidada | — |
| alfa1 | Ghost Vanuatu (-16.0, 168.0) | 110 | ✅ consolidada | — |
| alfa1 | GeoBat Japón Nankai Fluidos (33.5, 136.0) | 109 | ✅ consolidada | — |
| alfa1 | Tonga-Kermadec (-20.0, -175.0) | 103 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 94 | ✅ consolidada | — |

### ☀️ TORMENTA_Kp6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 3 | 🔁 recurrente | — |
| beta1 | global | 3 | 🔁 recurrente | — |
| alfa1 | global | 3 | 🔁 recurrente | — |
| alfa1 | global | 2 | 🆕 observada | — |
| alfa1 | global | 2 | 🆕 observada | — |

### ☀️ TORMENTA_Kp7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 7 | ✅ consolidada | — |
| omega | global | 6 | ✅ consolidada | — |
| omega | global | 5 | ✅ consolidada | — |
| alfa1 | global | 5 | ✅ consolidada | — |
| beta1 | global | 5 | ✅ consolidada | — |

### ☀️ TORMENTA_Kp9

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | global | 9 | ✅ consolidada | — |
| beta1 | global | 6 | ✅ consolidada | — |
| beta1 | global | 6 | ✅ consolidada | — |
| omega | global | 4 | 🔁 recurrente | — |
| alfa1 | global | 4 | 🔁 recurrente | — |

## 🔀 Orden de los precursores — ¿importa la secuencia?

> El Padre también observa el **orden** en que se activaron los dominios en la víspera de cada evento (¿primero el gas y luego los sismos, o al revés?) y discierne contando: si una secuencia domina claramente, el orden IMPORTA; si las permutaciones se reparten parejo, es INDIFERENTE — lo que pesa es la convergencia, no la coreografía.

| Conjunto de dominios | Casos | Secuencia dominante | % | Veredicto |
|---|---:|---|---:|---|
| COSMICO+DESGAS+SISMICO | 100 | COSMICO+DESGAS+SISMICO | 40% | **INDIFERENTE** |
| COSMICO+SISMICO | 94 | COSMICO+SISMICO | 61% | **EL ORDEN IMPORTA** |
| COSMICO+DESGAS+FINANCIERO+SISMICO | 55 | COSMICO+DESGAS+FINANCIERO+SISMICO | 24% | **INDIFERENTE** |

## ⚖️ El Juez — auditoría independiente

> El Juez es un auditor que **nunca predice**: solo registra cada aviso de los bots y, cuando se cierra la ventana de 72 horas, lo compara contra el catálogo sísmico real (USGS) y dicta sentencia. Dejar pasar un evento castiga 10 veces más que una falsa alarma — preferimos un sistema nervioso a uno dormido. **Solo la fase viva puntúa asertividad**; el resto es bitácora de entrenamiento y no se mezcla.

**Operación viva (lo que cuenta):**
- ACIERTO — avisó y el evento ocurrió: 14,983
- FALLO — el evento ocurrió sin aviso (lo más castigado): 72
- FALSO POSITIVO — avisó y no pasó nada: 929

**Bitácora de entrenamiento (reconocimiento/backtest/trasfondo — no puntúa):**
- ACIERTO: 939,183
- FALLO: 202

## 🧾 Bitácora del sistema — versión, cambios y salud

> No solo el planeta: el propio Sentinel deja traza. Cada corte registra versión, pesos y métricas, y se compara con el corte anterior — así se ve si un cambio mejoró o empeoró el comportamiento, y los post-mortems tienen base.

| Campo | Este corte | Corte anterior | Cambio |
|---|---|---|---|
| Versión del modelo | 2.5.4 | 2.5.4 | sin cambio |
| Asertividad viva | 93.7% | 93.7% | +0.0% |
| Aciertos / Fallos (vivos) | 14,983 / 72 | 14,983 / 72 | +0 aciertos |
| Pendientes de auditoría | 0 | 0 | +0 |
| Pesos de bots | 9 bots | — | sin movimiento |

*Asertividad viva, últimos cortes: 94% → 94% → 94% → 94% → 94%*


## ✅ Aciertos y Predicciones Correctas

> El sistema también tiene victorias que celebrar. Esta sección documenta cuándo nuestras predicciones fueron correctas: eventos que anticipamos, qué tan bien los predijimos, y cuántos días antes vimos el patrón.

### 📊 Resumen — Últimos 30 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 14983 |
| **Fallos** | 72 |
| **Falsos positivos** | 929 |
| **Tasa de acierto** | 93.7% `▓▓▓▓▓▓▓▓▓▓▓░` |
| **Total predicciones** | 15984 |

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación (días) |
|-----|----------|------|-----------|----------------------|
| alfa2 | 1768/1776 | 100% `▓▓▓▓▓▓▓▓` | 0.00 | 0.1 |
| beta2 | 1768/1776 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| delta | 1768/1776 | 100% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1 |
| loki | 1768/1776 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| omega | 1724/1776 | 97% `▓▓▓▓▓▓▓▓` | 0.36 | 0.1 |
| beta1 | 1648/1776 | 93% `▓▓▓▓▓▓▓░` | 0.31 | 0.1 |
| padre | 1640/1776 | 92% `▓▓▓▓▓▓▓░` | 0.16 | 0.1 |
| jupiter | 1591/1776 | 90% `▓▓▓▓▓▓▓░` | 0.23 | 0.1 |
| alfa1 | 1308/1776 | 74% `▓▓▓▓▓▓░░` | 0.42 | 0.1 |

### 🎯 Eventos Predichos Correctamente (más recientes primero)

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 25.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### JUPITER — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 0.0% `░░░░░░░░░░`
- **Fase:** viva

#### DELTA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### BETA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### BETA1 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### PADRE — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:22 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 0.0% `░░░░░░░░░░`
- **Fase:** viva

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:17 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-16 12:17 UTC
- **Evento real:** 2026-09-16 18:03 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 25.0% `▓▓░░░░░░░░`
- **Fase:** viva

_... y 14973 aciertos más en los últimos 30 días_

---
*Todos los datos provienen de fuentes públicas oficiales (NOAA, USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección civil: es investigación de precursores en curso.*

*Ciclos totales: 3,443 · Sentinel Omega · Fractal Core Research*
