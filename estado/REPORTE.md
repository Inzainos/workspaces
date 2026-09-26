# 🌍 Sentinel Omega — Estado del Sistema

**Generado:** 2026-09-26 16:39 UTC (10:39 UTC-6)

> **¿Qué es esto?** Sentinel Omega es un sistema que vigila señales físicas del planeta (campo magnético solar, resonancia de la Tierra, actividad sísmica, gases volcánicos, incluso el nerviosismo de los mercados) buscando *precursores*: condiciones que en 32 años de historia han aparecido **antes** de eventos naturales fuertes. No predice con certeza — reconoce parecidos con el pasado y avisa cuando el presente se parece demasiado a los días previos a un evento. Este reporte es una foto de lo que el sistema ve ahora.

## 📡 Último ciclo — lo que el sistema midió hace un momento

> El **Fantasma** es el termómetro principal: combina en un solo número la agitación del campo magnético, el viento solar y la resonancia de la Tierra. Verde 🟢 <12 = calma · Amarillo 🟡 12-29 · Naranja 🟠 29-78 · Rojo 🔴 ≥78 = condiciones muy cargadas. Umbrales recalibrados el 25-sep sobre 280.942 lecturas (percentiles 50/90/98): los de antes dejaban el 69,8 % en amarillo y el verde era inalcanzable. El **Muro de los 5** son cinco frentes de vigilancia (tierra, atmósfera, océano, sol, mercados); si 3 o más se activan a la vez, distintos dominios físicos están alterados al mismo tiempo — eso casi nunca es coincidencia.

| Métrica | Valor | Lectura |
|---|---|---|
| Fantasma | 🟢 **9.9** `▓▓░░░░░░░░` | calma |
| Consenso de los 6 bots | NEUTRAL (20%) | evaluando |
| Muro de los 5 frentes | 2/5 activos | estable — sin convergencia crítica |
| Precursores detectados | 2 | ["SILENT_TRIGGER", "SEISMIC_CLUSTER"] |
| Hora de la medición | 2026-09-26 14:25 UTC | |

### De qué está hecho ese número

| Término | Aporte | |
|---|---:|---|
| Bz² (Bz = 3.6 nT) | 12.8 | ⚠️ **Bz NORTE**: esta orientación *suprime* el acoplamiento con la magnetosfera, pero el índice la puntúa igual que la sur porque eleva al cuadrado el valor absoluto |
| Viento solar (482 km/s) × 0,02 | 9.6 | piso permanente: el viento nunca baja de ~300 km/s |
| Schumann × 1,5 | ≤ 1,5 | como mucho un 4-10 % del total |

*El viento solar solo ya aporta 9.6, y con el umbral VERDE en 5 que había hasta el 25-sep eso bastaba para salir de verde siempre: VERDE salió **6 veces en 280.942 lecturas** y el 69,8 % del histórico caía en amarillo. Los umbrales se recalibraron a los percentiles 50/90/98 de la distribución real (12 / 29 / 78), y ahora reparten 50/40/8/2 %. La discriminación sigue siendo DÉBIL: en el tramo rojo la tasa de M7+ a 72 h es 13,1 % contra 10,7 % en verde, o sea 1,22x. Leerlo así.*

🔎 **Con este Bz norte, el índice marca 22.4; contando solo el Bz sur marcaría 9.6.** Medido: el 49 % del 5 % de lecturas más altas del histórico viene de Bz norte, o sea de la orientación tranquila.

## 🚦 Semáforo — reglas fijas del nivel de riesgo

> Estas reglas son **cuantitativas y fijas** (revisables por versión, no por ciclo): con los números de arriba cualquiera puede inferir el nivel sin interpretación subjetiva. La fila marcada ➡ es la que dispara hoy.

| Nivel | Regla (se evalúa de abajo hacia arriba) | Acción interna |
|---|---|---|
| 🔴 ROJO | Muro ≥3/5 (breach) **y** Fantasma ≥78 | Escalamiento interno |
| 🟠 NARANJA | Muro ≥3/5 (breach) **o** (Fantasma ≥29 y firma ≥85%) | Revisión manual inmediata |
| ➡ 🟡 AMARILLO | Fantasma 12–29 **o** firma ≥80% | Vigilancia reforzada |
| 🔵 AZUL | Fantasma <12 con detecciones o muros 1–2 | Seguimiento ampliado |
| 🟢 VERDE | Fantasma <12, muro 0/5, sin firmas ≥80% | Monitoreo base |

