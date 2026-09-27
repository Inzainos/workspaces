# 🌍 Sentinel Omega — Estado del Sistema

**Generado:** 2026-09-27 08:55 UTC (02:55 UTC-6)

> **¿Qué es esto?** Sentinel Omega es un sistema que vigila señales físicas del planeta (campo magnético solar, resonancia de la Tierra, actividad sísmica, gases volcánicos, incluso el nerviosismo de los mercados) buscando *precursores*: condiciones que en 32 años de historia han aparecido **antes** de eventos naturales fuertes. No predice con certeza — reconoce parecidos con el pasado y avisa cuando el presente se parece demasiado a los días previos a un evento. Este reporte es una foto de lo que el sistema ve ahora.

## 📡 Último ciclo — lo que el sistema midió hace un momento

> El **Fantasma** es el termómetro principal: combina en un solo número la agitación del campo magnético, el viento solar y la resonancia de la Tierra. Verde 🟢 <12 = calma · Amarillo 🟡 12-29 · Naranja 🟠 29-78 · Rojo 🔴 ≥78 = condiciones muy cargadas. Umbrales recalibrados el 25-sep sobre 280.942 lecturas (percentiles 50/90/98): los de antes dejaban el 69,8 % en amarillo y el verde era inalcanzable. El **Muro de los 5** son cinco frentes de vigilancia (tierra, atmósfera, océano, sol, mercados); si 3 o más se activan a la vez, distintos dominios físicos están alterados al mismo tiempo — eso casi nunca es coincidencia.

| Métrica | Valor | Lectura |
|---|---|---|
| Fantasma | 🟢 **9.3** `▓▓░░░░░░░░` | calma |
| Consenso de los 6 bots | NEUTRAL (20%) | evaluando |
| Muro de los 5 frentes | 1/5 activos | estable — sin convergencia crítica |
| Precursores detectados | 1 | ["SEISMIC_CLUSTER"] |
| Hora de la medición | 2026-09-27 07:22 UTC | |

### De qué está hecho ese número

| Término | Aporte | |
|---|---:|---|
| Bz² (Bz = -2.7 nT) | 7.5 | Bz sur: la orientación que sí acopla |
| Viento solar (441 km/s) × 0,02 | 8.8 | piso permanente: el viento nunca baja de ~300 km/s |
| Schumann × 1,5 | ≤ 1,5 | como mucho un 4-10 % del total |

*El viento solar solo ya aporta 8.8, y con el umbral VERDE en 5 que había hasta el 25-sep eso bastaba para salir de verde siempre: VERDE salió **6 veces en 280.942 lecturas** y el 69,8 % del histórico caía en amarillo. Los umbrales se recalibraron a los percentiles 50/90/98 de la distribución real (12 / 29 / 78), y ahora reparten 50/40/8/2 %. La discriminación sigue siendo DÉBIL: en el tramo rojo la tasa de M7+ a 72 h es 13,1 % contra 10,7 % en verde, o sea 1,22x. Leerlo así.*

## 🚦 Semáforo — reglas fijas del nivel de riesgo

> Estas reglas son **cuantitativas y fijas** (revisables por versión, no por ciclo): con los números de arriba cualquiera puede inferir el nivel sin interpretación subjetiva. La fila marcada ➡ es la que dispara hoy.

| Nivel | Regla (se evalúa de abajo hacia arriba) | Acción interna |
|---|---|---|
| 🔴 ROJO | Muro ≥3/5 (breach) **y** Fantasma ≥78 | Escalamiento interno |
| 🟠 NARANJA | Muro ≥3/5 (breach) **o** (Fantasma ≥29 y firma ≥85%) | Revisión manual inmediata |
| ➡ 🟡 AMARILLO | Fantasma 12–29 **o** firma ≥80% | Vigilancia reforzada |
| 🔵 AZUL | Fantasma <12 con detecciones o muros 1–2 | Seguimiento ampliado |
| 🟢 VERDE | Fantasma <12, muro 0/5, sin firmas ≥80% | Monitoreo base |

