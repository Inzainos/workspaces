# 🌍 Sentinel Omega — Estado del Sistema

**Generado:** 2026-09-22 07:20 UTC (01:20 UTC-6)

> **¿Qué es esto?** Sentinel Omega es un sistema que vigila señales físicas del planeta (campo magnético solar, resonancia de la Tierra, actividad sísmica, gases volcánicos, incluso el nerviosismo de los mercados) buscando *precursores*: condiciones que en 32 años de historia han aparecido **antes** de eventos naturales fuertes. No predice con certeza — reconoce parecidos con el pasado y avisa cuando el presente se parece demasiado a los días previos a un evento. Este reporte es una foto de lo que el sistema ve ahora.

## 📡 Último ciclo — lo que el sistema midió hace un momento

> El **Fantasma** es el termómetro principal: combina en un solo número la agitación del campo magnético, el viento solar y la resonancia de la Tierra. Verde 🟢 <5 = calma · Amarillo 🟡 5-15 · Naranja 🟠 15-30 · Rojo 🔴 ≥30 = condiciones muy cargadas. El **Muro de los 5** son cinco frentes de vigilancia (tierra, atmósfera, océano, sol, mercados); si 3 o más se activan a la vez, distintos dominios físicos están alterados al mismo tiempo — eso casi nunca es coincidencia.

| Métrica | Valor | Lectura |
|---|---|---|
| Fantasma | 🟡 **8.5** `▓░░░░░░░░░` | actividad moderada |
| Consenso de los 6 bots | NO_SIGNAL (0%) | evaluando |
| Muro de los 5 frentes | 2/5 activos | estable — sin convergencia crítica |
| Precursores detectados | 2 | ["SILENT_TRIGGER", "SEISMIC_CLUSTER"] |
| Hora de la medición | 2026-09-20 20:58 UTC | |

## 🚦 Semáforo — reglas fijas del nivel de riesgo

> Estas reglas son **cuantitativas y fijas** (revisables por versión, no por ciclo): con los números de arriba cualquiera puede inferir el nivel sin interpretación subjetiva. La fila marcada ➡ es la que dispara hoy.

| Nivel | Regla (se evalúa de abajo hacia arriba) | Acción interna |
|---|---|---|
| 🔴 ROJO | Muro ≥3/5 (breach) **y** Fantasma ≥30 | Escalamiento interno |
| 🟠 NARANJA | Muro ≥3/5 (breach) **o** (Fantasma ≥15 y firma ≥85%) | Revisión manual inmediata |
| ➡ 🟡 AMARILLO | Fantasma 5–15 **o** firma ≥80% | Vigilancia reforzada |
| 🔵 AZUL | Fantasma <5 con detecciones o muros 1–2 | Seguimiento ampliado |
| 🟢 VERDE | Fantasma <5, muro 0/5, sin firmas ≥80% | Monitoreo base |

**Nivel del corte: 🟡 AMARILLO** — con Fantasma 8.5, muro 2/5 y firma máxima 100%.

## 📈 Operación reciente — hoy vs cómo solía estar

> La foto de arriba, puesta en contexto: ¿este corte está por encima, en el promedio o por debajo de la actividad usual de las últimas semanas? El **percentil** dice qué fracción de los cortes recientes fue igual o menor que hoy (P75 = hoy es más alto que el 75% del último mes).

| Métrica | Actual | Prom. 7d | Prom. 30d | Máx 30d | Percentil |
|---|---:|---:|---:|---:|---:|
| Fantasma | 8.5 | 36.8 | 23.6 | 62.3 | P15 |
| Muro de los 5 | 2 | 1.5 | 1.7 | 3 | P83 |
| Silent Trigger | activo | 50% ciclos | 48% ciclos | — | — |
| Asertividad viva | 94% | 87% | — | — | — |

*Los promedios de 30 días combinan los ciclos conservados y el resumen diario del barrido (lo compactado no se pierde, se resume).*

## 🎯 ¿Le ganamos a alertar siempre? — línea base de Molchan

> La prueba de honestidad definitiva: un bot sin cerebro que alerta SIEMPRE acierta cada vez que hay un sismo cerca de la malla en la ventana de 72 h. Su tasa de acierto es la **tasa base**. Solo si el sistema supera esa tasa hay habilidad real; si no, el número bonito es geografía, no predicción.

