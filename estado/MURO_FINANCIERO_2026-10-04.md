# Muro financiero, donde se quedo Claude (2026-10-04)

Claude midio el muro de 5 y se corto al calibrar el detector financiero contra historia.
No cambio comportamiento. Suite en verde. Diff suyo: `muro_cinco_eventos.py` (+53/-9), docstring.

## Lo que ya quedo medido (Claude)
- 5/5 nunca ocurre en 6915 ciclos. Financiero encendido 0,0 %. Con ese muro muerto, 5/5 es inalcanzable.
- 4/5 solo 20 ciclos. El umbral de 3 ya puesto es el optimo contra M>=6.0 en 24 h (ganancia 1,93x). No subirlo.
- Los pesos son constantes (0,95/0,9/0,7) y no aportan frente al conteo simple.
- El detector exige 2 de 4 extremos. Si falta el dato, los defaults son neutros y nunca dispara.
- En vivo, el cable si llega: fear_greed 67, vix 15,31, btc +4,68 %, market_signal neutral. Cero de cuatro: el mercado esta en calma, no es un cable roto.

## Lo que comprobe yo, solo lectura, 2026-10-04 12:50 CST
Tabla `tbl_psique_financiera`, 4125 filas, de 2014-09-17 a 2026-01-01 (se corto en enero).
- `fear_greed`: NULL en las 4125. La columna existe, el dato no.
- `yield_spread`: NULL en las 4125.
- `vix`: 1285 NULL; 156 filas con vix > 30.
- `btc_precio_usd`: completo.
El fear_greed 67 de la lectura en vivo no sale de esta tabla. Calibrar el detector contra ella, como iba a hacer Claude, no se puede hasta saber de donde sale el 67 y por que la columna historica esta vacia.

## Siguiente, sin tocar comportamiento
C rastrea de donde sale el fear_greed en vivo y por que la columna historica esta vacia. T revisa. Nada de umbrales ni de pesos hasta esa respuesta. El financiero muerto sigue siendo la causa de que 5/5 sea imposible, pero hoy no se puede decir si es el mercado en calma o un dato que nunca se guardo.

## Rastreo de C, 2026-10-04 12:57 CST (G lo anota)
- El 67 lo trae `fetch_fear_greed_index` (alternative.me, `crypto.py`) y `fetch_delta_data` lo pone en el dict (`data_pipeline.py`). El muro lo lee de ahi. No son los defaults.
- En la base no se guarda el 67. Queda `|67-50|/50 = 0.34` en `tbl_delta_cross.sentiment_coupling`.
- VIX 15.31 es el cierre vivo de Yahoo. El +4.68 es `btc_ret_win`.
- `tbl_psique_financiera` la llena el backcast solo con precio y volatilidad. `fear_greed` nace NULL en un ALTER y el camino en vivo nunca la escribe. `fetch_flags` NULL en las 4125: el backfill no corrio. VIX si tiene 2840 filas, ultima 2025-12-31 con 14.95.
- Conclusion: calibrar el umbral de fear contra esa tabla no se puede. El muro financiero apagado, hoy, es mercado en calma, no un cable roto.

## Contexto completo de Claude, anotado 2026-10-04 13:00 CST
Commits en HEAD, cargados por el launcher de las 12:44 de hoy:
- b465b3b (1-oct 16:23) Schumann a sos70.ru con puerta sha256. Latido 13429, 2026-10-01 16:35, hz=7.86, actividad=1.62. NULL si la imagen no cambia.
- 64ac733 (1-oct 16:40) filtro de mismo evento del Juez. 657 filas a 27 episodios, 3 por bot, igual a los 3 sismos M>=4.5 de esa ventana.

Cerrado al volver: el ONNX del 4-oct corrio a las 12:44 (la maquina estaba apagada a las 03:04). El filtro de episodio ya esta cargado.
Sigue sin hacerse, y solo con GO del Capitan: borrar los pesos y reentrenar. Claude lo dejo pedido y no lo hizo. El ONNX de hoy no borro pesos.

