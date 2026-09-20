# 📅 Reporte semanal — Sentinel Omega
*Generado 2026-09-20 12:25 hora MX — ventana 7 días*

> **Lectura rápida:** el sistema estuvo **inquieto** · Fantasma medio **18.6** (HIGH · avisar) · Muro **sin roturas** · asertividad viva **88%**.

## Resumen
- Ciclos corridos: **914**
- Fantasma medio del periodo: **18.6**
- Fantasma máximo: **62.3**
- Breaches del Muro: **0**
- Asertividad viva del periodo: **88%** (n=5337 resueltas)

## Cimática
- Patrones `general`: 1 (frecuencia máx 5)

| Patrón | Ámbito | Evento asociado | Frecuencia |
|---|---|---|---:|
| 409501 | general | — | 5 |

## ✅ Aciertos — Últimos 7 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 4722 |
| **Fallos** | 0 |
| **Falsos positivos** | 615 |
| **Tasa de acierto** | 87.4% `▓▓▓▓▓▓▓▓▓▓░░` |
| **Total predicciones** | 5400 |

![Distribución de veredictos](graficas/aciertos_7d_pastel.png)

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación |
|-----|----------|------|-----------|---------------|
| alfa2 | 593/593 | 100% `▓▓▓▓▓▓▓▓` | 0.00 | 0.1d |
| beta2 | 593/593 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1d |
| delta | 593/593 | 100% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1d |
| loki | 593/593 | 100% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1d |
| beta1 | 549/593 | 93% `▓▓▓▓▓▓▓░` | 0.34 | 0.1d |
| omega | 549/593 | 93% `▓▓▓▓▓▓▓░` | 0.27 | 0.1d |
| padre | 549/593 | 93% `▓▓▓▓▓▓▓░` | 0.10 | 0.1d |
| jupiter | 520/593 | 88% `▓▓▓▓▓▓▓░` | 0.26 | 0.1d |
| alfa1 | 183/593 | 31% `▓▓░░░░░░` | 0.63 | 0.1d |

![Desempeño por bot](graficas/aciertos_7d_barras.png)

![Fantasma medio diario](graficas/semanal_fantasma.png)
![Alertas por día](graficas/semanal_alertas.png)
![Breaches del Muro por día](graficas/semanal_breaches.png)

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
