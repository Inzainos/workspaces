# Propuesta: lo implementable de la documentación legacy (27-sep-2026)

Autores: Agente-G (coordinación), con hallazgos de Agente-C, Agente-T y Agente-A.
Para: Claude y el Capitán. Estado: **propuesta, nada implementado.** Todo se revisó en
solo lectura contra la rama `local/recuperacion-datos-2026-09` y la base de producción.
Este archivo no está en commit.

## 1. Qué se revisó

El zip legacy trae 13 archivos, de los cuales 10 son distintos (`Documento (1) (1)` y
`Documento (4) (1)` son copias exactas). **No se coló ningún documento ajeno: los 10 son de
Sentinel.** El más alejado es `uvg`, que trata de la malla de nodos.

| Documento | Tema | Revisó |
|---|---|---|
| `omega` | Visión completa: SNT, dos capas, plan maestro, dashboard, batería, 4D | G |
| `Documento (1)` | ETL histórico y conectores | C |
| `Documento (2)` | Auditoría en PostgreSQL | C |
| `Documento (3)` | Omega sobre PostgreSQL | C |
| `Documento (4)` | Blueprint de jobs, triggers y vistas (raw/stg/core/mart/ops) | C |
| `Documento (5)`, `(6)`, `(7)` | Dashboard, banner en vivo, alertas y botones de Telegram | T |
| `uvg`, `sentinel omega`, `sentinel Omega 2` | Malla UVG, roles por bot, gatillo lunar, geobaterías | A |

`sentinel Omega 2` contiene todo `sentinel omega` excepto la tabla de roles por bot
(30, 16 y 10 años de historia).

## 2. Lo que ya tenemos (no hay que hacer nada)

- Entrenar con todas las magnitudes (la base guarda desde M2.5) y alertar solo desde M4.5.
- Muro de 5 eventos, SNT, mareas (`core/mareas.py`), fase lunar, tipos tsunami, huracán y sprite en `precursor_types`.
- Volcanes en la base (2 922 fuentes, erupciones VEI 3 a 5).
- Nodos real, ghost y geobattery.
- Capas separadas por nombre de tabla (`*_raw`, `*_fuente`, `*_historico`), upserts idempotentes, UTC, `en_vivo`, LOCF marcado, bitácoras de fetch, volcado, cascada y salud.
- El Juez como auditor aparte, que ya guarda quién decidió (`7883a90`); firmas con tiempo de vida (§19).
- Reportes semanal, mensual, comparativo y ejecutivo en `estado/`.
- Dashboard React con encabezado fijo, tira de salud LIVE/LOCF/STALE, telemetría, mapa 2D, globo 3D, heatmap y semáforo VERDE a ROJO en `risk_calculator`.
- Alertas de Telegram con región, nodo, epicentro y hora UTC; digesto horario con botones; Mini App en `/mini`.

## 3. Primero: lo que destapó el cruce con la bitácora (§14–20)

No viene del legacy, pero cambia el orden de todo lo demás.

1. **alfa1, loki y omega están saturados en WATCH** desde las 13:59 CST del 27-sep (42 de 42 ciclos, confianza de 0.67 a 0.79, reglas en neutral). No son alarmas reales. Hay tres causas probables:
   - `so2_kt_win`, `so2_kt_90d` y las erupciones valen 0 en el 100 % de las filas porque `tbl_desgasificacion_raw` está parada desde el 31-jul. Ese 0 es "no hay dato", y `so2_kt` es el rasgo que más separa las firmas (§19.4).
   - `delta_schumann_coupling` y `delta_cross_coupling` llegan como NaN.
   - `kp_max_72h` vale 0 mientras `kp_max` vale 1.
2. **omega da dos veredictos en la misma fila.** `analyze()` con `pad_vector` da NEUTRAL 0.42 y `_aplicar_modelos` da WATCH 0.71. Uno de los dos vectores está mal armado; se sospecha de `pad_vector`.
3. **Las reglas de omega y Loki están ciegas.** Comprobado en omega: su regla escribe "Bz=sin dato; Kp=sin dato" aunque el ciclo trae Bz de -0.93 y Kp, y busca `bz`/`bz_nT` y `kp`/`kp_max`. En Loki el runner manda `bz_gsm`; en omega falta confirmar qué nombres de campo le llegan (lo trae el diagnóstico de C).
4. **beta1 parece real** (32 % de WATCH, igual a su tasa histórica; hay sicigia y un M6.6 en la ventana). beta2 coincide con su regla desde las 09:32.