| Métrica | Valor |
|---|---:|
| Ventanas evaluadas (viva) | 16029 |
| Ventanas con evento real (tasa base) | 0% |
| Asertividad del sistema | 94% |
| **Ganancia** (sistema ÷ tasa base) | 208.54× |

**Veredicto:** ✅ GANANCIA REAL: el sistema aporta información

*Con 50 nodos reales y radio de 5°, casi toda ventana de 72 h tiene un M4.5+ cerca de algún nodo: para ganar de verdad, las predicciones tendrán que volverse específicas por nodo, no globales.*

## 🔭 Detecciones recientes — las señales individuales

> Cada fila es una señal concreta que el escáner encontró en los datos: una perturbación magnética, un enjambre sísmico, un pico de gas volcánico… La **confianza** dice qué tan clara fue la señal (no la probabilidad de un evento). Una detección aislada es normal; varias juntas de tipos distintos es lo que sube el riesgo.

| Precursor | Confianza | Zona |
|---|---|---|
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |

## 🎯 Firma Match — la memoria reconoce el momento actual

> Esta es la parte más importante del reporte. Durante el entrenamiento, el sistema estudió los **14 días previos** a cada sismo fuerte de los últimos 32 años y guardó el 'rostro' de esas vísperas como una **firma**. Aquí compara el estado actual del planeta contra esa memoria. Un match del 84% significa: *lo que estamos viendo hoy se parece en un 84% a cómo se veían los días previos a ese tipo de evento*. **Veces vista** = cuántas veces esa misma firma precedió a un evento real en el histórico — a más repeticiones, más confiable el parecido.

| Parecido | Precedió a | Zona (nodo de la malla) | Veces vista | Suele avisar con |
|---|---|---|---|---|
| **100%** `▓▓▓▓▓` | SISMO_M5 | **Ghost Banda Sea** (-5.0, 130.0) · nodo 83 | 45 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M4 | **Ghost Tonga-Fiji** (-18.0, -178.0) · nodo 64 | 184 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M6 | **GeoBat Sumatra Hidrotermal** (1.0, 98.0) · nodo 109 | 6 | ~9 días |

*SISMO_M5 / M6 / M7 = sismo de magnitud 5+, 6+ o 7+. La zona es el punto de la malla global UVG-125 donde se aprendió la firma (nombre y coordenadas lat, lon); los nodos 'Ghost' son puntos teóricos de la malla sin estación física encima.*

## ⏱ Anticipación — con cuánto tiempo suele avisar

> Medido sobre el histórico: ¿cuántos días **antes** del evento ya era reconocible su firma? No es un cronómetro exacto — es el promedio de lo que ha pasado. El hallazgo contraintuitivo: **los eventos más grandes avisan con más tiempo**. Un M7 se 'carga' durante más días que un M5.

| Evento | Aviso promedio | Máximo | Mínimo | Casos medidos |
|---|---|---|---|---|
| ERUPCION_VEI3 | **7.2 días** | 14.0 d | 1.0 d | 73 |
| ERUPCION_VEI4 | **4.1 días** | 14.0 d | 1.0 d | 30 |
| SISMO_M4 | **6.2 días** | 14.0 d | 1.0 d | 116 |
| SISMO_M5 | **5.9 días** | 14.0 d | 1.0 d | 124 |
| SISMO_M6 | **8.9 días** | 14.0 d | 1.0 d | 142 |
| SISMO_M7 | **10.3 días** | 14.0 d | 1.0 d | 17 |

*Medición in-sample sobre 32 años de histórico; la ventana de estudio llega a 14 días, así que los máximos pueden estar recortados.*

## 🔍 ¿Qué acelera o retrasa un evento?

> Comparamos las firmas que avisaron con **poco** tiempo (rápidas) contra las que avisaron con **mucho** (lentas). El patrón que salió: cuando hay tormenta geomagnética, el evento llega pronto — *la tormenta precipita*. Cuando el espacio está en calma, la corteza se carga despacio y avisa con más días — *la calma carga*.

