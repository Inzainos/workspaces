# Dashboard de Sentinel Omega

Este documento describe el tablero de control principal del sistema Sentinel Omega.

## Ubicación

`/home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/web/src/`

## Estructura de carpetas

```
src/
├── App.tsx                  # Componente raíz con rutas
├── main.tsx                 # Punto de entrada
├── index.css                # Estilos globales
├── lib/                     # Utilidades y cliente API
│   ├── utils.ts             # Utilidades generales
│   └── ui.ts                # Componentes UI base (env, filtro)
│   ├── api.ts               # Cliente HTTP para la API
│   ├── http_client.ts       # Cliente HTTP endurecido
│   └── network_guard.py     # Cliente HTTP endurecido
├── components/
│   ├── ui/
│   │   ├── componentes.tsx  # Componentes base
│   │   └── ...
│   ├── charts/
│   │   └── componentes.tsx  # Componentes de gráficos
│   ├── CimaticaFigura.tsx   # Componente de cimática
│   ├── SeñalesVivas.tsx     # Señales activas
│   └── tabs/                # Pestañas del tablero
│       ├── PresentacionTab.tsx
│       ├── SintesisTab.tsx
│       ├── PrincipalTab.tsx
│       ├── LokiTab.tsx
│       ├── PadreJuezTab.tsx
│       ├── PrediccionesTab.tsx
│       ├── MapasTab.tsx
│       ├── ModelosTab.tsx
│       ├── ReportesTab.tsx
│       └── WatchdogTab.tsx
└── router.tsx               (opcional, si usas react-router)
```

## Reglas de diseño

1. **Color oscuro por defecto**: Fondo oscuro (#08090a), texto claro (#f7f8f8).
2. **Colores de riesgo**:
   - Verde (#10b981): Bajo
   - Amarillo (#ffc107): Medio
   - Naranja (#ff9100): Alto
   - Rojo (#ff1744): Crítico
3. **Sin emojis**: Usar texto plano para ser accesible y profesional.
4. **Datos reales**: Todos los datos vienen de la API de backend (`/api/*`).
5. **No hardcodear secretos**: Las API keys van en variables de entorno.

## Cómo agregar una nueva pestaña

1. Crear un archivo en `src/components/tabs/NombreTab.tsx`.
2. Exportar un componente funcional llamado `NombreTab`.
3. Importarlo en `App.tsx` y agregar una ruta.
4. Agregar un enlace en `BarraLateral.tsx` y `BarraNav.tsx`.

## Reglas de estilo

- Usar Tailwind CSS para estilos.
- Usar componentes de `src/components/ui/` para consistencia.
- No usar `console.log` en producción.
- Todos los textos en español.
- Fechas en formato `es-MX`.