**Nivel del corte: 🟡 AMARILLO** — con Fantasma 9.3, muro 1/5 y firma máxima 100%.

## 📈 Operación reciente — hoy vs cómo solía estar

> La foto de arriba, puesta en contexto: ¿este corte está por encima, en el promedio o por debajo de la actividad usual de las últimas semanas? El **percentil** dice qué fracción de los cortes recientes fue igual o menor que hoy (P75 = hoy es más alto que el 75% del último mes).

| Métrica | Actual | Prom. 7d | Prom. 30d | Máx 30d | Percentil |
|---|---:|---:|---:|---:|---:|
| Fantasma | 9.3 | 11.8 | 19.9 | 62.3 | P8 |
| Muro de los 5 | 1 | 0.5 | 1.0 | 3 | P71 |
| Silent Trigger | inactivo | 33% ciclos | 36% ciclos | — | — |
| Asertividad viva | 92% | 87% | — | — | — |

*Los promedios de 30 días combinan los ciclos conservados y el resumen diario del barrido (lo compactado no se pierde, se resume).*

## 🎯 ¿Le ganamos a alertar siempre? — línea base de Molchan

> La prueba de honestidad definitiva: un bot sin cerebro que alerta SIEMPRE acierta cada vez que hay un sismo cerca de la malla en la ventana de 72 h. Su tasa de acierto es la **tasa base**. Solo si el sistema supera esa tasa hay habilidad real; si no, el número bonito es geografía, no predicción.

| Métrica | Valor | Qué dice |
|---|---:|---|
| Ventanas evaluadas (viva) | 22086 | |
| Ventanas con evento real (**tasa base**) | 1.5% | el piso a superar |
| Ventanas en alarma | 1483 (6.7%) | cuánto tiempo el sistema se moja |
| Eventos detectados | 20 de 333 (6.0%) | de los eventos reales, cuántos vio |
| **Precisión de la alarma** | 1.3% | de sus alarmas, cuántas tenían evento |
| **Ganancia** (precisión ÷ tasa base) | 0.89× | 1× = no aporta nada |
| Diagonal de Molchan (perdidos + alarma) | 1.007 | 1.000 = sin habilidad; menos = habilidad |

**Veredicto:** 🔴 SIN ganancia: alertar SIEMPRE habría rendido igual o mejor — la asertividad de abajo aún no es habilidad

### Lo mismo, contado por EPISODIOS

> La tabla de arriba cuenta CICLOS, y los ciclos se solapan: el sistema mide cada 5 minutos con una ventana de 2 horas, así que un solo sismo confirma hasta 24 predicciones seguidas y una alarma sostenida se cuenta como decenas de falsas alarmas. Un episodio es una racha de alarmas; un evento, un sismo. **Esta es la cuenta honesta.**

| | contado por ciclos | contado por episodios |
|---|---:|---:|
| Alarmas | 1483 | 10 |
| Eventos | 333 | **3** |
| Precisión de la alarma | 1.3% | 10.0% |

🔴 **Sin evidencia para concluir nada.** Hacen falta 20 episodios de evento distintos y hay **3**. Cualquier ganancia calculada con esta muestra es ruido: los números de arriba describen lo que pasó, no miden habilidad. Por eso el peso por mérito de los bots se queda quieto hasta que haya con qué juzgarlos.

### La asertividad, en su sitio

> Este es el número que conviene no leer solo: cuenta como acierto cada «dije calma y hubo calma», y la calma es casi todo. Al lado va lo que sacaría un bot MUDO, que nunca abre la boca. Si el mudo empata o gana, la asertividad no es habilidad.

| | Asertividad | Coste con las severidades del Juez |
|---|---:|---:|
| Sistema | 92.0% | 4593 |
| Bot MUDO (nunca alarma) | 98.5% | 3330 |
| Bot ALARMISTA (siempre alarma) | 1.5% | 21753 |

*El coste pesa cada FALLO (callarse y que pase algo) ×10 y cada falsa alarma ×1, las severidades del propio Juez: castigar el silencio al décuplo es deliberado, para que los bots no se acostumbren a callar. Menos coste es mejor.*

