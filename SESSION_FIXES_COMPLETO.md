# Sentinel Omega — Fixes completos de sesión (2026-08)

Paquete **íntegro** de todos los cambios de la sesión de auditoría/corrección.
Destinado a revisión por otra IA: integridad, lógica, faltantes, documentación.

## Inventario de fixes (checklist de revisión)

### 1. Datos / LOCF / zero-synthetic
- [ ] `tbl_locf_cache` en schema.py (SCHEMA_VERSION **11**)
- [ ] `repository.save_locf` / `load_locf`
- [ ] `data_pipeline`: fallback al último valor si API falla

### 2. Histórico / vivo / volcado 24h
- [ ] `volcar_telemetria_viva` (vivo → histórico + cascada)
- [ ] `tbl_schumann_vivo`, `tbl_volcado_vivo_log`

### 3. ONNX
- [ ] Modelos: alfa1, alfa2, beta1, beta2, delta, **omega_espacial_rf.onnx**
- [ ] `core/onnx_mixin.py`, `train_onnx_from_db.py` (+ juez feedback)

### 4. Juez / disciplina
- [ ] `RITMO_HORAS = 2`
- [ ] `registrar_prediccion` por **cada bot** + Padre
- [ ] `castigar` / `reforzar` al resolver

### 5. Lags dinámicos + multi-evento
- [ ] `LAG_SEED_MAX_H = 90*24`, `lag_p95_h`
- [ ] `tbl_eventos_catalogo`

### 6. Omega + Padre dual-ask
- [ ] Omega espacial + Beta context + ONNX
- [ ] dual-ask + gate asertividad

### 7. Telegram Centinela V2
- [ ] `send_alert_gated`, solo env vars

### 8. Dashboard
- [ ] Eventos, Alfas, Betas, Omega, Padre, Juez

### 9. Deploy / deps
- [ ] services/timers, ephem, onnxruntime, sklearn

## Pendiente documentado
- Correo (pausado), snap liberación, landslides, topologia_cascada.py opcional
