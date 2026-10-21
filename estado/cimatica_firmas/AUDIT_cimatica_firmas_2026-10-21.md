# Motor cimático (tela SNT) sobre las firmas del Padre — Medición LOO

**Fecha:** 2026-10-21
**Script:** `deploy/medir_cimatica_firmas.py`
**Origen del motor:** `The-shadow-Node-Theory/reconstruction_real/code/tela_cimatica.py`
(su lectura cimática del cubo 𝒞(u, m, τ); auditado ese mismo día en
`TELA_CIMATICA_2026-10-21.md` y `TELA_V2_INTEGRADA_2026-10-21.md`)

## Qué es

La misma prueba de la tela, sobre las ventanas de 14 días (336 h) que
entrenaron las firmas: cada ventana reconstruida como **serie** (no como
vector agregado), interpolada a la retícula de fase de la tela, y leída
cimáticamente — detrend lineal + ventana Hann + FFT, huella por serie
(5 bins de fase + log A1/A2/A3).

**El pedido del operador:** «meterle el motor cimático a las firmas del
padre». La capa cimática existente (`core/firmas/cimatica.py`) cuenta
ESTADOS discretizados (bandas log → clave → frecuencia); lo que trae la
tela es la lectura ESPECTRAL de la TRAYECTORIA. Este experimento mide si
esa lectura identifica algo, antes de tocar al Padre.

| Serie | Fuente | Ventana |
|---|---|---|
| bz_promedio, bz_derivada, viento_solar_avg, kp_promedio, densidad_protones | `tbl_clima_espacial_raw` (horaria, 1994→) | 336 h previas al ancla |
| sismo_count (ritmo de enjambre del nodo) | `tbl_historico_sismico_raw` (evento-sparse: hora sin fila = cero temblores) | 336 h previas |

Anclas: celdas sísmicas M4.5+ deduplicadas (nodo+mag a ≤12 h) con muestreo
estratificado (M7 todas 489 · M6 800 · M5 800 · M4 800) + eventos no
sísmicos completos (VEI3 646, VEI4 154, VEI5 7, Kp6 373, Kp7 75, Kp9 1).
**4,145 casos con datos, 0 sin dato.** Semilla fija (42), reproducible.

## El viaje de la medición (los artefactos, documentados)

La primera corrida dio **77% volcánico por familia y 56% SISMO_M4** —
números que resultaron ser artefactos de DOS bugs corregidos en vivo:

1. **La serie de enjambre estaba muerta**: `tbl_historico_sismico_raw`
   es evento-sparse (0 filas con count=0, verificado) y el gate de
   cobertura (≥50% de horas con fila) la anulaba en casi toda ventana.
   Corrección: malla densa en ceros — hora sin fila es CERO temblores
   (semántica de la fuente, regla 2), con offset ABSOLUTO desde el inicio
   de la ventana (el offset relativo a la primera fila desplazaba el
   enjambre si el primer temblor llegaba tarde).
2. **Centroides envenenados por NaN**: `C.mean(axis=0)` sin máscara —
   con 232 ventanas de 1994 sin cobertura de clima, TODA dim de clima del
   centroide se volvía NaN y el LOO se calculaba sin saberlo. Corrección:
   `np.nanmean` por dim (una dim muere solo si NADIE del grupo la tiene).

**Después de ambas correcciones los números cayeron y quedaron los
reales.** La secuencia completa está en el log de esta bitácora porque es
la misma lección de la tela v1→v2: lo que sobrevive a la corrección es
lo que existe.

## Resultados medidos (corregidos)