**Nivel del corte: 🟡 AMARILLO** — con Fantasma 9.9, muro 2/5 y firma máxima 100%.

## 📈 Operación reciente — hoy vs cómo solía estar

> La foto de arriba, puesta en contexto: ¿este corte está por encima, en el promedio o por debajo de la actividad usual de las últimas semanas? El **percentil** dice qué fracción de los cortes recientes fue igual o menor que hoy (P75 = hoy es más alto que el 75% del último mes).

| Métrica | Actual | Prom. 7d | Prom. 30d | Máx 30d | Percentil |
|---|---:|---:|---:|---:|---:|
| Fantasma | 9.9 | 12.3 | 21.1 | 62.3 | P12 |
| Muro de los 5 | 2 | 0.4 | 0.9 | 3 | P98 |
| Silent Trigger | activo | 35% ciclos | 37% ciclos | — | — |
| Asertividad viva | 93% | 89% | — | — | — |

*Los promedios de 30 días combinan los ciclos conservados y el resumen diario del barrido (lo compactado no se pierde, se resume).*

## 🎯 ¿Le ganamos a alertar siempre? — línea base de Molchan

> La prueba de honestidad definitiva: un bot sin cerebro que alerta SIEMPRE acierta cada vez que hay un sismo cerca de la malla en la ventana de 72 h. Su tasa de acierto es la **tasa base**. Solo si el sistema supera esa tasa hay habilidad real; si no, el número bonito es geografía, no predicción.

| Métrica | Valor | Qué dice |
|---|---:|---|
| Ventanas evaluadas (viva) | 20979 | |
| Ventanas con evento real (**tasa base**) | 1.6% | el piso a superar |
| Ventanas en alarma | 1247 (5.9%) | cuánto tiempo el sistema se moja |
| Eventos detectados | 20 de 333 (6.0%) | de los eventos reales, cuántos vio |
| **Precisión de la alarma** | 1.6% | de sus alarmas, cuántas tenían evento |
| **Ganancia** (precisión ÷ tasa base) | 1.01× | 1× = no aporta nada |
| Diagonal de Molchan (perdidos + alarma) | 0.999 | 1.000 = sin habilidad; menos = habilidad |

**Veredicto:** 🟡 ganancia marginal sobre alertar a ciegas

### Lo mismo, contado por EPISODIOS

> La tabla de arriba cuenta CICLOS, y los ciclos se solapan: el sistema mide cada 5 minutos con una ventana de 2 horas, así que un solo sismo confirma hasta 24 predicciones seguidas y una alarma sostenida se cuenta como decenas de falsas alarmas. Un episodio es una racha de alarmas; un evento, un sismo. **Esta es la cuenta honesta.**

| | contado por ciclos | contado por episodios |
|---|---:|---:|
| Alarmas | 1247 | 9 |
| Eventos | 333 | **3** |
| Precisión de la alarma | 1.6% | 11.1% |

🔴 **Sin evidencia para concluir nada.** Hacen falta 20 episodios de evento distintos y hay **3**. Cualquier ganancia calculada con esta muestra es ruido: los números de arriba describen lo que pasó, no miden habilidad. Por eso el peso por mérito de los bots se queda quieto hasta que haya con qué juzgarlos.

### La asertividad, en su sitio

> Este es el número que conviene no leer solo: cuenta como acierto cada «dije calma y hubo calma», y la calma es casi todo. Al lado va lo que sacaría un bot MUDO, que nunca abre la boca. Si el mudo empata o gana, la asertividad no es habilidad.

| | Asertividad | Coste con las severidades del Juez |
|---|---:|---:|
| Sistema | 92.7% | 4357 |
| Bot MUDO (nunca alarma) | 98.4% | 3330 |
| Bot ALARMISTA (siempre alarma) | 1.6% | 20646 |

*El coste pesa cada FALLO (callarse y que pase algo) ×10 y cada falsa alarma ×1, las severidades del propio Juez: castigar el silencio al décuplo es deliberado, para que los bots no se acostumbren a callar. Menos coste es mejor.*

*Esa asimetría fija el **umbral de rentabilidad de una alarma**: alarmar sale a cuenta cuando la probabilidad de evento en la ventana supera 9.1%. Hoy las alarmas se disparan con un 1.6%, que es 6 veces menos.*

*Con 50 nodos reales y radio de 5°, casi toda ventana de 72 h tiene un M4.5+ cerca de algún nodo: para ganar de verdad, las predicciones tendrán que volverse específicas por nodo, no globales.*