*Esa asimetría fija el **umbral de rentabilidad de una alarma**: alarmar sale a cuenta cuando la probabilidad de evento en la ventana supera 9.1%. Hoy las alarmas se disparan con un 1.3%, que es 7 veces menos.*

*Con 50 nodos reales y radio de 5°, casi toda ventana de 72 h tiene un M4.5+ cerca de algún nodo: para ganar de verdad, las predicciones tendrán que volverse específicas por nodo, no globales.*

## 🔭 Detecciones recientes — las señales individuales

> Cada fila es una señal concreta que el escáner encontró en los datos: una perturbación magnética, un enjambre sísmico, un pico de gas volcánico… La **confianza** dice qué tan clara fue la señal (no la probabilidad de un evento). Una detección aislada es normal; varias juntas de tipos distintos es lo que sube el riesgo.

| Precursor | Confianza | Zona |
|---|---|---|
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |
| Patrón Silent Trigger (Calma) | 90% `▓▓▓▓░` | global |
| Enjambre Sísmico Local | 95% `▓▓▓▓▓` | regional |

## 🎯 Firma Match — la memoria reconoce el momento actual

> Esta es la parte más importante del reporte. Durante el entrenamiento, el sistema estudió los **14 días previos** a cada sismo fuerte de los últimos 32 años y guardó el 'rostro' de esas vísperas como una **firma**. Aquí compara el estado actual del planeta contra esa memoria. Un match del 84% significa: *lo que estamos viendo hoy se parece en un 84% a cómo se veían los días previos a ese tipo de evento*. **Veces vista** = cuántas veces esa misma firma precedió a un evento real en el histórico — a más repeticiones, más confiable el parecido.

| Parecido | Precedió a | Zona (nodo de la malla) | Veces vista | Suele avisar con |
|---|---|---|---|---|
| **100%** `▓▓▓▓▓` | SISMO_M5 | **Ghost Banda Sea** (-5.0, 130.0) · nodo 83 | 71 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M4 | **Ghost Tonga-Fiji** (-18.0, -178.0) · nodo 64 | 291 | ~6 días |
| **100%** `▓▓▓▓▓` | SISMO_M6 | **GeoBat Sumatra Hidrotermal** (1.0, 98.0) · nodo 109 | 8 | ~8 días |
| **94%** `▓▓▓▓▓` | SISMO_M4 | **Ghost Tonga-Fiji** (-18.0, -178.0) · nodo 64 | 68 | ~6 días |
| **94%** `▓▓▓▓▓` | SISMO_M5 | **Ghost Mariana** (15.0, 147.0) · nodo 81 | 26 | ~6 días |

*SISMO_M5 / M6 / M7 = sismo de magnitud 5+, 6+ o 7+. La zona es el punto de la malla global UVG-125 donde se aprendió la firma (nombre y coordenadas lat, lon); los nodos 'Ghost' son puntos teóricos de la malla sin estación física encima.*

## 🕐 Ventana temporal activa (muro de lags)

> Varias firmas independientes convergen en las MISMAS fechas. La ventana se fijó al **detectarla** y el contador **baja** cada ciclo mientras la señal persiste — no se re-proyecta desde hoy.

- **Faltan ~3–8 días** (ventana 2026-09-30 → 2026-10-05)
- Detectada hace **0 días** · clases: SISMO_M4, SISMO_M5, SISMO_M6

## ⏱ Anticipación — con cuánto tiempo suele avisar

> Medido sobre el histórico: ¿cuántos días **antes** del evento ya era reconocible su firma? No es un cronómetro exacto — es el promedio de lo que ha pasado. El hallazgo contraintuitivo: **los eventos más grandes avisan con más tiempo**. Un M7 se 'carga' durante más días que un M5.