| Variable | En firmas rápidas | En firmas lentas | Qué indica |
|---|---|---|---|
| Gas volcánico SO₂ en la ventana (kilotones) | 247.49 | 26.74 | más presente cuando el evento llega PRONTO |
| Tormenta geomagnética en las últimas 72h | 0.58 | 0.08 | más presente cuando el evento llega PRONTO |
| Índice Kp máximo (tormenta geomagnética) | 1.27 | 0.32 | más presente cuando el evento llega PRONTO |
| Sismos en las últimas 72h | 4.99 | 2.35 | más presente cuando el evento llega PRONTO |
| Erupciones registradas en la ventana | 4.37 | 2.17 | más presente cuando el evento llega PRONTO |
| Sismos en la ventana de 14 días | 14.79 | 7.51 | más presente cuando el evento llega PRONTO |

*Rápidas = tercio de firmas con menor anticipación; lentas = tercio con mayor.*

## 🧠 Memoria entrenada — lo que el sistema ya aprendió

> El sistema son **7 bots especializados**: `alfa1` vigila el clima espacial (30 años), `beta1` la resonancia Schumann — el latido electromagnético de la Tierra (30 años), `alfa2` los satélites Sentinel (aprende en vivo, sin backcast), `beta2` la desgasificación volcánica y la atmósfera (14 años), `delta` el humor de los mercados (10 años), `jupiter` la atención colectiva sobre tormentas solares (en vivo), y `padre` arbitra entre todos. Cada uno guarda sus propias **firmas** (patrones de vísperas de evento). El **peso** es su credibilidad ante el padre: 1.00 = normal; baja cuando falla y se recupera cuando acierta; puede superar 1.00 solo si detectó algo que el padre dejó pasar. `alfa2` y `jupiter` acumulan sus firmas desde los ciclos operativos, no desde el backcast histórico.

| Bot | Firmas aprendidas | Veces confirmadas | Credibilidad |
|---|---|---|---|
| alfa1 | 341 | 182,915 | 1.35 `▓▓▓▓▓░` |
| beta1 | 2,992 | 182,915 | 1.42 `▓▓▓▓▓▓` |
| beta2 | 787 | 92,130 | 1.29 `▓▓▓▓▓░` |
| delta | 676 | 65,394 | 1.29 `▓▓▓▓▓░` |
| loki | 5,467 | 79,445 | 1.29 `▓▓▓▓▓░` |
| omega | 1,386 | 182,915 | 1.35 `▓▓▓▓▓░` |
| padre | 9,549 | 182,915 | 0.83 `▓▓▓░░░` |
| alfa2 | _en vivo · esperando cobertura satelital_ | — | 1.00 `▓▓▓▓░░` |
| jupiter | _en vivo · atención colectiva_ | — | 1.00 `▓▓▓▓░░` |

## 🎯 Asertividad — ¿qué tan bien le ha ido?

> Tres formas de medir lo mismo. **Histórica**: al repasar los 32 años de datos como examen, ¿reconoció las vísperas de los eventos que ya sabemos que ocurrieron? **Viva**: desde que opera en tiempo real, cada aviso queda registrado y un auditor independiente (el Juez) lo califica 72 horas después contra los sismos que realmente ocurrieron — sin trampa posible. **7 días**: lo mismo, pero solo la última semana. La viva empieza en '—' hasta que las primeras ventanas de 72h se cierran.

| Métrica | Valor |
|---|---|
| **Histórica** (examen sobre 32 años) | 98.1% |
| **Viva** (operación real, auditada) | 93.7% |
| **Últimos 7 días** (viva) | 86.5% |

### Por bot

| Bot | Histórica | Viva | Viva 7d | Credibilidad |
|---|---|---|---|---|
| alfa1 | 99.1% | 73.4% | 30.4% | 1.35 |
| alfa2 | — | 99.6% | 100.0% | 1.00 |
| beta1 | 98.6% | 92.8% | 90.1% | 1.42 |
| beta2 | 97.1% | 99.6% | 100.0% | 1.29 |
| delta | 99.6% | 99.6% | 100.0% | 1.29 |
| jupiter | — | 89.3% | 78.0% | 1.00 |
| loki | 98.5% | 99.6% | 100.0% | 1.29 |
| omega | 98.2% | 97.0% | 90.1% | 1.35 |
| padre | 97.8% | 92.3% | 90.1% | 0.83 |

*La histórica mide reconocimiento de patrones dentro de los mismos datos con que se entrenó (por eso es tan alta). La viva es la prueba honesta: predicciones a futuro calificadas contra la realidad.*