## 🔭 Detecciones recientes — las señales individuales

> Cada fila es una señal concreta que el escáner encontró en los datos: una perturbación magnética, un enjambre sísmico, un pico de gas volcánico… La **confianza** dice qué tan clara fue la señal (no la probabilidad de un evento). Una detección aislada es normal; varias juntas de tipos distintos es lo que sube el riesgo.

| Precursor | Confianza | Zona |
|---|---|---|
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 80% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 80% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 80% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 80% `▓▓▓▓░` | global |

## 🎯 Firma Match — la memoria reconoce el momento actual

> Esta es la parte más importante del reporte. Durante el entrenamiento, el sistema estudió los **14 días previos** a cada sismo fuerte de los últimos 32 años y guardó el 'rostro' de esas vísperas como una **firma**. Aquí compara el estado actual del planeta contra esa memoria. Un match del 84% significa: *lo que estamos viendo hoy se parece en un 84% a cómo se veían los días previos a ese tipo de evento*. **Veces vista** = cuántas veces esa misma firma precedió a un evento real en el histórico — a más repeticiones, más confiable el parecido.

| Parecido | Precedió a | Zona (nodo de la malla) | Veces vista | Suele avisar con |
|---|---|---|---|---|
| **100%** `▓▓▓▓▓` | SISMO_M5 | **Ghost Banda Sea** (-5.0, 130.0) · nodo 83 | 71 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M4 | **Ghost Tonga-Fiji** (-18.0, -178.0) · nodo 64 | 291 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M6 | **GeoBat Sumatra Hidrotermal** (1.0, 98.0) · nodo 109 | 8 | ~8 días |
| **93%** `▓▓▓▓▓` | SISMO_M4 | **Tonga-Kermadec** (-20.0, -175.0) · nodo 26 | 27 | ~6 días |
| **91%** `▓▓▓▓▓` | SISMO_M4 | **Ghost Tonga-Fiji** (-18.0, -178.0) · nodo 64 | 68 | ~6 días |

*SISMO_M5 / M6 / M7 = sismo de magnitud 5+, 6+ o 7+. La zona es el punto de la malla global UVG-125 donde se aprendió la firma (nombre y coordenadas lat, lon); los nodos 'Ghost' son puntos teóricos de la malla sin estación física encima.*

## 🕐 Ventana temporal activa (muro de lags)

> Varias firmas independientes convergen en las MISMAS fechas. La ventana se fijó al **detectarla** y el contador **baja** cada ciclo mientras la señal persiste — no se re-proyecta desde hoy.

- **Faltan ~2–7 días** (ventana 2026-09-28 → 2026-10-03)
- Detectada hace **2 días** · clases: SISMO_M4, SISMO_M5, SISMO_M6

## ⏱ Anticipación — con cuánto tiempo suele avisar

> Medido sobre el histórico: ¿cuántos días **antes** del evento ya era reconocible su firma? No es un cronómetro exacto — es el promedio de lo que ha pasado. El hallazgo contraintuitivo: **los eventos más grandes avisan con más tiempo**. Un M7 se 'carga' durante más días que un M5.

| Evento | Aviso promedio | Máximo | Mínimo | Casos medidos |
|---|---|---|---|---|
| ERUPCION_VEI3 | **6.8 días** | 14.0 d | 1.0 d | 73 |
| ERUPCION_VEI4 | **2.6 días** | 10.0 d | 1.0 d | 24 |
| SISMO_M3_obs | **9.0 días** | 10.0 d | 7.0 d | 3 |
| SISMO_M4 | **6.3 días** | 14.0 d | 1.0 d | 111 |
| SISMO_M4_obs | **8.5 días** | 14.0 d | 1.0 d | 8 |
| SISMO_M5 | **6.0 días** | 14.0 d | 1.0 d | 118 |
| SISMO_M6 | **8.2 días** | 14.0 d | 1.0 d | 127 |
| SISMO_M7 | **9.4 días** | 14.0 d | 1.0 d | 14 |

*Medición in-sample sobre 32 años de histórico; la ventana de estudio llega a 14 días, así que los máximos pueden estar recortados.*

## 🔍 ¿Qué acelera o retrasa un evento?

> Comparamos las firmas que avisaron con **poco** tiempo (rápidas) contra las que avisaron con **mucho** (lentas). El patrón que salió: cuando hay tormenta geomagnética, el evento llega pronto — *la tormenta precipita*. Cuando el espacio está en calma, la corteza se carga despacio y avisa con más días — *la calma carga*.

