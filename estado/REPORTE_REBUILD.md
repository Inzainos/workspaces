# 🔧 Rebuild completo — reporte final
*Generado 2026-09-23 21:40 UTC*

## Pasos ejecutados

| Paso | Estado | Tiempo |
|---|---|---:|
| Parar launcher | ✅ | 0s |
| Vaciar memoria aprendida | ✅ | 0s |
| init_database (migración + índices + vistas) | ✅ | 0s |
| Tuning previo (ANALYZE + optimize) | ✅ | 1s |
| Entrenamiento completo | ✅ | 70884s |
| Disciplina + barrido (cruces) | ✅ | 337s |
| Tuning final (VACUUM + ANALYZE) | ✅ | 58s |
| Generar reportes | ✅ | 3s |

**Duración total:** 1188 min · **Tamaño DB:** 1039.5 MB

## Memoria reconstruida
- Firmas: **19,541** (12,848 consolidadas)
- Patrones cimáticos: **279,027**
- Rutas de propagación: **499** globales · **268** locales

## Pesos por bot

| Bot | Peso |
|---|---:|
| alfa1 | 1.425 |
| beta1 | 1.425 |
| beta2 | 1.354 |
| delta | 1.286 |
| jupiter | 0.857 |
| loki | 1.286 |
| omega | 1.425 |
| padre | 0.936 |

## Sesgo de aprendizaje (realidad vs fantasía)

| Bot | In-sample | Causal | Sesgo |
|---|---:|---:|---:|
| alfa1 | 1.0 | 1.0 | 0.0 |
| alfa2 | None | None | None |
| beta1 | 1.0 | 0.998 | 0.003 |
| beta2 | 0.983 | 0.514 | 0.469 |
| delta | 0.994 | 0.874 | 0.119 |
| jupiter | 0.005 | 0.005 | 0.0 |
| loki | 0.399 | 0.397 | 0.003 |
| omega | 1.0 | 0.998 | 0.003 |
| padre | 0.998 | 0.99 | 0.007 |

## Asertividad viva (append-only, no se tocó)
- {'ACIERTO': 15015, 'FALLO': 72, 'FALSO_POSITIVO': 942, 'PENDIENTE': 306}

*Reporte autogenerado por deploy/rebuild_completo.py*