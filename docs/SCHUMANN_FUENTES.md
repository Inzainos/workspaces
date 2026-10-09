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
| crudo | Zenodo, ~26,7 GB/año (2014: `10.5281/zenodo.6348691`) |
| procesado | repositorio UGR, handle `10481/71563`, 3,3 GB (devolvió HTTP 403 al consultarlo: pedir acceso) |
| código | `github.com/asalinas62/Sierra_Nevada_SR`, **GPL-3.0**, con muestra de marzo 2015 |
| artículo | *Computers & Geosciences* 2022, `10.1016/j.cageo.2022.105148` |

Esto es un ajuste lorentziano sobre un espectro calibrado: frecuencia de
verdad, no un conteo de brillo. Y a 10 minutos, más fino que la hora que pide
el pipeline.

## Plan, en orden y con su coste

1. **Validar el camino sin bajar nada grande.** Clonar el repo (GPL-3.0, trae
   la muestra de marzo 2015) y correr su pipeline sobre esa muestra. Confirma el
   esquema de salida y que los parámetros son los tres que hacen falta.
   *Coste: minutos.* ⚠ Es código y datos de terceros: en directorio propio y
   vacío, los scripts propios aparte, e intérprete con `-I`.
2. **Un año completo.** 2014 desde Zenodo (26,7 GB; hay 803 GB libres) y correr
   el pipeline → serie de 10 min para 2014.
3. **Probar la hipótesis del proyecto, por fin.** Pareja de ventanas por época
   contra el catálogo sísmico de 2014, con `deploy/medir_figura.py` y el canal
   de Schumann dentro. **Esto es lo que nunca se ha medido.**
4. Si sale señal: los cuatro años (≈107 GB) y Schumann entra al backcast.

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
