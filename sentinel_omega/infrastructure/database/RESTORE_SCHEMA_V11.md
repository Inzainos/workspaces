# Restore Schema v11

If `schema_parts/*.b64` are incomplete (placeholder or truncated), restore the full schema from the session package:

```bash
# From repo root
tar xzf path/to/sentinel_omega_COMPLETO_sesion.tar.gz \
  sentinel_omega/infrastructure/database/schema.py

# Or copy the expanded schema directly:
cp schema_v11_full.py sentinel_omega/infrastructure/database/schema.py
```

Then remove the self-expanding loader and use the plain full schema.py (35KB, SCHEMA_VERSION=11).

Alternatively keep the loader and replace all four parts:

```bash
cp schema_parts_v11/*.b64 sentinel_omega/infrastructure/database/schema_parts/
```

Verify:

```python
from sentinel_omega.infrastructure.database.schema import SCHEMA_VERSION, SCHEMA_SQL
assert SCHEMA_VERSION == 11
assert "tbl_locf_cache" in SCHEMA_SQL
assert "tbl_eventos_catalogo" in SCHEMA_SQL
print("OK")
```
