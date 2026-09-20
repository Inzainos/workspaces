# 🗓️ Reporte mensual — Sentinel Omega
*Generado 2026-09-14 23:37 hora MX — ventana 31 días*

> **Lectura rápida:** el sistema estuvo **inquieto** · Fantasma medio **9.4** (MODERATE · atención) · Muro con **742 breach(es)** · asertividad viva **96%**.

## Resumen
- Ciclos corridos: **8225**
- Fantasma medio del periodo: **9.4**
- Fantasma máximo: **16.2**
- Breaches del Muro: **742**
- Asertividad viva del periodo: **96%** (n=12285 resueltas)

## Cimática
- Patrones `general`: 76158 (frecuencia máx 435)
- Patrones `nodo`: 114886 (frecuencia máx 435)

| Patrón | Ámbito | Evento asociado | Frecuencia |
|---|---|---|---:|
| 190637 | general | SISMO_M5 | 435 |
| 190638 | nodo 14 | SISMO_M5 | 435 |
| 190639 | nodo 107 | SISMO_M4 | 435 |
| 190640 | nodo 21 | SISMO_M6 | 435 |
| 189470 | general | SISMO_M5 | 264 |
| 189471 | nodo 14 | SISMO_M5 | 264 |
| 189472 | nodo 107 | SISMO_M4 | 264 |
| 189473 | nodo 21 | SISMO_M6 | 264 |
| 190661 | general | SISMO_M5 | 254 |
| 190662 | nodo 14 | SISMO_M5 | 254 |

## ✅ Aciertos — Últimos 31 días

| Métrica | Valor |
|---------|-------|
| **Aciertos** | 11774 |
| **Fallos** | 72 |
| **Falsos positivos** | 439 |
| **Tasa de acierto** | 93.0% `▓▓▓▓▓▓▓▓▓▓▓░` |
| **Total predicciones** | 12654 |

![Distribución de veredictos](graficas/aciertos_31d_pastel.png)

### 🤖 Desempeño por Bot

| Bot | Aciertos | Tasa | Confianza | Anticipación |
|-----|----------|------|-----------|---------------|
| alfa2 | 1357/1365 | 99% `▓▓▓▓▓▓▓▓` | 0.00 | 0.1d |
| beta2 | 1357/1365 | 99% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1d |
| delta | 1357/1365 | 99% `▓▓▓▓▓▓▓▓` | 0.30 | 0.1d |
| loki | 1357/1365 | 99% `▓▓▓▓▓▓▓▓` | 0.20 | 0.1d |
| omega | 1351/1365 | 99% `▓▓▓▓▓▓▓▓` | 0.38 | 0.1d |
| beta1 | 1275/1365 | 93% `▓▓▓▓▓▓▓░` | 0.30 | 0.1d |
| padre | 1267/1365 | 93% `▓▓▓▓▓▓▓░` | 0.18 | 0.1d |
| jupiter | 1253/1365 | 92% `▓▓▓▓▓▓▓░` | 0.22 | 0.1d |
| alfa1 | 1200/1365 | 88% `▓▓▓▓▓▓▓░` | 0.35 | 0.1d |

![Desempeño por bot](graficas/aciertos_31d_barras.png)

![Fantasma medio diario](graficas/mensual_fantasma.png)
![Alertas por día](graficas/mensual_alertas.png)
![Breaches del Muro por día](graficas/mensual_breaches.png)

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
