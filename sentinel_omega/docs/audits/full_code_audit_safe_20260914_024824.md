# Full code audit (safe functional) 20260914_024824

- Files audited: 272
- AST failures: 0
- py_compile failures: 6
- CLI help-smoke attempted: 19
- CLI help-smoke nonzero/timeout: 7


## py_compile failures
- /home/deamon/workspaces/sentinel_omega/__init__.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/__init__.cpython-311.pyc.128714784436912'
- /home/deamon/workspaces/sentinel_omega/launcher.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/launcher.cpython-311.pyc.128714790707120'
- /home/deamon/workspaces/sentinel_omega/launcher_fixed.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/launcher_fixed.cpython-311.pyc.128714786553216'
- /home/deamon/workspaces/sentinel_omega/orchestrator.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/orchestrator.cpython-311.pyc.128714786212528'
- /home/deamon/workspaces/sentinel_omega/reboot.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/reboot.cpython-311.pyc.128714786222512'
- /home/deamon/workspaces/sentinel_omega/shutdown.py :: [Errno 13] Permission denied: '/home/deamon/workspaces/sentinel_omega/__pycache__/shutdown.cpython-311.pyc.128714782170672'

## CLI help-smoke failures
- /home/deamon/workspaces/sentinel_omega/core/delta_enriched/composite.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/infrastructure/pipeline/sismos_refetch_recent.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/infrastructure/pipeline/topologia_cascada.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/models/train_onnx_from_db.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/core/delta_enriched/composite.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/pipeline/sismos_refetch_recent.py :: exit=1 note=Traceback (most recent call last):
- /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/pipeline/topologia_cascada.py :: exit=1 note=Traceback (most recent call last):