# 🔧 Rebuild completo — reporte final
*Generado 2026-09-21 14:25 UTC*

## Pasos ejecutados

| Paso | Estado | Tiempo |
|---|---|---:|
| Parar launcher | ✅ | 0s |
| Vaciar memoria aprendida | ✅ | 2s |
| init_database (migración + índices + vistas) | ✅ | 0s |
| Tuning previo (ANALYZE + optimize) | ✅ | 0s |
| Entrenamiento completo | ✅ | 60311s |
| Disciplina + barrido (cruces) | ✅ | 107s |
| Tuning final (VACUUM + ANALYZE) | ✅ | 50s |
| Generar reportes | ✅ | 1s |

**Duración total:** 1008 min · **Tamaño DB:** 933.6 MB

## Memoria reconstruida
- Firmas: **14,616** (10,734 consolidadas)
- Patrones cimáticos: **234,982**
- Rutas de propagación: **0** globales · **0** locales

## Pesos por bot

| Bot | Peso |
|---|---:|
| alfa1 | 1.354 |
| beta1 | 1.425 |
| beta2 | 1.354 |
| delta | 1.286 |
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
| loki | None | None | None |
| omega | 1.0 | 0.997 | 0.003 |
| padre | 1.0 | 0.997 | 0.003 |

## Asertividad viva (append-only, no se tocó)
- {'ACIERTO': 15015, 'FALLO': 72, 'FALSO_POSITIVO': 942, 'PENDIENTE': 306}

*Reporte autogenerado por deploy/rebuild_completo.py*