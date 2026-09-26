# Copias de seguridad — cómo hacerlas bien

La base está en **modo WAL**: `cp SENTINEL_OMEGA_PRO.db destino.db` **NO copia
todo**. Lo que aún no se ha volcado vive en `...db-wal`, que el 2026-09-25
llegó a pesar **1 GB, más que la base**. Una copia hecha así puede no tener ni
las vistas (`viva_real` faltaba) ni los datos recientes.

Hacerla así, que además tarda segundos:

```python
import sqlite3
src = sqlite3.connect("file:sentinel_omega/data/SENTINEL_OMEGA_PRO.db?mode=ro", uri=True)
dst = sqlite3.connect("scratchpad/backup_AAAAMMDD_HHMM_COMPLETO.db")
src.backup(dst); dst.close(); src.close()
```

`src.backup()` incluye el WAL. Comprobar después que la copia tiene la vista:

```sql
SELECT 1 FROM sqlite_master WHERE name = 'viva_real';
```

Los archivos `INCOMPLETO_sin_wal_*.db` se hicieron con `cp` el 25-sep antes de
saber esto: **no sirven para restaurar**. Se conservan solo como rastro.