| Evento | Aviso promedio | Máximo | Mínimo | Casos medidos |
|---|---|---|---|---|
| ERUPCION_VEI3 | **6.8 días** | 14.0 d | 1.0 d | 73 |
| ERUPCION_VEI4 | **2.6 días** | 10.0 d | 1.0 d | 24 |
| SISMO_M3_obs | **11.7 días** | 14.0 d | 7.0 d | 3 |
| SISMO_M4 | **6.3 días** | 14.0 d | 1.0 d | 111 |
| SISMO_M4_obs | **9.8 días** | 14.0 d | 1.0 d | 10 |
| SISMO_M5 | **6.0 días** | 14.0 d | 1.0 d | 118 |
| SISMO_M6 | **8.2 días** | 14.0 d | 1.0 d | 127 |
| SISMO_M7 | **9.4 días** | 14.0 d | 1.0 d | 14 |

*Medición in-sample sobre 32 años de histórico; la ventana de estudio llega a 14 días, así que los máximos pueden estar recortados.*

## 🔍 ¿Qué acelera o retrasa un evento?

> Comparamos las firmas que avisaron con **poco** tiempo (rápidas) contra las que avisaron con **mucho** (lentas). El patrón que salió: cuando hay tormenta geomagnética, el evento llega pronto — *la tormenta precipita*. Cuando el espacio está en calma, la corteza se carga despacio y avisa con más días — *la calma carga*.

| Variable | En firmas rápidas | En firmas lentas | Qué indica |
|---|---|---|---|
| Campo magnético solar (Bz promedio) | 0.04 | -0.05 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ en la ventana (kilotones) | 93.27 | 4.90 | más presente cuando el evento llega PRONTO |
| Campo magnético solar (Bz, últimas 72h) | -0.01 | -0.07 | más presente cuando el evento llega PRONTO |
| Gas volcánico SO₂ (90 días) | 231.25 | 90.52 | más presente cuando el evento llega PRONTO |
| Sismos en las últimas 72h | 4.17 | 1.65 | más presente cuando el evento llega PRONTO |
| es_sicigia | 0.27 | 0.14 | más presente cuando el evento llega PRONTO |

*Rápidas = tercio de firmas con menor anticipación; lentas = tercio con mayor.*

## 🧠 Memoria entrenada — lo que el sistema ya aprendió

> El sistema son **7 bots especializados**: `alfa1` vigila el clima espacial (30 años), `beta1` la resonancia Schumann — el latido electromagnético de la Tierra (30 años), `alfa2` los satélites Sentinel (aprende en vivo, sin backcast), `beta2` la desgasificación volcánica y la atmósfera (14 años), `delta` el humor de los mercados (10 años), `jupiter` la atención colectiva sobre tormentas solares (en vivo), y `padre` arbitra entre todos. Cada uno guarda sus propias **firmas** (patrones de vísperas de evento). El **peso** es su credibilidad ante el padre: 1.00 = normal; baja cuando falla y se recupera cuando acierta; puede superar 1.00 solo si detectó algo que el padre dejó pasar. `alfa2` y `jupiter` acumulan sus firmas desde los ciclos operativos, no desde el backcast histórico.

| Bot | Firmas aprendidas | Veces confirmadas | Credibilidad |
|---|---|---|---|
| alfa1 | 1,632 | 187,298 | 1.42 `▓▓▓▓▓▓` |
| beta1 | 993 | 187,505 | 1.42 `▓▓▓▓▓▓` |
| beta2 | 809 | 96,720 | 1.35 `▓▓▓▓▓░` |
| delta | 676 | 65,394 | 1.29 `▓▓▓▓▓░` |
| jupiter | 14 | 1,719 | 0.86 `▓▓▓░░░` |
| loki | 858 | 74,169 | 1.29 `▓▓▓▓▓░` |
| omega | 307 | 187,391 | 1.42 `▓▓▓▓▓▓` |
| padre | 14,289 | 187,505 | 0.94 `▓▓▓▓░░` |
| alfa2 | _en vivo · 20 ciclos · 2860 pases observados_ | — | 1.00 `▓▓▓▓░░` |

## 🎯 Asertividad — ¿qué tan bien le ha ido?

