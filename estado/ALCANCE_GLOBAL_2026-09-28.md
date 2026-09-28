# El alcance es global, y la malla todavía no llega — 2026-09-28

Para fundir en `estado/BITACORA_2026-09-26.md` como **§24** cuando se pueda
(quedó como archivo aparte porque el clasificador de comandos estaba caído y no
se pudo hacer el append ni el commit). **Sin commit.**

Empezó con una corrección del operador que hay que dejar escrita porque el error
era conceptual: propuse backfill satelital de «las tres zonas (guerrero_gap,
oaxaca_costa, chiapas)» y me contestó *«no sé en qué momento estás pensando que
solo nos importa México cuando estamos haciendo el sistema global»*. Tenía razón.
Tomé las tres zonas del baseline de alfa2 —un artefacto de SU implementación— y
las traté como el alcance del sistema.

## 1. El alcance de cada sensor, que no estaba documentado en ninguna parte

| bot | alcance real de su sensor |
|---|---|
| alfa1 | **planetario**: Kp, Bz y viento solar son escalares globales, sin geografía |
| beta1 | **una estación**: Tomsk, Siberia. Un punto para una cavidad global |
| beta2 | global (MSVOLSO2L4 cubre todos los volcanes) |
| delta | global (mercados) |
| capa sísmica | **global, 125 nodos UVG** |
| **alfa2** | **3 polígonos mexicanos** |

alfa2 es el único cuyo alcance se encogió a una región. Y el Juez lo califica
contra el catálogo global, así que lo puntúa por eventos que **estructuralmente
no puede ver**. Eso es peor que su rasgo faltante.

**Medición pendiente:** qué fracción de los eventos que el Juez le cobra a alfa2
caen dentro de sus tres cajas. Si es el 2 %, ese número cuenta la historia entera.

## 2. alfa2: el diagnóstico correcto

No está apagado: es **notificador por decisión del operador del 2026-09-24**,
documentada en `entrenamiento.py:175`. Sus tres rasgos no alcanzan
`MIN_DIMENSIONES_COMPARABLES = 4`, y por debajo de ese suelo `similitud()`
devuelve 0,0 —una firma no empareja ni consigo misma.

El problema de fondo no es el conteo de rasgos: **dos de los tres miden el
INSTRUMENTO, no el planeta.** `coverage_score` y `clear_passes` son «cuán
despejado estaba el cielo para el satélite». El tercero, `thermal_anomalies`, era
un 0 puesto a mano: un solo valor distinto en 2.817 filas. No le faltaba
historial —nunca estuvo mirando la Tierra.

Corrección a lo que yo mismo creía: **el conector de la ESA ya está verificado**
(`esa_frp.py`, `VERIFICADO_CONTRA_PRODUCTO_REAL = True` desde el 26-sep, con los
cuatro NetCDF mapeados por Agente-C). El `invalid_grant` era una línea sin
comillas en `deploy/.env` que rompía el `source`, no la contraseña.

**Y aun así, FRP probablemente no es la variable.** Es potencia radiativa del
FUEGO: vale cero casi siempre. Darle a alfa2 un cuarto rasgo que es 0 en el 99 %
de las ventanas es el defecto que se mató esa misma noche —un rasgo que no
discrimina (regla dura 8) y que el modelo puede aprender como procedencia. La
propuesta legacy ordena las variables satelitales así: **deformación, temperatura
de superficie, SO₂ y TEC**. FRP no aparece. `S3_SL_2_LST` es el mismo satélite, el
mismo conector y el mismo archivo, y da un valor en CADA pasada.

## 3. `uvg.docx`: lo que el documento pide

Dentro de `drive-download-20260927T232027Z-1-001.zip`. Es el diseño del mapa de
nodos y del flujo energético entre ellos. Pide ficha por nodo —estado activo /
atenuado / apagado relativo / desplazado / fantasma, tipo, profundidad, cercanía a
nódulos polimetálicos, firma cimática, historial de eventos liberatorios— y
**enlaces entre nodos** clasificados en hermano fuerte, hermano débil, enlace
fantasma y enlace inactivo, medidos por correlación temporal, retardos y similitud
de firmas.