| Prueba | Exactitud | Nulo | Veredicto |
|---|---|---|---|
| **FAMILIA (el tono): sismico/volcánico/solar** | **46.8%** (n=4145) | 33.3% uniforme · **placebo 32.9% ± 7.2** | **SEÑAL REAL** (~+2 se): la ventana identifica el régimen |
| Ablación solo-clima | 51.2% (n=3913) | — | el tono vive sobre todo en el clima espacial |
| Ablación solo-enjambre | 46.1% (n=4145) | — | el ritmo del nodo también carga familia |
| CLASE (9 clases) | 18.4% | 19.3% mayoría | **AL NULO** — el 24.8% previo era el bug |
| ERUPCION_VEI3 | 228/646 = **35%** | 11.1% uniforme | identificable por separado |
| SISMO_M4 / SISMO_M5 | 32% / 20% | 11.1% | efecto Omori visible (enjambre reciente → tamaño menor) |
| **NODO** | **1.4%** | 10.9% mayoría | **MUERTO** — el tono no localiza |

Por familia: sismico 1452/2889 (50%) · volcanico 388/807 (48%) ·
solar 100/449 (22%).

Placebo (permutación de etiquetas, 5 corridas): clase 6.0% ± 2.3 ·
familia 32.9% ± 7.2. El control placebo es el estándar del workspace
(cf. H-φ en SNT v30): sin él, la estructura de los datos se disfraza de
señal.

## Lectura cimática honesta

1. **La figura identifica el tono, no el instrumento — igual que en la
   tela SNT, y con la misma fuerza relativa.** La víspera de erupción
   (VEI3 35%, volcánico 48%) se distingue del medio sísmico; el medio
   sísmico (M4-M7) se dibuja igual (3-32% por clase, agregado al nulo).
2. **El tono NO dice dónde**: nodo 1.4% contra un nulo de 10.9%. La
   ventana de clima+enjambre no localiza el nodo — consistente con la
   compuerta ONNX (AUC ~0.5 vs nulo-por-nodo 0.899) y con todo lo que
   este workspace ha medido antes.
3. **Las tormentas son CIRCULARES en esta prueba**: el ancla es el onset
   Kp≥6 y la ventana contiene la fase de subida — la serie kp_promedio
   lleva el propio evento. Su 22% de identificación no es predicción; se
   divulga, no se celebra.
4. **El tono volcánico es lo más aprovechable**: 48% familia / 35% VEI3
   contra 33% placebo, con física real (enjambre pre-erupción + clima)
   y SIN circularidad — es corroboración ortogonal a beta2 (SO₂).

## Limitaciones

- Schumann excluido: `tbl_enjambre_telemetria` tiene 1,026 filas vivas
  (jul-2026→), sin backcast. El tono Schumann se acumulará en vivo.
- Muestra estratificada con semilla fija; los M6+ completos del universo
  (4,200+) quedan en 800 — el LOO por clase con muestra balanceada es la
  medición base, no una frontera definitiva (misma salvedad que la tela).
- Interpolación lineal sobre huecos internos de fase — suaviza; el
  detrend+Hann aplica la lección de beta1 (fuga espectral).
- La clasificación es centroide-cercano sin calibrar.

## Qué significa para «meterle el motor al padre»

El motor espectral SÍ lee algo real (familia +2 se sobre placebo, el
tono volcánico lo más distinguible) pero NO localiza (nodo muerto) y NO
separa clases sísmicas (al nulo). La integración honesta:

- **El tono entra como EVIDENCIA, no como compuerta**: lectura por ciclo
  de la ventana viva → huella → distancia a los centroides de familia →
  «tono actual: volcánico (dist 3.1) / sísmico (dist 3.6)» — reportado
  en digesto/plantillas y REGISTRADO para que el Juez mida en producción
  si el tono corrobora (como se hizo con el matching de firmas antes de
  dejarlo decidir algo).
- **No entra**: localización por tono (muerto), identificación de clase
  sísmica (al nulo), tormentas (circular).

## Reproducir

```bash
cd /home/deamon/workspaces
.venv/bin/python deploy/medir_cimatica_firmas.py --ablation   # ~90 s
```

Salidas: `estado/cimatica_firmas/` (huellas_por_clase.csv,
loo_resumen.json, fig_cimatica_firmas_tonos.png).

---

*Sentinel Omega · Fractal Core Research · 2026-10-21*