| Variable | En firmas rápidas | En firmas lentas | Qué indica |
|---|---|---|---|
| Campo magnético solar (Bz promedio) | 0.03 | -0.05 | más presente cuando el evento llega PRONTO |
| Campo magnético solar (Bz, últimas 72h) | 0.06 | -0.05 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ en la ventana (kilotones) | 89.10 | 5.06 | más presente cuando el evento llega PRONTO |
| Sismos en las últimas 72h | 4.15 | 1.60 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ (90 días) | 203.50 | 89.04 | más presente cuando el evento llega PRONTO |
| es_sicigia | 0.27 | 0.14 | más presente cuando el evento llega PRONTO |

*Rápidas = tercio de firmas con menor anticipación; lentas = tercio con mayor.*

## 🧠 Memoria entrenada — lo que el sistema ya aprendió

> El sistema son **7 bots especializados**: `alfa1` vigila el clima espacial (30 años), `beta1` la resonancia Schumann — el latido electromagnético de la Tierra (30 años), `alfa2` los satélites Sentinel (aprende en vivo, sin backcast), `beta2` la desgasificación volcánica y la atmósfera (14 años), `delta` el humor de los mercados (10 años), `jupiter` la atención colectiva sobre tormentas solares (en vivo), y `padre` arbitra entre todos. Cada uno guarda sus propias **firmas** (patrones de vísperas de evento). El **peso** es su credibilidad ante el padre: 1.00 = normal; baja cuando falla y se recupera cuando acierta; puede superar 1.00 solo si detectó algo que el padre dejó pasar. `alfa2` y `jupiter` acumulan sus firmas desde los ciclos operativos, no desde el backcast histórico.

| Bot | Firmas aprendidas | Veces confirmadas | Credibilidad |
|---|---|---|---|
| alfa1 | 1,632 | 187,270 | 1.42 `▓▓▓▓▓▓` |
| beta1 | 994 | 187,477 | 1.42 `▓▓▓▓▓▓` |
| beta2 | 809 | 96,692 | 1.35 `▓▓▓▓▓░` |
| delta | 676 | 65,394 | 1.29 `▓▓▓▓▓░` |
| jupiter | 21 | 1,691 | 0.86 `▓▓▓░░░` |
| loki | 898 | 75,073 | 1.29 `▓▓▓▓▓░` |
| omega | 304 | 187,477 | 1.42 `▓▓▓▓▓▓` |
| padre | 14,286 | 187,477 | 0.94 `▓▓▓▓░░` |
| alfa2 | _en vivo · 22 ciclos · 3062 pases observados_ | — | 1.00 `▓▓▓▓░░` |

## 🎯 Asertividad — ¿qué tan bien le ha ido?

> Tres formas de medir lo mismo. **Histórica**: al repasar los 32 años de datos como examen, ¿reconoció las vísperas de los eventos que ya sabemos que ocurrieron? **Viva**: desde que opera en tiempo real, cada aviso queda registrado y un auditor independiente (el Juez) lo califica 72 horas después contra los sismos que realmente ocurrieron — sin trampa posible. **7 días**: lo mismo, pero solo la última semana. La viva empieza en '—' hasta que las primeras ventanas de 72h se cierran.

| Métrica | Valor |
|---|---|
| **Histórica** (examen sobre 32 años) | 98.0% |
| **Viva** (operación real, auditada) | 92.7% |
| **Últimos 7 días** (viva) | 89.2% |

### Por bot

| Bot | Histórica | Viva | Viva 7d | Credibilidad |
|---|---|---|---|---|
| alfa1 | 97.9% | 69.2% | 55.1% | 1.42 |
| alfa2 | — | 98.4% | 94.8% | 1.00 |
| beta1 | 98.2% | 92.8% | 93.0% | 1.42 |
| beta2 | 97.2% | 98.8% | 96.6% | 1.35 |
| delta | 99.6% | 98.4% | 94.8% | 1.29 |
| jupiter | 98.2% | 89.1% | 87.7% | 0.86 |
| loki | 98.3% | 98.4% | 94.8% | 1.29 |
| omega | 98.0% | 96.1% | 93.0% | 1.42 |
| padre | 98.0% | 92.5% | 93.2% | 0.94 |

*La histórica mide reconocimiento de patrones dentro de los mismos datos con que se entrenó (por eso es tan alta). La viva es la prueba honesta: predicciones a futuro calificadas contra la realidad.*

## 🪞 Realidad vs fantasía — el sesgo de aprendizaje