Nodos de arranque que nombra: **Clarion-Clipperton, Baikal, y los polos
geomagnéticos con su trayectoria de migración.**

## 4. La malla no llega a ninguno de los cuatro

Medido contra `MATRIZ_UVG_125` con haversine:

| nodo de arranque del documento | nodo más cercano de la malla | distancia |
|---|---|---:|
| Clarion-Clipperton | Baja California Sur | **2.635 km** |
| Baikal | Japón Tohoku | **3.106 km** |
| Polo norte geomagnético | Ghost Iceland-Jan Mayen | **2.944 km** |
| Polo sur geomagnético | Nueva Zelanda | **3.535 km** |

La malla es global de verdad (lat −57 a 67, lon −178 a 178; 50 real + 50 ghost +
25 geobattery) pero su **|lat| máximo es 67°: no hay un solo nodo polar**.

## 5. Y la métrica de asignación está rota donde el documento quiere ir

`geometria_uvg.nodo_mas_cercano` usa **distancia euclidiana en grados**, no
haversine. El propio archivo lo avisa y propone «evaluar haversine en un parche
separado». Un grado de longitud son 111 km en el ecuador y ~19 km a 80° de
latitud, y en el antimeridiano el error es catastrófico: el nodo 64 (Ghost
Tonga-Fiji, lon −178) y el 68 (Ghost NZ-Hikurangi, lon +178) están a 4° reales y
la métrica los ve a **356°**.

Medido sobre cinco ubicaciones reales, **dos mal asignadas**:

| sismo | nodo que elige | km | nodo real más cercano | km | error |
|---|---|---:|---|---:|---:|
| Fiji (−18, 179,5) | Ghost Vanuatu | 1.243 | Ghost Tonga-Fiji | 264 | **+978** |
| Aleutianas (52, −179) | Ghost Alaska-Aleutian | 982 | Ghost Aleutian W | 411 | **+572** |
| Kermadec (−25, −177,5) | Tonga-Kermadec | 612 | Tonga-Kermadec | 612 | 0 |
| Kuriles (47, 154) | Ghost Kamchatka-Kuril | 134 | Ghost Kamchatka-Kuril | 134 | 0 |
| Svalbard (78, 10) | Ghost Iceland-Jan Mayen | 1.377 | Ghost Iceland-Jan Mayen | 1.377 | 0 |

**Por qué bloquea el documento entero:** su petición central es la correlación
entre nodos hermanos. Si los sismos se asignan al nodo equivocado, esa correlación
mide otra cosa. Es el mismo defecto que puso el **M7.4 de Chocó, Colombia
(2026-08-10) en «Chiapas Subducción» con 1.700 km de error** —documentado en el
propio `geometria_uvg.py`, v2.5.2— salvo que aquel se arregló y **este
sobrevivió**.

## 6. Por qué no se tocó esta noche

Cambiar la métrica **cambia a qué nodo mapea cada sismo**, y las 22.025 firmas
actuales se construyeron con la asignación euclidiana. Aplicarlo sin rebuild
dejaría el histórico y el ciclo vivo hablando de nodos distintos: exactamente el
desajuste entrenamiento-vivo que ocupó todo el día. **Va junto con el próximo
rebuild, no antes.**

Y extender la malla necesita decisión del operador: `_generar_matriz_125` **exige
exactamente 125 nodos y revienta si no**. Meter Clarion-Clipperton, Baikal o un
nodo polar significa quitar otro, o cambiar ese invariante.

## 7. Orden propuesto

1. Medir qué fracción de los eventos de alfa2 cae dentro de sus tres cajas (§1).
2. Hacer global la cobertura viva de alfa2: consultar LST en las posiciones de los
   125 nodos en vez de 3 polígonos. **No necesita backfill.**
3. Haversine en `nodo_mas_cercano`, **con** el rebuild.
4. Decisión del operador sobre la malla: ¿125 nodos fijos, o se amplía para cubrir
   los nodos de arranque del documento?
5. Backfill de LST incremental, priorizando nodos con historia sísmica real.
