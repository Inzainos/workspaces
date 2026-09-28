# Dashboard — Sentinel Omega

Dos tableros conviven, con propósitos distintos:

| | Stack | Puerto | Estado |
|---|---|---|---|
| **Moderno** | React 19 + Vite 6 + Tailwind 4 → FastAPI | `5173` (dev) → `8787` (API) | **el que se trabaja** |
| Legacy | Streamlit + Plotly (11 pestañas) | `8510` | se conserva, no se amplía |

```bash
# API (siempre primero: el front sin ella no tiene datos)
python -m uvicorn sentinel_omega.infrastructure.dashboard.api:app --host 127.0.0.1 --port 8787

# Front en desarrollo
cd sentinel_omega/infrastructure/dashboard/web && npm run dev

# Build de producción → dist/
npm run build
```

---

## Sistema de diseño (v3, 2026-09-28)

Vive en `web/src/index.css` (tokens) y `web/src/components/ui/data.tsx`
(primitivas). Tres reglas mandan sobre el gusto:

### 1. El color saturado significa riesgo. Nada más.

La rampa de riesgo (`--color-calma`, `--color-atencion`, `--color-aviso`,
`--color-critico`) es la única familia saturada del tablero. Todo el cromo
—bordes, fondos, ejes, etiquetas— vive en la rampa neutra fría
(`--color-base-*`). Las series de gráfica usan `--color-serie-*`, azules y
teales desaturados a propósito: **una línea de datos nunca debe confundirse
con un estado de riesgo**.

`--color-accent` es acento de *interfaz* (foco, tab activo, enlace), jamás de
dato. Si un número sale azul, no significa nada.

Los cuatro colores de riesgo comparten luminancia (~0.72 L en oklch), así que
ninguno grita más fuerte que otro por accidente. La rampa es oklch porque al
interpolar no se ensucia como HSL.

### 2. Número comparable = cifra tabular.

El tablero se lee en diagonal. Una columna de métricas que baila
horizontalmente no se puede comparar. `.tnum` / `.mono` fuerzan
`tabular-nums`, y `DataTable` alinea a la derecha toda columna marcada
`num: true`.

Tipografía: **IBM Plex Sans/Mono**, elegida —no heredada— por su `0` rebanado
y su `1` con base, que a 11px distinguen un `0.01` de un `0.07` sin acercarse.

### 3. Lo que no se midió se ve distinto de lo que midió cero.

`.dato-ausente` pinta el guion de "sin lectura" en un gris que **no** es el del
texto normal. La primitiva `<Cifra>` lo aplica sola ante `null`, `undefined`,
`""` o `NaN`. Es la regla dura 8 del proyecto llevada al pixel.

---

## Superficies

Cada pestaña se diseñó contra **una** superficie, y eso manda sobre la
composición (no al revés). Un dashboard no es una landing: darle un hero
centrado con tres tarjetas iguales es el error más común y el más caro.

| Pestaña | Superficie | Qué implica |
|---|---|---|
| Presentación | **Decide/Learn** | la única donde un hero es correcto |
| Principal | **Monitor** | densidad, lectura de reojo, sin hero |
| Predicciones | **Monitor** | estado de precursores y ventana |
| Mapas | **Explore** | mapa primero, controles al margen |
| Señales | **Monitor** | telemetría cruda por familia |
| Modelos | **Compare** | 9 bots enfrentados, columnas alineadas |
| Reportes | **Explore** | bitácora navegable |

---

## Primitivas (`components/ui/data.tsx`)

