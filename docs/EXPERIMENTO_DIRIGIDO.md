# Plantilla del experimento dirigido

**Cómo probar una hipótesis nueva de precursor sin repetir los errores viejos.**

Escrito el 2026-10-11, después de cerrar la hipótesis Schumann→sismo en
negativo con dos estaciones independientes. Todo lo que sigue son las
lecciones de esa medición, convertidas en pasos.

---

## Las cuatro reglas que lo salvan

1. **Declara la hipótesis ANTES de mirar los datos.** Especifica: señal,
   ventana, magnitud mínima, dirección esperada del efecto. Escribe lo que
   contarías como confirmación y lo que contarías como refutación.

2. **El modelo nulo va al lado del número.** Sin el comparador de calma, tu
   métrica vale cero (la calma es el 97 % del tiempo). Para cada ventana de
   evento, una de calma **emparejada por época** — y estrecha el empareje
   hasta que la calma esté en la misma quincena (la lección de Eskdalemuir:
   ±180 días → +0,64; ±7 días → +0,057 = cero).

3. **Barrido de semillas.** Once semillas distintas. Si el efecto depende de
   cuál muestra de calma te tocó, es ruido de muestreo, no señal (la lección
   de Granada: +0,19 con una semilla, +0,06 ± 0,07 con once).

4. **El control más BARATO antes de la explicación elaborada.** Cuando algo
   sobreviva un control, el siguiente control más simple — no una teoría
   sofisticada (la lección del residuo de Eskdalemuir: propuse Omori y era
   más calendario).

---

## Pasos concretos

### 1. Identifica la señal candidata

| Señal | Por qué podría funcionar | Fuente |
|---|---|---|
| Radón (~²²²Rn) | Exhalación pre-sísmica por micro-fractura | estaciones de radón |
| Resistividad eléctrica | Cambios en la porosidad de la roca | magnetotelúricos |
| Migración de enjambres | Omori difuso: la sismicidad se mueve antes del evento | USGS (ya en la DB) |
| Vp/Vs | Cambios en la velocidad de ondas por presión de fluidos | sismómetros |
| Infrasonido | Ondas de presión atmosférica generadas por actividad | estaciones IMS |

### 2. Asegura que la fuente existe con historia suficiente

- **Nyquist**: si la señal vive en una banda X, el muestreo debe ser ≥2X.
- **Calibración**: la fuente debe tener una respuesta instrumental conocida
  (la lección de Granada: sin calibración, la "frecuencia" era una recta
  sobre conteo de píxeles).
- **Historia**: mínimo un año para tener estaciones, idealmente cuatro.

### 3. Declara la hipótesis

```
HIPÓTESIS: la señal [X] cambia en la ventana de [Y] horas antes de
sismos M[Z]+ con una magnitud de efecto esperada de [W].

CONFIRMACIÓN: |dif/sd| >= [umbral] en la mayoría de semillas, con el
control de forma (ev-ev) mostrando firma compartida (lift > 1).

REFUTACIÓN: el efecto no sobrevive el barrido de semillas, o muere al
estrechar el empareje temporal.
```

### 4. Construye el medidor (usa la plantilla)

```bash
# copia el medidor y adapta la fuente de datos
cp deploy/medir_schumann_precursor.py deploy/medir_[senal]_precursor.py
# cambia: la tabla de la señal, los canales, la fuente de eventos
# NO cambies: los controles (ventana, semilla, EPOCA_D, forma ev-ev)
```

### 5. Corre el barrido completo

```bash
# barrido de ventana: si hay efecto, sale en SU escala
for V in 24 72 168 336; do
  medir_[senal]_precursor.py <db_eventos> <db_senal> $V $V 53 [tabla]
done

# en la escala que asome: once semillas
for S in 53 1 2 3 7 42 99 123 555 888 31337; do
  medir_[senal]_precursor.py <db_eventos> <db_senal> 24 24 $S [tabla]
done

# control estacional: estrecha el empareje
for E in 180 30 7; do
  medir_[senal]_precursor.py <db_eventos> <db_senal> 24 24 53 [tabla] $E
done
```

### 6. Interpreta

| Resultado | Veredicto | Acción |
|---|---|---|
| Efecto estable a 11 semillas + sobrevive ±7 días | **Candidato real** | Publica, replica en otra estación |
| Efecto que muere a ±7 días | **Fuga estacional** | Busca la variable de calendario |
| Efecto inestable entre semillas | **Ruido de muestreo** | Más muestra o mejor empareje |
| Sin efecto en ninguna escala | **Nulo** | Cierra la hipótesis, escribe la bitácora |

### 7. Documenta (aunque sea negativo)

Una bitácora completa del nulo vale MÁS que un positive no replicado:
ahorra a la siguiente persona tres años del mismo error. Incluye:
- la hipótesis declarada antes de medir
- el barrido completo con sus números
- los controles que se aplicaron
- la descomposición del efecto (si aplicable)
- las lecciones de proceso

---

## Lo que NO hay que hacer (lecciones del proyecto)

- **No** calibrar umbrales sin medir su distribución primero (regla 8).
- **No** aceptar un efecto que solo aparece con una semilla.
- **No** explicar un residuo con una teoría elaborada antes de aplicar el
  control más barato siguiente.
- **No** integrar al backcast un canal medido en nulo.
- **No** seguir refinando el instrumento cuando lo que falta es una
  hipótesis que funcione.