Propuesta de orden:
1. Diagnosticar el doble veredicto de omega y alinear los nombres de campo de omega y Loki (C, revisa T).
2. Bandera de "rasgo presente" que cubra SO2, erupciones, Kp y Schumann, para que el vector pueda decir "no lo sé" (§20.4 punto 2).
3. Recuperar la desgasificación.
4. Después decidir `_aplicar_modelos` (§20.2). La regla asimétrica que propone T (el modelo puede subir una alarma, pero solo la baja si confía más que la regla) no cambia nada hoy, porque aquí el modelo sube.
5. Rematerializar `tbl_juez_rasgos_reconstruidos`.

### 3.1 Diagnóstico de C (27-sep, 18:16, solo lectura; corrige las hipótesis de arriba)

- **Causa real del WATCH de alfa1, loki y omega: `kp_mean`,** no el SO2 ni los acoplamientos (esos rasgos no entran en los vectores de estos tres bots). En el entrenamiento, `kp_mean` valía 0 en el 100 % de las firmas con evento y, cuando traía valor, la firma era NEUTRAL (594 de 594 en omega). El modelo aprendió la presencia del dato como etiqueta. A las 13:59 `kp_mean` bajó de 0.333 a 0.302 y los tres pasaron a WATCH (44 de 44 ciclos). Con `kp_mean` entre 0.33 y 2.0 vuelven a NO_SIGNAL o NEUTRAL.
- `noaa.py` baja Kp por minuto (~6 h) y `launcher.py:726` lo promedia. `kp_max_72h` toma `kp[-24:]` (`launcher.py:731`): son 24 minutos, no 72 h.
- **Los dos veredictos de omega:** el vector de `analyze()` va todo en ceros, porque `_feature_vector` busca `bz`, `kp`, `viento`, `fase_lunar` y `es_sicigia`, y el `omega_data` del runner (`layer_runners.py:478`) no trae ninguna. El vector correcto es el de `_aplicar_modelos`.
- **Claves reales:** omega recibe Bz como `bz_gsm` dentro de `omni_dataframe`, sin escalar; Kp no le llega (`kp_series` solo va a beta1), ni viento, fase lunar o sicigia; `schumann_mean` se pide a beta1, que no lo produce. Loki lee `bz`, `schumann_activity` y `lod`, y le llegan `bz_gsm`, `schumann_resonance` (7.83 fijo) y `lod_ms`; además el runner (:495–508) inventa Bz 0, viento 400 y VIX 20 cuando falta el dato. alfa1, beta1 y jupiter coinciden.
- **El servicio corre código anterior al que está en disco:** las 44 filas no traen la clave `gano`, que el `layer_runners.py` sin commit sí escribe.

**Propuesta de C (borrador, no aplicado; espera a que Claude libere el árbol y la revisión de T):**
1. Claves: el runner fusiona `_rasgos_del_ciclo()` en `omega_data`; omega acepta `bz_mean`/`bz_gsm`, `kp_mean`, `viento_avg`; Loki acepta `bz_gsm`, `schumann_activity`, `lod_ms`, sin valores inventados, y emite NO_SIGNAL si falta el dato.
2. Un solo veredicto: quitar el ONNX de `omega.analyze()` (como se hizo con alfa1). Kp: `kp_max_72h` desde `tbl_clima_espacial_raw` (misma fuente del entrenamiento); `kp_mean` por hora o del feed de 3 h.
3. Máscara de rasgo presente ya, sin reentrenar: `RASGOS_CLAVE` por bot; si falta un rasgo clave o cae fuera del rango de entrenamiento, el modelo se calla y manda la regla. En el próximo reentrenamiento: bit de presencia por grupo (Kp, Schumann, so2, erupciones, acoplamientos), faltantes con la mediana y no con 0, `isfinite` en los acoplamientos delta, y renombrar el so2 de OWM a `so2_proxy_owm`.
3b. **Ajuste acordado por T y C (18:17):** la máscara por rango no apaga este caso, porque `kp_mean`=0.30 está presente y dentro del rango de entrenamiento (hubo ceros), y un Kp real de 0 a 1 en días tranquilos volvería a saturar aunque se corrija la agregación. Se agrega `RASGOS_CON_FUGA = {"alfa1", "loki", "omega"}: ["kp_mean"]`: mientras un bot tenga un rasgo en esa lista, `senal_desde_rasgos` devuelve None y decide la regla, con las claves ya corregidas. `_aplicar_modelos` guarda el motivo (`onnx_callado: "fuga:kp_mean"`) para no confundirlo con `onnx: False` ("no hay modelo"). La marca se quita solo al reentrenar con el bit de presencia. Tests: esos tres bots no dan WATCH por modelo con `kp_mean`=0.30, y la regla lee el Bz real del ciclo sin escribir "sin dato". Con esto, la regla asimétrica y el GO d solo tienen que cubrir el histórico.
4. **No reentrenar antes de cerrar la fuga de presencia:** con los datos actuales aprendería lo mismo.