| Primitiva | Para qué |
|---|---|
| `<Panel>` | contenedor con título, meta y **nota al pie** (por qué importa el dato) |
| `<Metrica>` | métrica con jerarquía `principal` / `normal` / `compacta` y contexto obligatorio |
| `<Cifra>` | número con ausencia explícita; nunca convierte `null` en `0` |
| `<EscalaRiesgo>` | Fantasma sobre su escala real con los umbrales 15/30 dibujados |
| `<SegmentosMuro>` | las 5 paredes como segmentos discretos (un 2/5 se ve como 2 de 5) |
| `<BarraVeredictos>` | aciertos / falsas alarmas / omisiones en proporción real |
| `<ChipFuente>` | estado de fuente, con `CONGELADO` como estado de primera clase |
| `<SinDatos>` / `<BannerError>` | vacío y error honestos |

### Por qué `BarraVeredictos` existe

La asertividad del sistema (97,7 %) **deja los falsos positivos fuera del
denominador** y cuenta como acierto cada silencio en calma. Suena impecable y
esconde 1.651 falsas alarmas. La barra las obliga a ocupar su ancho.

Nunca se enseña sola: va pegada a la ganancia de Molchan. Hoy ese par dice
`97,7 %` junto a `0,84×` — "acierta casi siempre porque casi siempre está en
calma, y sus alarmas todavía no superan a alertar a ciegas". El tablero tiene
que hacer esa contradicción **imposible de pasar por alto**.

⚠️ **Los tres veredictos deben venir del mismo universo.**
`aciertos_total`/`fallos_total` son la suma **por bot** de `TBL_PESOS_BOTS`
(138.068: cada ventana contada una vez por cada bot que opinó). Los veredictos
del sistema salen de `viva_real` (21.400 / 1.651 / 313). Mezclarlos daba una
barra con 0 % de falsas alarmas, que es falso. Usar
`veredictos_sistema` de `/api/bots`.

---

## Contratos de la API que el front asume

| Endpoint | Campo | Contrato |
|---|---|---|
| `/api/health/apis` | `status` | `LIVE` · `LOCF_ACTIVE` · `STALE` · `CONGELADO` · `DESCONOCIDO` |
| | | una fuente ilegible sale como `DESCONOCIDO`, **nunca se omite** |
| `/api/bots` | `veredictos_sistema` | los tres resultados del mismo universo (`viva_real`, `en_vivo=1`) |
| | `totales_son_por_bot` | marca que `aciertos_total` es suma por bot |
| `/api/cimatica/ahora` | `biblioteca_presente` | distingue tabla **ausente** de biblioteca **vacía** |

### `CONGELADO`: frescura no es validez

Tomsk sirvió una imagen estática durante días. El registro se reescribía cada
hora —parecía `LIVE`— con el **mismo valor**. `/api/health/apis` ahora marca
`CONGELADO` cuando la serie no varía en toda la ventana, y el tablero lo
explica en el encabezado. Un semáforo verde sobre una fuente muerta es peor
que no tener semáforo.

---

## Pozos conocidos

- **`tbl_locf_cache.updated_at` es REAL (epoch), no TEXT.** Un `strptime`
  directo lanza `TypeError`. Usar el helper `_edad_horas`, que acepta ambos.
  Hasta el 2026-09-28 un `except: pass` se tragaba **cinco de seis fuentes** y
  el strip mostraba dos chips como si ése fuera el total.
- **`viva_real` sólo filtra por `fase='viva'`.** No excluye los 603 veredictos
  marcados `en_vivo=0` (el día de los dos Sentinel escribiendo a la vez).
  Toda consulta de asertividad necesita además `COALESCE(en_vivo,1)=1`.
- **El correo está muerto desde 2026-09-15.** `tbl_correo_salida` sigue en la
  base pero cero código la lee. No volver a pintarla como canal activo.
- **`Number(x ?? 0)` en una serie** convierte "no hay lectura" en un cero
  dibujable. Filtrar los nulos y decir cuántos faltaron.
- **Radix Tabs ignora `.click()` sintético** (escucha pointer events). Para
  automatizar la navegación hay que despachar `Input.dispatchMouseEvent` por
  CDP, o parecerá que todas las pestañas muestran lo mismo.