## 🪞 Realidad vs fantasía — el sesgo de aprendizaje

> La asertividad histórica alta es *in-sample*: el bot reconoce las firmas con las que se entrenó (comodidad). La columna **Causal (real)** mide lo honesto: ¿reconoció el evento con la memoria que ya tenía **antes** de que ocurriera? El **sesgo** es la diferencia — cuánto de esa competencia era fantasía. Aunque el número real sea más bajo, es la verdad.

| Bot | In-sample | **Causal (real)** | Sesgo (fantasía) |
|---|---|---|---|
| beta2 | 98.2% | **50.3%** | +48.0% ⚠️ |
| delta | 99.4% | **87.4%** | +11.9% |
| beta1 | 100.0% | **99.5%** | +0.5% ✅ |
| padre | 100.0% | **99.5%** | +0.5% ✅ |
| alfa1 | 100.0% | **99.7%** | +0.3% ✅ |
| omega | 100.0% | **99.7%** | +0.3% ✅ |
| loki | 40.6% | **40.6%** | +0.0% ✅ |
| alfa2 | — | **—** | — |
| jupiter | — | **—** | — |

*Sesgo < 5% = el bot generaliza de verdad. Sesgo alto = su competencia era comodidad in-sample; su decisión real es más floja de lo que aparentaba.*

## 🗺 Correlaciones aprendidas — qué precede a cada evento

> Mapa de calor: qué tan elevada está cada variable en los **14 días previos** a cada tipo de evento comparado con su nivel habitual. 🔴≥2× · 🟠≥1.5× · 🟡≥1.2× · ⬜~normal · 🔵↓bajo. Un 🔴 en 'SO₂' para 'ERUPCION_VEI4' significa que justo antes de esas erupciones el SO₂ estaba el doble de lo normal. Un 🔵 en 'Kp' para 'SISMO_M7' confirma el Silent Trigger: los grandes sismos a veces ocurren en calma geomagnética.

