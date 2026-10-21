# El Juez como mecanismo de incentivos — diagnosis con teoría de juegos

> Ítem 4 del plan de mejoras (2026-10-20). Marco: Streb, «Nash, el último
> fundador de la teoría de juegos y la evolución del concepto de equilibrio
> desde Cournot» (UCEMA, DT 572, ~/conocimiento) + los números MEDIDOS del
> sistema. **Es un análisis, no un cambio**: toda propuesta de rediseño del
> mecanismo exige el GO del operador (y calibración medida, regla 9).

## 1. El juego que el Juez define hoy

El Juez no solo AUDITA: define un juego en el que cada bot elige una
estrategia (callarse / alertar) por ventana, y recibe un pago según la
verdad:

| Estrategia del bot | Hay evento | No hay evento |
|---|---|---|
| **Alertar** | +acierto | −1 (falsa alarma) |
| **Callarse** | **−10** (FALLO: omitir evento) | +acierto (calma) |

Con `miss_penalty = 10` vs `false_alarm_penalty = 1` (pérdida asimétrica
deliberada del diseño, core/juez/juez.py), el pago esperado de cada
estrategia para un bot con probabilidad subjetiva `p` de evento:

- Alertar: `p·(+1) + (1−p)·(−1)`
- Callarse: `p·(−10) + (1−p)·(+1)`

**Alertar es la estrategia dominante siempre que `p > 1/11 ≈ 0.09`** —
o sea: con apenas un 9 % de sospecha de evento, el pago racional es
ALERTAR. No es un defecto de los bots: es el equilibrio que el mecanismo
pide (Streb: el equilibrio no describe la virtud de los jugadores,
describe lo que las reglas hacen racional).

## 2. Lo que el sistema MIDE es exactamente ese equilibrio

- Ganancia del sistema (Molchan, viva_real): **0,88×** — por debajo de 1:
  alertar SIEMPRE habría rendido igual o mejor. El propio AGENTS.md lo
  anticipa: «el sistema prefiere sobre-alertar a sub-alertar».
- Asertividad viva ~61 % contra **~94 % del bot mudo**: el sistema
  alarmó en la mayoría de las ventanas aunque casi nunca hubo evento.
- El 8-oct se intentó compensar por mérito («cuánto ahorra cada bot
  frente a callarse siempre») — pero `pesos_por_merito` exige ≥50
  ventanas de evidencia y la fase viva apenas acumula: **el incentivo
  sigue siendo 10:1, el ajuste solo está congelado**.

## 3. Diagnosis

La pérdida 10:1 fue elegida con un propósito bueno (el costo humano de
un evento no avisado > el costo de una alarma de más) — pero se paga en
el otro bolsillo: **cualquier mecanismo con esa asimetría produce
sobre-alerta racional**, y la ganancia <1 que vemos es su firma, no un
fallo de los clasificadores. Ajustar a los bots por alertar de más es
castigar la conducta racional que las reglas crearon.

## 4. Opciones de mechanism design (ninguna aplicada)

| Opción | Qué cambia | Riesgo |
|---|---|---|
| **A. Pago proporcional a la precisión** (score de Molchan como pago directo): el peso del bot sube con su ganancia, no con aciertos crudos | Alinea el pago con la habilidad real | Baja sensibilidad deseada si se aplica crudo |
| **B. Coste de alertar por ciclo activo** (una alarma sostenida paga una vez, no por ventana solapada): ya existe el conteo por EPISODIOS de los reportes — llevarlo al pago del Juez | Mata el spam de solapamiento sin tocar el 10:1 del episodio único | Requiere ventana de deduplicación medida |
| **C. Asimetría graduada por magnitud** (10:1 para M6+, menor para M4): el costo de omitir escala con el evento que la propia tabla `severidad` ya tiene | Más simple de lo que parece: la gravedad anclada en M4.5 ya existe en el código | Requiere relabel de la vara histórica (el blanco objetivo ya documentado) |
| **D. No tocar el pago, medir mejor** (estatuir el modelo nulo por BOT como comparador oficial): la ganancia ya existe; falta que el PESO la lea | Cero cambio de conducta; hace visible quién aporta | No arregla el sobre-alerta, solo lo explica mejor |

## 5. Recomendación

**D primero** (gratis, honesta: el mérito congelado pasa a ser ganancia
reportada por bot), **B después** (los episodios son la unidad honesta
del evento y ya están medidos), y **C solo junto al relabel de la vara**
que el propio reporte declara pendiente. A requiere validar contra
distribución (regla 9) antes de tocar el voto del Padre.

## Referencias
- Streb (2015), UCEMA DT 572: Cournot→Nash — por qué el equilibrio describe
  las reglas, no la virtud (`~/conocimiento/texto/837156254.txt`).
- Severidades: `core/juez/juez.py` (`SEVERIDAD_FALLO_BASE=10`,
  `SEVERIDAD_FALSO_POSITIVO=1`); epifanía de episodios: `baseline.py`
  `evaluar_episodios` (reporte principal, §Molchan).
- Medición viva: `viva_real`, ganancia 0,88× (REPORTE.md del 19-oct).
