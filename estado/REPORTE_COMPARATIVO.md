# 🔄 Comparativo diario — 2026-09-27 vs 2026-09-26
*Corte 00:06 hora MX*

| Métrica | Hoy | Ayer | Cambio |
|---|---:|---:|---:|
| Fantasma medio | 9.5 | 11.5 | ▼ -2.0 |
| Fantasma máx | 9.7 | 14.1 | ▼ -4.4 |
| Ciclos corridos | 60 | 210 | ▼ -150 |
| Breaches del Muro | 0 | 0 | ＝ +0 |
| Asertividad viva (resuelta en el día) | — | 82% (n=1665) | — |
| Patrones cimáticos (total / nuevos 24h) | 279472 | — | +279472 |

> **Lectura rápida:** el sistema estuvo **en calma** · Fantasma medio **9.5** (MODERATE · atención) · Muro **sin roturas**.

## ✅ Aciertos — Últimas 24 horas

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 1359 |
| **Fallos** | 0 |
| **Falsos positivos** | 297 |
| **Tasa de acierto** | 74.0% `▓▓▓▓▓▓▓▓▓░░░` |
| **Total predicciones** | 1836 |

![Distribución de veredictos](graficas/aciertos_1d_pastel.png)

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación |
|-----|----------|------|-----------|---------------|
| alfa2 | 184/184 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1d |
| beta2 | 184/184 | 100% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1d |
| delta | 184/184 | 100% `▓▓▓▓▓▓▓▓` | 0.33 | 0.1d |
| jupiter | 184/184 | 100% `▓▓▓▓▓▓▓▓` | 0.28 | 0.1d |
| loki | 184/184 | 100% `▓▓▓▓▓▓▓▓` | 0.29 | 0.1d |
| omega | 176/184 | 96% `▓▓▓▓▓▓▓▓` | 0.54 | 0.1d |
| padre | 131/184 | 71% `▓▓▓▓▓▓░░` | 0.29 | 0.1d |
| beta1 | 88/184 | 48% `▓▓▓▓░░░░` | 0.51 | 0.1d |
| alfa1 | 44/184 | 24% `▓▓░░░░░░` | 0.60 | 0.1d |

![Desempeño por bot](graficas/aciertos_1d_barras.png)

![Fantasma 7 días](graficas/comparativo_fantasma.png)

## ℹ️ Cómo leer este reporte

- **Fantasma** — índice de *riesgo cósmico* (TITAN V32). **No es un sismo**: mide la
  tensión del sistema combinando campo magnético (Bz), viento solar, resonancia
  Schumann, presión y más. Escala: **LOW <5** (calma) · **MODERATE 5–15** (atención)
  · **HIGH 15–30** (avisar) · **CRITICAL ≥30** (protocolo).
- **Muro de los 5 Eventos** — cinco "paredes" de correlación (geofísica, atmosférica,
  oceánica, solar/geomagnética y financiera). Hay *breach* cuando **3 o más** se
  activan a la vez.
- **Asertividad viva** — de las predicciones ya verificadas contra la realidad (USGS),
  qué porcentaje resultó **ACIERTO**. Verdad por fila, ventana de 72 h; el Juez
  audita aparte (nunca predice).
- **Cimática** — patrones de telemetría que el sistema ve repetirse; si un patrón
  antecede a un evento real se etiqueta con su clase (SISMO_M4…M7, ERUPCION_VEI…).
  La frecuencia es cuántas veces se ha visto ese patrón.
- **Anticipación** — días de adelanto promedio entre la señal y el evento.
