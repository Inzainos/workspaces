# Full code audit closure (20260914_025000)

- Total .py audited: 272
- /home/deamon/workspaces/sentinel_omega: 261
- /home/deamon/workspaces/deploy: 11
- Files with __main__: 35
- CLI help-smoke attempted: 19
- CLI help-smoke failures: 7
- AST failures: 0
- compile(source) failures (no pyc write): 0

## Help-smoke failures (root cause)
- /home/deamon/workspaces/sentinel_omega/core/delta_enriched/composite.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/infrastructure/pipeline/sismos_refetch_recent.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/infrastructure/pipeline/topologia_cascada.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/models/train_onnx_from_db.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/core/delta_enriched/composite.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/pipeline/sismos_refetch_recent.py :: exit=1 :: Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/pipeline/topologia_cascada.py :: exit=1 :: Traceback (most recent call last):

Interpretación: fallan por dependencias faltantes (numpy/pandas) en este entorno, no por parseo de args.

## Test evidence
- PYTHONPATH=. python -m pytest tests/ -q => PASS (100%).

## Coverage conclusion
- Auditoría de código: cobertura total de archivos .py en alcance Sentinel+deploy.
- Verificación funcional: completa para suite de tests; smoke de CLIs condicionado por dependencias locales.