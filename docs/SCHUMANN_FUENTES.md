# Schumann: de dónde sacar el latido

**Problema, medido el 2026-10-09.** La resonancia Schumann es el eje del
proyecto —todo se correlaciona contra el latido— y hoy no está medida:

| | |
|---|---|
| fuente única | `https://sos70.ru/provider.php?file=shm.jpg` (una imagen JPEG de Tomsk) |
| método | contar píxeles claros en el 40 % superior (HSV 180-255) |
| `schumann_hz` | **fabricado**: `7,83 + actividad × 0,02`, exacto en 583/743 filas |
| variación | actividad `21,46 %` en **564 de 743 filas (76 %)**: congelado |
| en la memoria | **86 de 4.000 firmas (2,2 %)**, recorrido de **0,03 Hz** |
| historia | `tbl_enjambre_telemetria`: 880 filas, **un** nodo, desde 2026-07-24 |

Consecuencia: el AUC 0,49 de los ONNX, el lift 1,04× de las figuras y el «no
hay señal precursora» se midieron **sin el sensor principal**. La hipótesis
central del proyecto nunca se ha podido probar.

La frecuencia fabricada se retiró de `api/schumann.py` el 2026-10-09:
`analyze_spectrogram` devuelve `(None, activity_pct)`. La actividad es real; la
frecuencia, sin medir.

---

## Lo que NO sirve

- **Las «API 2026» de terceros** (`schumannresonancelive.com/api/data.php`,
  `schumannresonance.app`, `sungeo.net`). Raspan **la misma imagen de Tomsk** y
  rellenan SR2-SR5 con **valores nominales de referencia**. Sería el mismo
  vicio por otra puerta, con una capa más de indirección.
- **Datos geomagnéticos de 1 segundo** (INTERMAGNET, USGS). Schumann está en
  7,83 / 14,1 / 20,3 Hz y Nyquist exige **≥ 40 Hz** de muestreo. Con 1 Hz es
  físicamente imposible ver la resonancia. Descartado por teorema, no por
  disponibilidad.

## Lo que sí sirve: Sierra Nevada ELF (Granada)

La única fuente verificada con **dato calibrado y con historia**.

| | |
|---|---|
| cobertura | **marzo 2013 → febrero 2017** (4 años) |
| muestreo | **256 Hz**, un archivo crudo por sensor y hora |
| sensores | 0 = NS, 1 = EW |
| procesado | FFT en la banda calibrada **6-25 Hz** → quita ruido antropogénico → **ajuste lorentziano** (`lmfit`) |
| salida | `.npz` por mes y sensor (~43 MB), parámetros **cada 10 minutos** |
| parámetros | de la lorentziana: frecuencia central, amplitud y anchura (→ Q), **con error de ajuste y incertidumbre por parámetro** |
| crudo | Zenodo, ~26,7 GB/año (2014: `10.5281/zenodo.6348691`) — **ya no hace falta**: el procesado de 4 años está descargado |
| procesado | repositorio UGR, handle `10481/71563`, 3,58 GB — **descargado el 2026-10-09**. El «HTTP 403» era bloqueo de bots: con `User-Agent` propio entra. Script reproducible: `deploy/bajar_schumann_ugr.sh` |
| código | `github.com/asalinas62/Sierra_Nevada_SR`, **GPL-3.0**, con muestra de marzo 2015 |
| artículo | *Computers & Geosciences* 2022, `10.1016/j.cageo.2022.105148` |

Esto es un ajuste lorentziano sobre un espectro calibrado: frecuencia de
verdad, no un conteo de brillo. Y a 10 minutos, más fino que la hora que pide
el pipeline.

## Plan, en orden y con su coste — ejecutado el 2026-10-09

1. **Validar el camino sin bajar nada grande.** ✅ Hecho: repo clonado en
   directorio propio, muestra de marzo 2015 corrida con intérprete `-I`,
   esquema de salida confirmado (`arr_0` satélites, `arr_5/6` parámetros
   lorentzianos, `arr_9` tiempo — ver `schumann_granada.leer_npz`).
2. **Un año completo.** ✅ **Sobrecumplido**: los CUATRO años procesados
   (2013-03 → 2017-02) bajados de una pieza desde la UGR — 3,58 GB, 96 `.npz`
   — en vez de bajar 26,7 GB de crudo por año y correr el pipeline por nuestra
   cuenta. Ingiero: **405.276 intervalos de 10 min, ambos sensores**.
   Persistido en `sentinel_omega/data/schumann_granada/` (DB SQLite de 70 MB +
   `Npz.zip`; `data/` es gitignored, regla 3). Ojo con el nombre real de los
   archivos: la UGR publica `SN_{YYMM}_LO_6_1_{sensor}.npz`, no el
   `SN_{YYMM}_{sensor}.npz` que construye su `Packaging.py` — el lector acepta
   las dos formas.
3. **Probar la hipótesis del proyecto, por fin.** ✅ Hecho con
   `deploy/medir_schumann_precursor.py`: 26.458 sismos M4.5+ del periodo,
   ventanas de evento contra calma **emparejada por época**, NIVEL y FORMA,
   barrido de ventana (24/72/168/336 h) y de semilla de calma. Resultado en
   `estado/BITACORA_2026-10-09.md`.
4. Si sale señal: los cuatro años y Schumann entra al backcast. **No salió
   señal** — ver bitácora.

## Y para el vivo

El archivo de Granada acaba en 2017, así que para el tiempo real siguen dos
caminos, y ninguno da frecuencia hoy:

- **Tomsk/sos70 como está**, pero rotulado por lo que es: `schumann_activity`,
  una intensidad. Ya corregido.
- **Eskdalemuir (British Geological Survey)**: espectrograma ELF con ejes de
  frecuencia y potencia **calibrados**. No se encontró la página oficial de
  descarga; es la vía institucional que vale la pena perseguir para el vivo.

Mientras el vivo no dé frecuencia, el entrenamiento puede usar la historia de
Granada y el vivo aportar solo intensidad —declarado, no disimulado—.
