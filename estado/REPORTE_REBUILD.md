# 🔧 Rebuild completo — reporte final
*Generado 2026-09-22 07:20 UTC*

## Pasos ejecutados

| Paso | Estado | Tiempo |
|---|---|---:|
| Parar launcher | ✅ | 0s |
| Vaciar memoria aprendida | ✅ | 20s |
| init_database (migración + índices + vistas) | ✅ | 0s |
| Tuning previo (ANALYZE + optimize) | ✅ | 0s |
| Entrenamiento completo | ✅ | 59068s |
| Disciplina + barrido (cruces) | ✅ | 126s |
| Tuning final (VACUUM + ANALYZE) | ✅ | 40s |
| Generar reportes | ✅ | 3s |

**Duración total:** 988 min · **Tamaño DB:** 1011.4 MB

## Memoria reconstruida
- Firmas: **21,198** (11,501 consolidadas)
- Patrones cimáticos: **243,102**
- Rutas de propagación: **499** globales · **268** locales

## Pesos por bot

| Bot | Peso |
|---|---:|
| alfa1 | 1.354 |
| beta1 | 1.425 |
| beta2 | 1.286 |
| delta | 1.286 |
| loki | 1.286 |
| omega | 1.354 |
| padre | 0.826 |

## Sesgo de aprendizaje (realidad vs fantasía)

| Bot | In-sample | Causal | Sesgo |
|---|---:|---:|---:|
| alfa1 | 1.0 | 0.997 | 0.003 |
| alfa2 | None | None | None |
| beta1 | 1.0 | 0.995 | 0.005 |
| beta2 | 0.982 | 0.503 | 0.48 |
| delta | 0.994 | 0.874 | 0.119 |
| jupiter | None | None | None |
| loki | 0.406 | 0.406 | 0.0 |
| omega | 1.0 | 0.997 | 0.003 |
| padre | 1.0 | 0.995 | 0.005 |

## Asertividad viva (append-only, no se tocó)
- {'ACIERTO': 15015, 'FALLO': 72, 'FALSO_POSITIVO': 942, 'PENDIENTE': 306}

*Reporte autogenerado por deploy/rebuild_completo.py*