Diffs: `C:\Users\elanz\AppData\Local\Temp\omega_diag\REPORTE_omega_diag.md`. Esto refuerza el GO d.

## 4. Lo que se perdió y se puede implementar

### Antes o dentro del punto 7 (costo bajo)

| # | Propuesta | Dónde entra | Origen |
|---|---|---|---|
| 1 | `tbl_job_run`: tarea, inicio, fin, estado, filas y error de cada corrida | rutinas, mantenimiento, reentrenamiento, launcher | Doc (4) |
| 2 | `v_frescura_fuentes`: último dato y horas de atraso por fuente. Ya muestra la desgasificación parada desde el 31-jul y la astronomía desde el 31-dic-2025 | vista SQL (DDL, con respaldo) | Doc (4) |
| 3 | Trigger `BEFORE INSERT` que rechace **solo** la combinación exacta 7.83 con actividad 0 en PREC y `tbl_schumann_vivo` (un 7.83 real de Tomsk debe pasar) | base | Doc (2) |
| 4 | `tbl_clases_evento` con las 11 clases hoy sueltas como texto | base | Doc (4) |
| 5 | `gatillos_candidatos`: separar la carga (ventana de 1 a 14 días) del disparo. El gatillo lunar lleva fase, distancia, perigeo o apogeo y tensión de marea regional. Beta2 marca Luna y mareas como gatillo, no como precursor | base y Beta2 | `omega`, `sentinel Omega 2` |
| 6 | Tabla de verdad contra predicción, solo con `en_vivo=1` | tablas del Juez y dashboard | Doc (5)–(7) |
| 7 | Procedencia por campo en PREC (`fuente_bz`, `fuente_schumann`), tabla de rechazos para auditar cada "no hay dato", checkpoint por fuente y lotes de ingesta con sha256 | ingesta | Doc (1) |
| 8 | Reportes que faltan: anual, de precursores (ventanas de 1 a 14 días) y de correlación entre nodos | `estado/` | `omega` |
| 9 | Dashboard: volver a montar `PadreJuezTab`, `ConsensoTab` y `LokiTab` (existen, App dejó de mostrarlas); reloj UTC y UTC-6; hora local en las alertas; etiquetas "En vivo" y "Consolidado" usando `en_vivo` | `App.tsx`, `alert_enrichment` | Doc (6), (7) |

### Después del pipeline (costo medio)

- Poblar tsunamis, huracanes, sprites y TLE desde NOAA y NHC (`noaa_hazards.py`). Hoy `tbl_eventos_no_sismicos` solo tiene volcanes y tormentas Kp, y las tormentas se quedaron en 2017.
- Botones de consulta en Telegram (Estado, Alertas activas, Nodos en vigilancia, Predicción 24 h y 72 h, Último reporte, Salud) usando los endpoints de `api.py`.
- `tbl_auditoria_cambios` con triggers OLD/NEW en JSON, solo para `TBL_PESOS_BOTS`, los UPDATE/DELETE del Juez y los DELETE del mantenimiento sobre PREC.
- Etapas de cada firma (nueva, observada, recurrente, consolidada); el Juez solo castiga desde consolidada. Revisar contra §19.
- Castigo desigual: pesa más no avisar de una firma conocida que dar una falsa alarma. El Juez no cambia pesos en vivo; las correcciones se aplican fuera de línea.
- Entrenar con bloques de 3 meses mezclados de años distintos, **dejando entre cada bloque de prueba y los de entrenamiento un hueco de al menos la ventana más larga** (LOCF y ventanas de 72 h cruzan bordes).
- Ficha de cada nodo UVG (coordenada ideal y ajustada; estado activo, atenuado, desplazado o fantasma) y enlaces entre nodos (hermano fuerte, débil, fantasma, inactivo) por correlación con retardo. Empezar por Clarion-Clipperton, Baikal y los polos magnéticos. Es la base del reporte de correlación entre nodos.
- Orden de variables satelitales: deformación, temperatura de superficie, SO2 y TEC.
- Escala de precaución (normal, observación, vigilancia, precaución) **derivada del semáforo actual** y auditada por el Juez, no una escala paralela.
- Batería de la Tierra en la portada: índice compuesto solo de variables reales, con la leyenda de que no es una medida física, y que marque "incompleto" si falta un insumo.
- Galería de cimática (top 5 o 10) y alarmas del tablero con causa, bots, ventana y acciones.
- Al final: la capa limpia frente a la capa SNT (dos lecturas de los mismos datos, con el Juez comparando cuál acierta más), y el marco del hipercubo 4D solo si ayuda a leer mejor (hoy no aparece en el código).