> Tres formas de medir lo mismo. **Histórica**: al repasar los 32 años de datos como examen, ¿reconoció las vísperas de los eventos que ya sabemos que ocurrieron? **Viva**: desde que opera en tiempo real, cada aviso queda registrado y un auditor independiente (el Juez) lo califica 72 horas después contra los sismos que realmente ocurrieron — sin trampa posible. **7 días**: lo mismo, pero solo la última semana. La viva empieza en '—' hasta que las primeras ventanas de 72h se cierran.

| Métrica | Valor |
|---|---|
| **Histórica** (examen sobre 32 años) | 98.0% |
| **Viva** (operación real, auditada) | 92.0% |
| **Últimos 7 días** (viva) | 87.3% |

### Por bot

| Bot | Histórica | Viva | Viva 7d | Credibilidad |
|---|---|---|---|---|
| alfa1 | 97.9% | 67.6% | 51.6% | 1.42 |
| alfa2 | — | 98.5% | 95.7% | 1.00 |
| beta1 | 98.2% | 89.3% | 80.1% | 1.42 |
| beta2 | 97.2% | 98.9% | 97.2% | 1.35 |
| delta | 99.6% | 98.5% | 95.7% | 1.29 |
| jupiter | 97.3% | 89.7% | 90.0% | 0.86 |
| loki | 98.3% | 98.5% | 95.7% | 1.29 |
| omega | 98.1% | 96.0% | 93.1% | 1.42 |
| padre | 98.0% | 90.7% | 86.6% | 0.94 |

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
| loki | 39.4% | **39.1%** | +0.2% ✅ |
| alfa1 | 100.0% | **100.0%** | +0.0% ✅ |
| jupiter | 0.8% | **0.8%** | +0.0% ✅ |
| alfa2 | — | **—** | — |

*Sesgo < 5% = el bot generaliza de verdad. Sesgo alto = su competencia era comodidad in-sample; su decisión real es más floja de lo que aparentaba.*

## 🗺 Correlaciones aprendidas — qué precede a cada evento

> Mapa de calor: qué tan elevada está cada variable en los **14 días previos** a cada tipo de evento comparado con su nivel habitual. 🔴≥2× · 🟠≥1.5× · 🟡≥1.2× · ⬜~normal · 🔵↓bajo. Un 🔴 en 'SO₂' para 'ERUPCION_VEI4' significa que justo antes de esas erupciones el SO₂ estaba el doble de lo normal. Un 🔵 en 'Kp' para 'SISMO_M7' confirma el Silent Trigger: los grandes sismos a veces ocurren en calma geomagnética.

