# 🔧 Rebuild completo — reporte final
*Generado 2026-09-26 16:39 UTC*

## Pasos ejecutados

| Paso | Estado | Tiempo |
|---|---|---:|
| Parar launcher | ✅ | 0s |
| Vaciar memoria aprendida | ✅ | 25s |
| init_database (migración + índices + vistas) | ✅ | 0s |
| Tuning previo (ANALYZE + optimize) | ✅ | 0s |
| Entrenamiento completo | ✅ | 7404s |
| Disciplina + barrido (cruces) | ✅ | 117s |
| Tuning final (VACUUM + ANALYZE) | ✅ | 12s |
| Generar reportes | ✅ | 4s |

**Duración total:** 126 min · **Tamaño DB:** 949.6 MB

## Memoria reconstruida
- Firmas: **19,620** (12,889 consolidadas)
- Patrones cimáticos: **279,408**
- Rutas de propagación: **500** globales · **268** locales

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
| jupiter | 0.007 | 0.007 | 0.0 |
| loki | 0.399 | 0.397 | 0.003 |
| omega | 1.0 | 0.998 | 0.003 |
| padre | 0.998 | 0.99 | 0.007 |

## Asertividad viva (append-only, no se tocó)
- {'ACIERTO': 19439, 'FALLO': 313, 'FALSO_POSITIVO': 1227, 'PENDIENTE': 225}

*Reporte autogenerado por deploy/rebuild_completo.py*