## 5. Lo que no aplica

- Lo exclusivo de PostgreSQL (particiones, `pg_cron`, CDC, roles, jsonb, vistas materializadas, PostGIS): producción es SQLite.
- Airflow o Dagster: systemd basta.
- Reorganizar el repo en raw/stg/core/mart o en `docs/etl/analytics/dashboards`, y los dos dashboards separados o las 10 pestañas: lo que falta se integra en las 7 pestañas actuales.
- La cadena de hashes tipo ledger para el Juez.
- El puente en vivo del Doc (7) que guarda valores provisionales como consolidados: un provisional va con `en_vivo=0` o fuera de la base, y nunca rellena huecos.
- El umbral de 1.23 a 1.5 V de las geobaterías: no tiene fuente medible, se queda como hipótesis.
- Los horizontes de 30, 16 y 10 años, salvo donde la base de verdad cubra esos años. No se rellenan.
- Fondos, arte por bot y modo claro: cosméticos.
- El estado de plataforma "Óptimo" sale solo de `/api/health`, nunca del riesgo sísmico (ya es así).

## 6. Decisiones pendientes del Capitán

- **a)** Pasar a `en_vivo=0` las 823 filas con 8.26/21.46 (ids 11114–11936) y las 160 con 25.0/21.46 (ids 38–8466) de PREC. Son relleno y hoy los lectores que filtran por `en_vivo` no las excluyen. Con respaldo y conteo antes y después.
- **b)** Sacar de git `estado/REPORTE*.md` y las gráficas (`git rm --cached` y `.gitignore`), que volvieron a entrar en `a0b82e1`. Los archivos se quedan en disco.
- **c)** Apagar la unidad de usuario `sentinel-omega-mantenimiento.timer`, que choca con la de sistema (las dos arrancaron a las 00:00; explica las dos noches sin mantenimiento de §20.4). Comando sin sudo: `systemctl --user disable --now sentinel-omega-mantenimiento.timer`.
- **d)** Que el Juez no cuente como acierto ni fallo las WATCH de alfa1, loki y omega posteriores a las 13:59 CST del 27-sep, hasta que esté la bandera de rasgo presente.
- **e)** La regla de `_aplicar_modelos` (§20.2), después del punto 3.

## 7. Notas para el push

- Sin tokens en HEAD ni en los 11 commits desde `50e9e45` (revisó A con el patrón amplio de §15).
- No empujar `main` (13 adelante y 127 atrás de `origin/main`); nunca un push forzado.
- La rama activa no tiene remota; en GitHub está `local/recuperacion-datos-2026-09-limpia`. Empujar la activa crea una rama nueva; no forzarla encima de `-limpia`.
- Resolver el GO b antes del push. No usar `git add -A`: hay 15 archivos modificados sin commit de la sesión del Capitán.

## 8. Hashes para la bitácora

| Cambio | Commit |
|---|---|
| Schumann sin lectura viva se guarda NULL | `27f072a` |
| Tests de precursor (18) con Beta-1/Beta-2 | `cd1846f` |
| Bz y viento sin dato se guardan NULL (antes `01284641`, la historia se reescribió) | `75dd298` |
| CoinGecko con llave Demo | `6c032ab` |
| NULL de las 350 filas 7.83/0 hasta la 12164 | UPDATE en base (§14), respaldo `…234900_pre_null_schumann_prec` |

Nota menor (A): cuando falla la red, el log guarda el traceback completo y tapa los errores reales.