> La asertividad histórica alta es *in-sample*: el bot reconoce las firmas con las que se entrenó (comodidad). La columna **Causal (real)** mide lo honesto: ¿reconoció el evento con la memoria que ya tenía **antes** de que ocurriera? El **sesgo** es la diferencia — cuánto de esa competencia era fantasía. Aunque el número real sea más bajo, es la verdad.

| Bot | In-sample | **Causal (real)** | Sesgo (fantasía) |
|---|---|---|---|
| beta2 | 98.2% | **51.4%** | +46.9% ⚠️ |
| delta | 99.4% | **87.4%** | +11.9% |
| padre | 99.8% | **99.0%** | +0.8% ✅ |
| beta1 | 100.0% | **99.8%** | +0.2% ✅ |
| omega | 100.0% | **99.8%** | +0.2% ✅ |
| loki | 39.9% | **39.6%** | +0.2% ✅ |
| alfa1 | 100.0% | **100.0%** | +0.0% ✅ |
| jupiter | 0.8% | **0.8%** | +0.0% ✅ |
| alfa2 | — | **—** | — |

*Sesgo < 5% = el bot generaliza de verdad. Sesgo alto = su competencia era comodidad in-sample; su decisión real es más floja de lo que aparentaba.*

## 🗺 Correlaciones aprendidas — qué precede a cada evento

> Mapa de calor: qué tan elevada está cada variable en los **14 días previos** a cada tipo de evento comparado con su nivel habitual. 🔴≥2× · 🟠≥1.5× · 🟡≥1.2× · ⬜~normal · 🔵↓bajo. Un 🔴 en 'SO₂' para 'ERUPCION_VEI4' significa que justo antes de esas erupciones el SO₂ estaba el doble de lo normal. Un 🔵 en 'Kp' para 'SISMO_M7' confirma el Silent Trigger: los grandes sismos a veces ocurren en calma geomagnética.