| Variable | 🌋VEIVEI3 | 🌋VEIVEI4 | 🌋VEIVEI5 | M3_obs | M4 | M5 | M6 | M7 | ☀️KpKp6 | ☀️KpKp7 | ☀️KpKp9 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gas volcánico SO₂ en la ventana (kilot | ⬜1.0 | 🔴2.9 | 🔴2.3 | 🔴15.7 | ⬜1.0 | ⬜1.0 | ⬜1.1 | 🔵0.7 | 🔵0.7 | 🔵0.5 | ⬜0.8 |
| Rendimiento de Bitcoin en la ventana | 🟠1.7 | 🔴2.8 | 🔵-3.9 |   —   | ⬜1.0 | ⬜0.9 | ⬜1.1 | ⬜1.0 |   —   | 🔵-1.6 | 🟠1.5 |
| Tormenta geomagnética en las últimas 7 | ⬜0.8 | 🔵0.5 | 🔵0.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.9 | 🔴5.0 | 🔴3.3 | 🔴4.5 |
| Índice Kp promedio | 🔵0.6 | 🔵0.8 | 🔵0.1 | 🔵0.1 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | 🔴3.5 | 🟠1.9 | 🔴2.0 |
| Índice Kp máximo (tormenta geomagnétic | 🔵0.7 | ⬜0.9 | 🔵0.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.9 | 🔴3.1 | 🔴2.0 | 🟠2.0 |
| Erupciones registradas en la ventana | 🟡1.5 | 🟡1.5 | 🟠1.6 | 🔴2.7 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | 🔵0.6 | ⬜0.9 | 🔵0.6 |
| Gas volcánico SO₂ (90 días) | ⬜1.0 | 🟡1.5 | 🟠1.7 | 🔴2.5 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜1.1 | ⬜1.1 | ⬜1.0 |
| Erupciones (90 días) | 🟡1.3 | ⬜0.9 | 🔴2.4 | 🔵0.5 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | ⬜1.0 | ⬜1.2 |

## 🏆 Top 10 patrones del sistema

> Los **patrones más vistos** en 32 años de historia: firmas que el sistema reconoció más veces antes de un evento. Cuantas más repeticiones, más confiable es el patrón como señal. El **aviso** es el tiempo de anticipación típico que esa firma da antes del evento.

| # | Evento | Bot | Zona / Nodo | Veces | Estado | Aviso |
|---|---|---|---|---|---|---|
| 1 | 🌎 **SISMO_M4** | alfa1 | Filipinas | 12,250 | ✅ consolidada | — |
| 2 | 🌎 **SISMO_M4** | loki | Mid-Atlantic Ridge | 10,544 | ✅ consolidada | — |
| 3 | 🌎 **SISMO_M4** | alfa1 | Ghost Anatolia E | 8,831 | ✅ consolidada | — |
| 4 | 🌎 **SISMO_M4** | alfa1 | Ghost Aleutian W | 8,369 | ✅ consolidada | — |
| 5 | 🌎 **SISMO_M4** | alfa1 | Ghost Mid-Atlantic S | 8,225 | ✅ consolidada | — |
| 6 | 🌎 **SISMO_M4** | alfa1 | Ghost NZ-Hikurangi | 7,300 | ✅ consolidada | — |
| 7 | 🌎 **SISMO_M4** | omega | Ghost Scotia Arc | 7,117 | ✅ consolidada | — |
| 8 | 🌎 **SISMO_M4** | alfa1 | Ghost Sulawesi | 7,086 | ✅ consolidada | — |
| 9 | 🌎 **SISMO_M4** | alfa1 | Himalaya Nepal | 6,919 | ✅ consolidada | — |
| 10 | 🌎 **SISMO_M4** | loki | Ghost Scotia Arc | 6,693 | ✅ consolidada | — |

## 📊 Patrones por tipo de evento — top 5 por clase

> Para cada tipo de evento que el sistema ha aprendido, las 5 firmas más consolidadas: los patrones más reconocibles que preceden a ese tipo de evento. La **zona** es el nodo de la malla UVG-125 donde se aprendió la firma.

### 🌋 ERUPCION_VEI3

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Baja California Sur (24.1, -110.0) | 102 | ✅ consolidada | — |
| alfa1 | GeoBat Guerrero Sulfuros (17.3, -100.2) | 83 | ✅ consolidada | — |
| beta1 | Baja California Sur (24.1, -110.0) | 81 | ✅ consolidada | — |
| beta2 | Ghost Puebla-Veracruz (19.0, -97.5) | 79 | ✅ consolidada | — |
| loki | Ghost Puebla-Veracruz (19.0, -97.5) | 77 | ✅ consolidada | — |

### 🌋 ERUPCION_VEI4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Baja California Sur (24.1, -110.0) | 52 | ✅ consolidada | — |
| beta1 | Baja California Sur (24.1, -110.0) | 32 | ✅ consolidada | — |
| loki | Grecia Helénica (37.0, 22.0) | 31 | ✅ consolidada | — |
| omega | Perú Subducción (-12.0, -77.0) | 28 | ✅ consolidada | — |
| omega | Grecia Helénica (37.0, 22.0) | 25 | ✅ consolidada | — |

### 🌋 ERUPCION_VEI5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
| beta1 | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
| omega | Grecia Helénica (37.0, 22.0) | 1 | 🆕 nueva | — |
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
| alfa1 | Filipinas (14.5, 121.0) | 12,250 | ✅ consolidada | — |
| loki | Mid-Atlantic Ridge (30.0, -42.0) | 10,544 | ✅ consolidada | — |
| alfa1 | Ghost Anatolia E (38.0, 42.0) | 8,831 | ✅ consolidada | — |
| alfa1 | Ghost Aleutian W (52.0, 175.0) | 8,369 | ✅ consolidada | — |
| alfa1 | Ghost Mid-Atlantic S (10.0, -40.0) | 8,225 | ✅ consolidada | — |

### 🌎 SISMO_M5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | GeoBat Turquía Geotermal (38.5, 29.0) | 3,696 | ✅ consolidada | — |
| alfa1 | Centroamérica (13.0, -88.0) | 3,304 | ✅ consolidada | — |
| alfa1 | Ghost Chile S (-42.0, -73.0) | 3,208 | ✅ consolidada | — |
| loki | Ghost Sumatra-Java (-4.0, 104.0) | 3,036 | ✅ consolidada | — |
| alfa1 | Ghost Vanuatu (-16.0, 168.0) | 2,787 | ✅ consolidada | — |

### 🌎 SISMO_M6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Centroamérica (13.0, -88.0) | 444 | ✅ consolidada | — |
| alfa1 | GeoBat PNG Rabaul (-4.3, 152.2) | 404 | ✅ consolidada | — |
| alfa1 | Ghost Nankai-Tokai (34.5, 138.0) | 395 | ✅ consolidada | — |
| omega | GeoBat PNG Rabaul (-4.3, 152.2) | 394 | ✅ consolidada | — |
| alfa1 | Ghost Kamchatka-Kuril (48.0, 153.0) | 340 | ✅ consolidada | — |

### 🌎 SISMO_M7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | Ghost Vanuatu (-16.0, 168.0) | 111 | ✅ consolidada | — |
| alfa1 | GeoBat Japón Nankai Fluidos (33.5, 136.0) | 101 | ✅ consolidada | — |
| alfa1 | Tonga-Kermadec (-20.0, -175.0) | 87 | ✅ consolidada | — |
| omega | GeoBat Japón Nankai Fluidos (33.5, 136.0) | 78 | ✅ consolidada | — |
| loki | Ghost East Pacific Rise S (-15.0, -113.0) | 39 | ✅ consolidada | — |

### ☀️ TORMENTA_Kp6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | global | 3 | 🔁 recurrente | — |
| alfa1 | global | 2 | 🆕 observada | — |
| alfa1 | global | 2 | 🆕 observada | — |
| padre | global | 2 | 🆕 observada | — |
| beta1 | global | 2 | 🆕 observada | — |

### ☀️ TORMENTA_Kp7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 6 | ✅ consolidada | — |
| alfa1 | global | 5 | ✅ consolidada | — |
| alfa1 | global | 5 | ✅ consolidada | — |
| omega | global | 3 | 🔁 recurrente | — |
| alfa1 | global | 3 | 🔁 recurrente | — |

### ☀️ TORMENTA_Kp9

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| alfa1 | global | 9 | ✅ consolidada | — |
| beta1 | global | 5 | ✅ consolidada | — |
| alfa1 | global | 4 | 🔁 recurrente | — |
| beta1 | global | 4 | 🔁 recurrente | — |
| beta1 | global | 3 | 🔁 recurrente | — |

## 🔀 Orden de los precursores — ¿importa la secuencia?

> El Padre también observa el **orden** en que se activaron los dominios en la víspera de cada evento (¿primero el gas y luego los sismos, o al revés?) y discierne contando: si una secuencia domina claramente, el orden IMPORTA; si las permutaciones se reparten parejo, es INDIFERENTE — lo que pesa es la convergencia, no la coreografía.

| Conjunto de dominios | Casos | Secuencia dominante | % | Veredicto |
|---|---:|---|---:|---|
| COSMICO+DESGAS+SISMICO | 100 | DESGAS+SISMICO→COSMICO | 24% | **INDIFERENTE** |
| COSMICO+SISMICO | 94 | SISMICO→COSMICO | 38% | **INDIFERENTE** |
| COSMICO+DESGAS+FINANCIERO+SISMICO | 55 | DESGAS+FINANCIERO+SISMICO→COSMICO | 20% | **INDIFERENTE** |

## 🌐 Cimática: cómo se mueve la energía por la malla

> Más allá de *qué* nodos se activan, importa **en qué orden** espacial — la ruta por la que la energía se propaga antes de un evento. Una ruta que se repite ante **distintos tipos** de evento es **GLOBAL**: confirma una cimática organizada, un sistema liberando energía con precursores y gatillos identificables. Una ruta ligada a un solo tipo es **LOCAL** — una causa específica de ese nodo o región.

**8** de las 8 rutas recurrentes mostradas son globales (cimática organizada).

| Ruta de propagación | Apariciones | Tipos de evento | Alcance |
|---|---:|---:|---|
| nodo26>nodo84>nodo96 | 20 | 3 | 🌐 **GLOBAL** |
| nodo26>nodo83>nodo96 | 14 | 3 | 🌐 **GLOBAL** |
| nodo26>nodo84>nodo97 | 14 | 3 | 🌐 **GLOBAL** |
| nodo26>nodo64>nodo84 | 13 | 2 | 🌐 **GLOBAL** |
| nodo83>nodo96>nodo26 | 13 | 2 | 🌐 **GLOBAL** |
| nodo26>nodo84>nodo93 | 12 | 2 | 🌐 **GLOBAL** |
| nodo26>nodo83>nodo84 | 11 | 3 | 🌐 **GLOBAL** |
| nodo84>nodo96>nodo26 | 11 | 2 | 🌐 **GLOBAL** |

## ⚖️ El Juez — auditoría independiente

> El Juez es un auditor que **nunca predice**: solo registra cada aviso de los bots y, cuando se cierra la ventana de 72 horas, lo compara contra el catálogo sísmico real (USGS) y dicta sentencia. Dejar pasar un evento castiga 10 veces más que una falsa alarma — preferimos un sistema nervioso a uno dormido. **Solo la fase viva puntúa asertividad**; el resto es bitácora de entrenamiento y no se mezcla.

**Operación viva (lo que cuenta):**
- ACIERTO — avisó y el evento ocurrió: 15,015
- FALLO — el evento ocurrió sin aviso (lo más castigado): 72
- FALSO POSITIVO — avisó y no pasó nada: 942
- PENDIENTE — ventana de 72h aún abierta: 306

**Bitácora de entrenamiento (reconocimiento/backtest/trasfondo — no puntúa):**
- ACIERTO: 965,130
- FALLO: 100

## 🧾 Bitácora del sistema — versión, cambios y salud

> No solo el planeta: el propio Sentinel deja traza. Cada corte registra versión, pesos y métricas, y se compara con el corte anterior — así se ve si un cambio mejoró o empeoró el comportamiento, y los post-mortems tienen base.

| Campo | Este corte | Corte anterior | Cambio |
|---|---|---|---|
| Versión del modelo | 2.5.4 | 2.5.4 | sin cambio |
| Asertividad viva | 93.7% | 93.7% | +0.0% |
| Aciertos / Fallos (vivos) | 15,015 / 72 | 15,015 / 72 | +0 aciertos |
| Pendientes de auditoría | 306 | 306 | +0 |
| Pesos de bots | 7 bots | — | beta2 1.35→1.29 |

*Asertividad viva, últimos cortes: 94% → 94% → 94% → 94% → 94%*


## ✅ Aciertos y Predicciones Correctas

> El sistema también tiene victorias que celebrar. Esta sección documenta cuándo nuestras predicciones fueron correctas: eventos que anticipamos, qué tan bien los predijimos, y cuántos días antes vimos el patrón.

### 📊 Resumen — Últimos 30 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 15015 |
| **Fallos** | 72 |
| **Falsos positivos** | 942 |
| **Tasa de acierto** | 91.9% `▓▓▓▓▓▓▓▓▓▓▓░` |
| **Total predicciones** | 16335 |

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación (días) |
|-----|----------|------|-----------|----------------------|
| alfa2 | 1773/1781 | 100% `▓▓▓▓▓▓▓▓` | 0.00 | 0.1 |
| beta2 | 1773/1781 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| delta | 1773/1781 | 100% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1 |
| loki | 1773/1781 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| omega | 1728/1781 | 97% `▓▓▓▓▓▓▓▓` | 0.35 | 0.1 |
| beta1 | 1652/1781 | 93% `▓▓▓▓▓▓▓░` | 0.31 | 0.1 |
| padre | 1644/1781 | 92% `▓▓▓▓▓▓▓░` | 0.16 | 0.1 |
| jupiter | 1591/1781 | 89% `▓▓▓▓▓▓▓░` | 0.23 | 0.1 |
| alfa1 | 1308/1781 | 73% `▓▓▓▓▓▓░░` | 0.42 | 0.1 |

### 🎯 Eventos Predichos Correctamente (más recientes primero)

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 25.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 0.0% `░░░░░░░░░░`
- **Fase:** viva

#### DELTA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### BETA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### BETA1 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### PADRE — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:10 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:05 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:05 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 25.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-20 18:05 UTC
- **Evento real:** 2026-09-20 20:14 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 0.0% `░░░░░░░░░░`
- **Fase:** viva

_... y 15005 aciertos más en los últimos 30 días_

---
*Todos los datos provienen de fuentes públicas oficiales (NOAA, USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección civil: es investigación de precursores en curso.*

*Ciclos totales: 2,911 · Sentinel Omega · Fractal Core Research*