Frase que Claude no alcanzo a cerrar: "mira lo que delta si produce y el muro ignora". Va en el mismo pase de solo lectura que SEISMIC_CLUSTER y SILENT_TRIGGER.

## Pase de C, 2026-10-04 13:04 CST
- El muro financiero solo lee fear_greed, vix, btc_change_pct y market_signal, y pide 2 de 4 en panico (`scanner.py:518-526`). Delta ademas trae dominancia, volatilidad de bitcoin, yield, score, acoples y estado geomagnetico, y el muro no los usa.
- Ahora: fear 65, VIX 15.31, bitcoin +5 %, senal neutral. `geo_storm_active` esta en 1 y el regimen dice GEOSTORM, pero el muro financiero no tiene rama para eso. Sigue en 0 en 7026 ciclos.
- `SEISMIC_CLUSTER` es el muro geofisico: 23 o mas sismos M4+ en 24 h (`precursor_types.py:226`). 82.05 % encendido. El 99.2 % de los ciclos con geofisico ON son solo ese detector.
- `SILENT_TRIGGER` es el muro solar y enciende por calma (kp menor a 2 y media de 1.5 o menos). 55.02 %. Juntos, el 44 % de los ciclos. Si vacian la premisa de dominios distintos a la vez.
- Detectores sin cambios. T revisa. Siguiente en la lista de Claude: TSUNAMI al 27.9 %.

## TSUNAMI, C, 2026-10-04 13:10 CST
No mide tsunamis. Enciende si la magnitud maxima es 7 o mas y la profundidad es menor a 70 km (`precursor_types.py:259`). Nadie escribe la profundidad: el scanner usa 30 km por defecto (`scanner.py:486`), y 30 siempre pasa el corte. El catalogo son los 500 sismos M>=2.5 mas recientes, no 30 dias.
En 7027 ciclos encendio 1931 (27.48 %). El muro oceanico es exactamente eso: huracan en cero. El M7.4 de Colombia del 10 de agosto esta a 110 km y aun asi encendio 1217 ciclos porque la profundidad quedo en 30. Ahora esta apagado: el maximo del catalogo es 6.6. Detector sin cambios. Falta la revision de T y el conteo del 23 de SEISMIC_CLUSTER.
T aprobo el codigo (13:12). La linea del default es 486, no 485. No reconto los 1931 ni los 1217.

## SEISMIC_CLUSTER, el conteo del 23. C, 2026-10-04 13:16 CST
El 23 no es el p90 de lo que entra hoy. El docstring dice que 23 es el p90 del backcast diario (media 15.6). En tbl_eventos_sismicos_fuente, 11688 dias de 1994 a 2025, el p90 es 27, la media 17.8, y el dia pasa de 23 el 18.7 % de las veces, no el 10 %.
Lo que entra ahora es un conteo rodante de 24 h (data_pipeline.py:290), M>=4 dentro del fetch de 500. Sobre 7028 ciclos: p50 22, p90 37, pasa de 23 en el 47 %, no en el 82 %. El 82 % es la bandera, inflada: hasta el 20 de septiembre quedo encendida al 100 % aun en dias cuyo maximo rodante era 10-22, porque el entero guardado era el de los ~500 eventos, no el de 24 h. Desde el 26 de septiembre el guardado si es el de 24 h (23, 26, 27). Ahora el LOCF trae 26. Umbral sin tocar. T no ha recontado.

## Cierre de la medicion, T, 2026-10-04 13:20 CST
T reconto y cuadra. 11688 dias, media 17.8, p90 27, 18.7 % de los dias con 23 o mas. Sobre 7029 ciclos el rodante da p50 22, p90 37 y pasa de 23 en el 47.1 %. La bandera geofisica esta en el 82.7 %. Umbral quieto.
Siguiente, sin aplicar: C prepara el diff para guardar la profundidad real del catalogo en vez del default de 30 km. Un M7 a 110 km no debe encender TSUNAMI. T revisa.