| Variable | 🌋VEIVEI3 | 🌋VEIVEI4 | 🌋VEIVEI5 | M3_obs | M4 | M4_obs | M5 | M6 | M7 | ☀️KpKp6 | ☀️KpKp7 | ☀️KpKp9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Campo magnético solar (Bz, últimas 72h | 🔴2.4 | 🔵-4.2 | 🔵0.4 | 🔵-39.6 | ⬜1.0 | 🔵-51.1 | 🔵0.7 | 🟠1.9 | ⬜1.0 | 🔴48.4 | 🔴2.2 | 🔴5.2 |
| Campo magnético solar (Bz promedio) | 🔵-0.2 | 🔵-0.7 | 🔵-2.4 | 🔵-22.7 | ⬜1.1 | 🔵-33.8 | ⬜1.0 | 🟡1.2 | 🔵0.6 | 🔴15.6 | 🔴6.8 | 🔴3.0 |
| Rendimiento de Bitcoin en la ventana | 🟠1.6 | 🔴2.4 | 🔵-3.7 |   —   | ⬜0.9 |   —   | ⬜1.0 | ⬜1.2 | ⬜0.9 |   —   | 🔵-1.5 | 🟡1.5 |
| Gas volcánico SO₂ en la ventana (kilot | ⬜1.0 | 🔴2.8 | 🔴2.3 | 🔴2.7 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜0.9 | 🔵0.7 | 🔵0.7 | 🔵0.6 | ⬜0.9 |
| Erupciones (90 días) | 🟡1.3 | ⬜0.9 | 🔴2.4 | 🔵0.8 | ⬜1.0 | ⬜0.8 | ⬜1.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | ⬜1.0 | 🟡1.2 |
| lod | 🔵0.8 | ⬜1.1 | 🔵-0.3 | 🔵0.6 | ⬜1.0 | 🔵0.3 | ⬜1.0 | ⬜1.0 | ⬜1.1 | 🟡1.2 | 🟠1.5 | 🟡1.3 |
| Erupciones registradas en la ventana | 🟡1.4 | 🟠1.6 | 🟠1.6 | 🔵0.5 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜1.0 | ⬜0.8 | 🔵0.6 | ⬜0.9 | 🔵0.6 |
| es_sicigia | ⬜0.8 | ⬜1.0 | 🔵0.0 | 🔵0.0 | ⬜1.0 | 🔵0.0 | ⬜1.0 | ⬜0.9 | 🔵0.7 | ⬜0.9 | 🟡1.2 | 🔵0.8 |

## 🏆 Top 10 patrones del sistema

> Los **patrones más vistos** en 32 años de historia: firmas que el sistema reconoció más veces antes de un evento. Cuantas más repeticiones, más confiable es el patrón como señal. El **aviso** es el tiempo de anticipación típico que esa firma da antes del evento.

| # | Evento | Bot | Zona / Nodo | Veces | Estado | Aviso |
|---|---|---|---|---|---|---|
| 1 | 🌎 **SISMO_M4** | omega | Ghost Mariana | 12,433 | ✅ consolidada | — |
| 2 | 🌎 **SISMO_M4** | omega | Ghost Banda Sea | 8,699 | ✅ consolidada | — |
| 3 | 🌎 **SISMO_M4** | omega | Ghost Philippines-Taiwan | 8,148 | ✅ consolidada | — |
| 4 | 🌎 **SISMO_M4** | omega | Ghost Kamchatka-Kuril | 8,082 | ✅ consolidada | — |
| 5 | 🌎 **SISMO_M4** | omega | Ghost Scotia Arc | 6,840 | ✅ consolidada | — |
| 6 | 🌎 **SISMO_M4** | omega | Filipinas | 6,821 | ✅ consolidada | — |
| 7 | 🌎 **SISMO_M4** | omega | Ghost Alaska-Aleutian | 6,243 | ✅ consolidada | — |
| 8 | 🌎 **SISMO_M4** | omega | Ghost Vanuatu | 5,703 | ✅ consolidada | — |
| 9 | 🌎 **SISMO_M4** | omega | Ghost Hindu Kush | 5,099 | ✅ consolidada | — |
| 10 | 🌎 **SISMO_M5** | omega | Cascadia | 4,650 | ✅ consolidada | — |

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
| beta2 | Ghost Aleutian W (52.0, 175.0) | 55 | ✅ consolidada | — |
| padre | Ghost Aleutian W (52.0, 175.0) | 44 | ✅ consolidada | — |
| jupiter | Caribe Norte (18.5, -67.0) | 34 | ✅ consolidada | — |
| beta1 | Ghost Alaska-Aleutian (55.0, -165.0) | 29 | ✅ consolidada | — |
| omega | Ghost Aleutian W (52.0, 175.0) | 24 | ✅ consolidada | — |

### 🌎 SISMO_M4

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Mariana (15.0, 147.0) | 12,433 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 8,699 | ✅ consolidada | — |
| omega | Ghost Philippines-Taiwan (20.0, 122.0) | 8,148 | ✅ consolidada | — |
| omega | Ghost Kamchatka-Kuril (48.0, 153.0) | 8,082 | ✅ consolidada | — |
| omega | Ghost Scotia Arc (-57.0, -30.0) | 6,840 | ✅ consolidada | — |

### 🌎 SISMO_M4_obs

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| beta2 | Ghost Ryukyu (26.0, 128.0) | 93 | ✅ consolidada | — |
| jupiter | Ghost Colombia Interior (4.0, -75.0) | 67 | ✅ consolidada | — |
| padre | Ghost Ryukyu (26.0, 128.0) | 36 | ✅ consolidada | ~11 días |
| omega | Ghost Ryukyu (26.0, 128.0) | 34 | ✅ consolidada | — |
| beta1 | Ghost Colombia Interior (4.0, -75.0) | 31 | ✅ consolidada | — |

### 🌎 SISMO_M5

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Cascadia (46.0, -124.0) | 4,650 | ✅ consolidada | — |
| omega | Ghost Mariana (15.0, 147.0) | 3,708 | ✅ consolidada | — |
| omega | Filipinas (14.5, 121.0) | 3,518 | ✅ consolidada | — |
| omega | Ghost Mariana (15.0, 147.0) | 3,379 | ✅ consolidada | — |
| omega | Ghost Kamchatka-Kuril (48.0, 153.0) | 3,178 | ✅ consolidada | — |

### 🌎 SISMO_M6

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Banda Sea (-5.0, 130.0) | 469 | ✅ consolidada | — |
| omega | Nueva Zelanda (-41.0, 174.0) | 452 | ✅ consolidada | — |
| omega | Ghost San Andreas Mid (35.5, -119.5) | 416 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 379 | ✅ consolidada | — |
| omega | Ghost Chiapas Interior (15.5, -93.0) | 334 | ✅ consolidada | — |

### 🌎 SISMO_M7

| Bot | Zona (nodo de la malla) | Veces vista | Estado | Aviso típico |
|---|---|---|---|---|
| omega | Ghost Tonga-Fiji (-18.0, -178.0) | 109 | ✅ consolidada | — |
| omega | Ghost Banda Sea (-5.0, 130.0) | 78 | ✅ consolidada | — |
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
| COSMICO+DESGAS+SISMICO+SOLAR | 97 | COSMICO+SISMICO+SOLAR→DESGAS | 10% | **INDIFERENTE** |
| COSMICO+SISMICO+SOLAR | 86 | SISMICO+SOLAR→COSMICO | 24% | **INDIFERENTE** |
| COSMICO+DESGAS+FINANCIERO+SISMICO+SOLAR | 47 | COSMICO+DESGAS+SISMICO+SOLAR→FINANCIERO | 6% | **INDIFERENTE** |

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
- ACIERTO — avisó y el evento ocurrió: 20,310
- FALLO — el evento ocurrió sin aviso (lo más castigado): 313
- FALSO POSITIVO — avisó y no pasó nada: 1,463
- PENDIENTE — ventana de 72h aún abierta: 306

**Bitácora de entrenamiento (reconocimiento/backtest/trasfondo — no puntúa):**
- ACIERTO: 985,074
- FALLO: 1,277

## 🧾 Bitácora del sistema — versión, cambios y salud

> No solo el planeta: el propio Sentinel deja traza. Cada corte registra versión, pesos y métricas, y se compara con el corte anterior — así se ve si un cambio mejoró o empeoró el comportamiento, y los post-mortems tienen base.

| Campo | Este corte | Corte anterior | Cambio |
|---|---|---|---|
| Versión del modelo | 2.5.4 | 2.5.4 | sin cambio |
| Asertividad viva *(cuenta los silencios)* | 92.0% | 92.0% | -0.1% |
| **Ganancia real** (precisión ÷ tasa base) | 0.89× | — | 1× = no aporta |
| Aciertos / Fallos (vivos) | 20,310 / 313 | 20,156 / 313 | +154 aciertos |
| Pendientes de auditoría | 306 | 369 | -63 |
| Pesos de bots | 8 bots | — | alfa1 0.30→1.42; beta1 0.30→1.42; omega 0.95→1.42; padre 0.30→0.94 |

*Asertividad viva, últimos cortes: 93% → 92% → 92% → 92% → 92%*

### Quién ve QUÉ — competencia por clase de evento

> Un solo número por bot aplasta al especialista. Aquí, la fracción de eventos de cada tamaño que cada bot SÍ vio. Sale de las fases que discriminan (trasfondo y viva): la de reconocimiento marca todo como acierto y no enseña nada. La flecha compara con el primer corte guardado.

| bot | M3 | M4 | M5 |
|---|---:|---:|---:|
| beta1 | 35% (25/71) ↓ | 70% (167/237) | 3% (1/29) |
| omega | 52% (37/71) ↑ | 70% (165/237) | 3% (1/29) |
| padre | 44% (31/71) ↓ | 65% (155/237) ↑ | 7% (2/29) |
| alfa1 | 34% (24/71) ↑ | 64% (151/237) ↑ | 17% (5/29) |
| beta2 | 11% (8/71) ↓ | 18% (43/237) | 38% (11/29) |
| jupiter | 4% (3/71) | 10% (23/237) | 0% (0/29) |
| loki | 0% (0/71) ↓ | 1% (3/237) ↓ | 0% (0/29) |
| delta | — | — | 0% (0/29) |
| alfa2 | — | — | 0% (0/29) |

**El mejor de cada clase:** M3 → **omega** (52%) · M4 → **beta1** (70%) · M5 → **beta2** (38%).

*El peso de cada bot en el consenso es el de su MEJOR clase: un experto que solo sirve para una cosa, sirve.*


## ✅ Aciertos y Predicciones Correctas

> El sistema también tiene victorias que celebrar. Esta sección documenta cuándo nuestras predicciones fueron correctas: eventos que anticipamos, qué tan bien los predijimos, y cuántos días antes vimos el patrón.

### 📊 Resumen — Últimos 30 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 20310 |
| **Fallos** | 313 |
| **Falsos positivos** | 1463 |
| **Tasa de acierto** | 90.7% `▓▓▓▓▓▓▓▓▓▓▓░` |
| **Total predicciones** | 22392 |

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación (días) |
|-----|----------|------|-----------|----------------------|
| beta2 | 2427/2454 | 99% `▓▓▓▓▓▓▓▓` | 0.21 | 0.1 |
| alfa2 | 2417/2454 | 98% `▓▓▓▓▓▓▓▓` | 0.05 | 0.1 |
| delta | 2417/2454 | 98% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1 |
| loki | 2417/2454 | 98% `▓▓▓▓▓▓▓▓` | 0.21 | 0.1 |
| omega | 2355/2454 | 96% `▓▓▓▓▓▓▓▓` | 0.35 | 0.1 |
| padre | 2227/2454 | 91% `▓▓▓▓▓▓▓░` | 0.15 | 0.1 |
| jupiter | 2201/2454 | 90% `▓▓▓▓▓▓▓░` | 0.24 | 0.1 |
| beta1 | 2191/2454 | 89% `▓▓▓▓▓▓▓░` | 0.33 | 0.1 |
| alfa1 | 1658/2454 | 68% `▓▓▓▓▓░░░` | 0.46 | 0.1 |

### 🎯 Eventos Predichos Correctamente (más recientes primero)

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 35.4% `▓▓▓▓░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 68.6% `▓▓▓▓▓▓▓░░░`
- **Fase:** viva

#### JUPITER — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 49.5% `▓▓▓▓▓░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

#### DELTA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 39.7% `▓▓▓▓░░░░░░`
- **Fase:** viva

#### BETA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 04:02 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 40.0% `▓▓▓▓░░░░░░`
- **Fase:** viva

#### LOKI — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 03:56 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 35.4% `▓▓▓▓░░░░░░`
- **Fase:** viva

#### OMEGA — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 03:56 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 68.6% `▓▓▓▓▓▓▓░░░`
- **Fase:** viva

#### JUPITER — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 03:56 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 49.5% `▓▓▓▓▓░░░░░`
- **Fase:** viva

#### ALFA2 — CALMA — (zonas monitoreadas)

- **Predicción:** 2026-09-27 03:56 UTC
- **Evento real:** 2026-09-27 06:05 UTC
- **Anticipación:** 0.1 días
- **Confianza:** 20.0% `▓▓░░░░░░░░`
- **Fase:** viva

_... y 20300 aciertos más en los últimos 30 días_

---
*Todos los datos provienen de fuentes públicas oficiales (NOAA, USGS, NASA, ESA). Nada aquí es un pronóstico oficial de protección civil: es investigación de precursores en curso.*

*Ciclos totales: 3,503 · Sentinel Omega · Fractal Core Research*