| Variable | 🌋VEIVEI3 | 🌋VEIVEI4 | 🌋VEIVEI5 | M3_obs | M4 | M4_obs | M5 | M6 | M7 | ☀️KpKp6 | ☀️KpKp7 | ☀️KpKp9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Campo magnético solar (Bz, últimas 72h | 🔴2.4 | 🔵-4.2 | 🔵0.4 | 🔵-47.2 | ⬜1.0 | 🔵-68.6 | 🔵0.7 | 🟠1.9 | ⬜1.1 | 🔴48.8 | 🔴2.3 | 🔴5.2 |
| Campo magnético solar (Bz promedio) | 🔵-0.2 | 🔵-0.7 | 🔵-2.5 | 🔵-26.5 | ⬜1.1 | 🔵-31.9 | ⬜1.0 | 🟡1.3 | 🔵0.7 | 🔴16.0 | 🔴7.0 | 🔴3.1 |
| Rendimiento de Bitcoin en la ventana | 🟠1.6 | 🔴2.4 | 🔵-3.7 |   —   | ⬜0.9 |   —   | ⬜1.0 | ⬜1.2 | ⬜0.9 |   —   | 🔵-1.5 | 🟡1.5 |
| Gas volcánico SO₂ en la ventana (kilot | ⬜1.0 | 🔴2.8 | 🔴2.3 | 🔴4.1 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜0.9 | 🔵0.7 | 🔵0.7 | 🔵0.6 | ⬜0.9 |
| Erupciones (90 días) | 🟡1.3 | ⬜0.9 | 🔴2.4 | 🔵0.7 | ⬜1.0 | ⬜0.8 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | ⬜1.0 | 🟡1.2 |
| lod | 🔵0.8 | ⬜1.1 | 🔵-0.3 | 🔵0.5 | ⬜1.0 | 🔵0.3 | ⬜1.0 | ⬜1.0 | ⬜1.1 | 🟡1.2 | 🟠1.6 | 🟡1.3 |
| Erupciones registradas en la ventana | 🟡1.4 | 🟠1.6 | 🟠1.6 | 🔵0.7 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | 🔵0.6 | ⬜0.9 | 🔵0.6 |
| es_sicigia | ⬜0.8 | ⬜1.0 | 🔵0.0 | 🔵0.0 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜0.9 | 🔵0.7 | ⬜0.9 | 🟡1.2 | 🔵0.8 |

## 🏆 Top 10 patrones del sistema

> Los **patrones más vistos** en 32 años de historia: firmas que el sistema reconoció más veces antes de un evento. Cuantas más repeticiones, más confiable es el patrón como señal. El **aviso** es el tiempo de anticipación típico que esa firma da antes del evento.

| # | Evento | Bot | Zona / Nodo | Veces | Estado | Aviso |
|---|---|---|---|---|---|---|
| 1 | 🌎 **SISMO_M4** | omega | Ghost Mariana | 12,434 | ✅ consolidada | — |
| 2 | 🌎 **SISMO_M4** | omega | Ghost Banda Sea | 8,742 | ✅ consolidada | — |
| 3 | 🌎 **SISMO_M4** | omega | Ghost Kamchatka-Kuril | 8,150 | ✅ consolidada | — |
| 4 | 🌎 **SISMO_M4** | omega | Ghost Philippines-Taiwan | 7,926 | ✅ consolidada | — |
| 5 | 🌎 **SISMO_M4** | omega | Ghost Scotia Arc | 6,849 | ✅ consolidada | — |
| 6 | 🌎 **SISMO_M4** | omega | Filipinas | 6,785 | ✅ consolidada | — |
| 7 | 🌎 **SISMO_M4** | omega | Ghost Alaska-Aleutian | 6,248 | ✅ consolidada | — |
| 8 | 🌎 **SISMO_M4** | omega | Ghost Vanuatu | 5,703 | ✅ consolidada | — |
| 9 | 🌎 **SISMO_M4** | omega | Ghost Hindu Kush | 5,099 | ✅ consolidada | — |
| 10 | 🌎 **SISMO_M5** | omega | Cascadia | 4,653 | ✅ consolidada | — |

## 📊 Patrones por tipo de evento — top 5 por clase

> Para cada tipo de evento que el sistema ha aprendido, las 5 firmas más consolidadas: los patrones más reconocibles que preceden a ese tipo de evento. La **zona** es el nodo de la malla UVG-125 donde se aprendió la firma.

### 🌋 ERUPCION_VEI3

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | Baja California Sur (24.1, -110.0) | 186 | ✅ consolidada | — |
| omega | Baja California Sur (24.1, -110.0) | 149 | ✅ consolidada | — |
| beta2 | Ghost Puebla-Veracruz (19.0, -97.5) | 79 | ✅ consolidada | — |
| beta1 | GeoBat Michoacán Sulfuros (18.5, -102.5) | 54 | ✅ consolidada | — |
| omega | GeoBat Guerrero Sulfuros (17.3, -100.2) | 49 | ✅ consolidada | — |

### 🌋 ERUPCION_VEI4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | Ghost Puebla-Veracruz (19.0, -97.5) | 47 | ✅ consolidada | — |
| omega | Grecia Helénica (37.0, 22.0) | 27 | ✅ consolidada | — |
| omega | Baja California Sur (24.1, -110.0) | 26 | ✅ consolidada | — |
| omega | Ghost Puebla-Veracruz (19.0, -97.5) | 22 | ✅ consolidada | — |
| loki | Chiapas Subducción (14.8, -92.5) | 20 | ✅ consolidada | — |

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
| beta2 | Ghost Aleutian W (52.0, 175.0) | 54 | ✅ consolidada | — |
| padre | Ghost Aleutian W (52.0, 175.0) | 45 | ✅ consolidada | — |
| omega | Ghost Aleutian W (52.0, 175.0) | 44 | ✅ consolidada | — |
| beta1 | Ghost Alaska-Aleutian (55.0, -165.0) | 31 | ✅ consolidada | — |
| jupiter | Ghost Caribbean-PR (19.5, -65.0) | 28 | ✅ consolidada | — |

### 🌎 SISMO_M4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Mariana (15.0, 147.0) | 12,434 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 8,742 | ✅ consolidada | — |
| omega | Ghost Kamchatka-Kuril (48.0, 153.0) | 8,150 | ✅ consolidada | — |
| omega | Ghost Philippines-Taiwan (20.0, 122.0) | 7,926 | ✅ consolidada | — |
| omega | Ghost Scotia Arc (-57.0, -30.0) | 6,849 | ✅ consolidada | — |

### 🌎 SISMO_M4_obs

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta2 | Ghost Ryukyu (26.0, 128.0) | 87 | ✅ consolidada | — |
| omega | Ghost Ryukyu (26.0, 128.0) | 78 | ✅ consolidada | — |
| jupiter | Etna-Sicilia (37.8, 15.0) | 49 | ✅ consolidada | — |
| padre | Ghost Colombia Interior (4.0, -75.0) | 38 | ✅ consolidada | ~1 días |
| jupiter | Ghost Ryukyu (26.0, 128.0) | 31 | ✅ consolidada | — |

### 🌎 SISMO_M5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Cascadia (46.0, -124.0) | 4,653 | ✅ consolidada | — |
| omega | Ghost Mariana (15.0, 147.0) | 3,727 | ✅ consolidada | — |
| omega | Filipinas (14.5, 121.0) | 3,518 | ✅ consolidada | — |
| omega | Ghost Mariana (15.0, 147.0) | 3,395 | ✅ consolidada | — |
| omega | Ghost Kamchatka-Kuril (48.0, 153.0) | 3,117 | ✅ consolidada | — |

### 🌎 SISMO_M6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Banda Sea (-5.0, 130.0) | 469 | ✅ consolidada | — |
| omega | Nueva Zelanda (-41.0, 174.0) | 454 | ✅ consolidada | — |
| omega | Ghost San Andreas Mid (35.5, -119.5) | 410 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 379 | ✅ consolidada | — |
| omega | Ghost Chiapas Interior (15.5, -93.0) | 336 | ✅ consolidada | — |

### 🌎 SISMO_M7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Tonga-Fiji (-18.0, -178.0) | 110 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 77 | ✅ consolidada | — |
| omega | Filipinas (14.5, 121.0) | 58 | ✅ consolidada | — |
| omega | GeoBat Sumatra Hidrotermal (1.0, 98.0) | 51 | ✅ consolidada | — |
| beta1 | Ghost Cascadia Gap (44.0, -125.0) | 45 | ✅ consolidada | — |

### ☀️ TORMENTA_Kp6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 8 | ✅ consolidada | — |
| omega | global | 3 | 🔁 recurrente | — |
| alfa1 | global | 2 | 🆕 observada | — |
| omega | global | 2 | 🆕 observada | — |
| omega | global | 2 | 🆕 observada | — |

### ☀️ TORMENTA_Kp7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 16 | ✅ consolidada | — |
| omega | global | 8 | ✅ consolidada | — |
| omega | global | 8 | ✅ consolidada | — |
| omega | global | 4 | 🔁 recurrente | — |
| beta1 | global | 4 | 🔁 recurrente | — |

### ☀️ TORMENTA_Kp9

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta1 | global | 17 | ✅ consolidada | — |
| omega | global | 6 | ✅ consolidada | — |
| omega | global | 5 | ✅ consolidada | — |
| omega | global | 5 | ✅ consolidada | — |
| padre | global | 2 | 🆕 observada | — |

## 🔀 Orden de los precursores — ¿importa la secuencia?

> El Padre también observa el **orden** en que se activaron los dominios en la víspera de cada evento (¿primero el gas y luego los sismos, o al revés?) y discierne contando: si una secuencia domina claramente, el orden IMPORTA; si las permutaciones se reparten parejo, es INDIFERENTE — lo que pesa es la convergencia, no la coreografía.

| Conjunto de dominios | Casos | Secuencia dominante | % | Veredicto |
|---|---:|---|---:|---|
| COSMICO+DESGAS+SISMICO+SOLAR | 95 | DESGAS+SISMICO+SOLAR→COSMICO | 16% | **INDIFERENTE** |
| COSMICO+SISMICO+SOLAR | 92 | SISMICO+SOLAR→COSMICO | 28% | **INDIFERENTE** |
| COSMICO+DESGAS+FINANCIERO+SISMICO+SOLAR | 49 | DESGAS+FINANCIERO+SISMICO+SOLAR→COSMICO | 14% | **INDIFERENTE** |

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
- ACIERTO — avisó y el evento ocurrió: 19,439
- FALLO — el evento ocurrió sin aviso (lo más castigado): 313
- FALSO POSITIVO — avisó y no pasó nada: 1,227
- PENDIENTE — ventana de 72h aún abierta: 225

**Bitácora de entrenamiento (reconocimiento/backtest/trasfondo — no puntúa):**
- ACIERTO: 985,934
- FALLO: 1,267

## 🧾 Bitácora del sistema — versión, cambios y salud

> No solo el planeta: el propio Sentinel deja traza. Cada corte registra versión, pesos y métricas, y se compara con el corte anterior — así se ve si un cambio mejoró o empeoró el comportamiento, y los post-mortems tienen base.

| Campo | Este corte | Corte anterior | Cambio |
|---|---|---|---|
| Versión del modelo | 2.5.4 | 2.5.4 | sin cambio |
| Asertividad viva *(cuenta los silencios)* | 92.7% | 92.7% | -0.0% |
| **Ganancia real** (precisión ÷ tasa base) | 1.01× | — | 1× = no aporta |
| Aciertos / Fallos (vivos) | 19,439 / 313 | 19,271 / 313 | +168 aciertos |
| Pendientes de auditoría | 225 | 378 | -153 |
| Pesos de bots | 8 bots | — | alfa1 0.30→1.42; beta1 1.00→1.42; beta2 1.00→1.35; delta 1.00→1.29; jupiter 1.00→0.86; loki 1.00→1.29; omega 1.00→1.42; padre 1.00→0.94 |

*Asertividad viva, últimos cortes: 93% → 93% → 93% → 93% → 93%*

### Quién ve QUÉ — competencia por clase de evento

> Un solo número por bot aplasta al especialista. Aquí, la fracción de eventos de cada tamaño que cada bot SÍ vio. Sale de las fases que discriminan (trasfondo y viva): la de reconocimiento marca todo como acierto y no enseña nada. La flecha compara con el primer corte guardado.

| bot | M3 | M4 | M5 |
|---|---:|---:|---:|
| beta1 | 37% (22/59) | 72% (179/249) | 3% (1/29) |
| omega | 44% (26/59) | 69% (171/249) | 3% (1/29) |
| alfa1 | 31% (18/59) | 61% (152/249) | 17% (5/29) |
| padre | 49% (29/59) | 60% (149/249) | 7% (2/29) |
| beta2 | 14% (8/59) | 18% (44/249) | 38% (11/29) |
| jupiter | 5% (3/59) | 12% (29/249) | 0% (0/29) |
| loki | 3% (2/59) | 5% (13/249) | 0% (0/29) |
| delta | — | — | 0% (0/29) |
| alfa2 | — | — | 0% (0/29) |

**El mejor de cada clase:** M3 → **padre** (49%) · M4 → **beta1** (72%) · M5 → **beta2** (38%).

*El peso de cada bot en el consenso es el de su MEJOR clase: un experto que solo sirve para una cosa, sirve.*


## ✅ Aciertos y Predicciones Correctas

> El sistema también tiene victorias que celebrar. Esta sección documenta cuándo nuestras predicciones fueron correctas: eventos que anticipamos, qué tan bien los predijimos, y cuántos días antes vimos el patrón.

### 📊 Resumen — Últimos 30 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 19439 |
| **Fallos** | 313 |
| **Falsos positivos** | 1227 |
| **Tasa de acierto** | 91.7% `▓▓▓▓▓▓▓▓▓▓▓░` |
| **Total predicciones** | 21204 |

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación (días) |
|-----|----------|------|-----------|----------------------|
| beta2 | 2304/2331 | 99% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| alfa2 | 2294/2331 | 98% `▓▓▓▓▓▓▓▓` | 0.04 | 0.1 |
| delta | 2294/2331 | 98% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1 |
| loki | 2294/2331 | 98% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1 |
| omega | 2240/2331 | 96% `▓▓▓▓▓▓▓▓` | 0.34 | 0.1 |
| beta1 | 2164/2331 | 93% `▓▓▓▓▓▓▓░` | 0.31 | 0.1 |
| padre | 2157/2331 | 93% `▓▓▓▓▓▓▓░` | 0.14 | 0.1 |
| jupiter | 2078/2331 | 89% `▓▓▓▓▓▓▓░` | 0.23 | 0.1 |
| alfa1 | 1614/2331 | 69% `▓▓▓▓▓▓░░` | 0.45 | 0.1 |

### 🎯 Eventos Predichos Correctamente (más recientes primero)

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 40.0% `▓▓▓▓░░░░░░`
- **Fase:** viva

#### JUPITER — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### DELTA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### BETA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### BETA1 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 30.0% `▓▓▓░░░░░░░`
- **Fase:** viva

#### PADRE — SISMO_M5 — (Ghost Banda Sea)

- **Predicción:** 2026-09-26 12:01 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 11:56 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-26 11:56 UTC
- **Evento real:** 2026-09-26 14:04 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 40.0% `▓▓▓▓░░░░░░`
- **Fase:** viva

_... y 19429 aciertos más en los últimos 30 días_

---
*Todos los datos provienen de fuentes públicas oficiales (NOAA, USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección civil: es investigación de precursores en curso.*

*Ciclos totales: 3,371 · Sentinel Omega · Fractal Core Research*
