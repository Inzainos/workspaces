# Sentinel Omega — Fixes completos de sesión (2026-08)

Paquete **íntegro** de todos los cambios de la sesión de auditoría/corrección.
Destinado a revisión por otra IA: integridad, lógica, faltantes, documentación.

## Cómo aplicar

```bash
cd workspaces   # repo Inzainos/workspaces
git pull
tar xzf sentinel_omega_COMPLETO_sesion.tar.gz
# revisar git status / diff
git add -A
git commit -m "feat(sentinel): sesión completa — LOCF, ONNX+Omega, Juez 2h, dual-ask, Telegram, lags, dashboard"
git push origin main
```

Después:
```bash
pip install -r sentinel_omega/requirements.txt
python -m sentinel_omega.models.train_onnx_bootstrap   # si faltan .onnx
python -m sentinel_omega.launcher --once --dry-run
```

## Inventario de fixes (checklist de revisión)

### 1. Datos / LOCF / zero-synthetic
- [ ] `tbl_locf_cache` en schema.py (SCHEMA_VERSION **11**)
- [ ] `repository.save_locf` / `load_locf`
- [ ] `data_pipeline`: fallback al último valor si API falla (sin defaults sintéticos tipo FGI=50)

### 2. Histórico / vivo / volcado 24h
- [ ] `persist_live_earthquakes` / USGS live
- [ ] `volcar_telemetria_viva` en mantenimiento.py (vivo → histórico + cascada)
- [ ] `tbl_schumann_vivo`, `tbl_volcado_vivo_log`
- [ ] Dual histórico (sismico + raw) coherente

### 3. ONNX
- [ ] Modelos: alfa1, alfa2, beta1, beta2, delta, **omega_espacial_rf.onnx**
- [ ] `core/onnx_mixin.py` (`try_load_onnx` → session, inference)
- [ ] `core/onnx_engine.py` (`n_features` en ONNXBotInference)
- [ ] `config/onnx_config.py` incluye **omega**
- [ ] Agentes cableados (alfa1–delta + omega)
- [ ] `train_onnx_bootstrap.py` + `train_onnx_from_db.py` (firmas + **load_juez_feedback**)

### 4. Juez / disciplina
- [ ] `RITMO_HORAS = 2` en verificacion.py
- [ ] `ventana_h` adaptativa en launcher (2h o lag de firma, tope 90d)
- [ ] `registrar_prediccion` por **cada bot** + Padre (no solo Padre)
- [ ] `castigar` / `reforzar` al resolver (FALLO, FALSO_POSITIVO, ACIERTO)
- [ ] Reload pesos + asertividad Omega/córum post-Juez

### 5. Lags dinámicos + multi-evento
- [ ] `LAG_SEED_MAX_H = 90*24`, `_lag_offsets_dinamicos`, `lag_p95_h`
- [ ] `rebuild_eventos_catalogo` + `tbl_eventos_catalogo` (schema + runtime)
- [ ] Clases: SISMO_*, ERUPCION_*, TORMENTA_Kp*, TSUNAMI_* (proxy)
- [ ] Vector de firma sigue ~14d; **lead time** no cortado a 14d

### 6. Omega + Padre dual-ask
- [ ] `layers/geodynamic/omega/agent.py` (espacial + pregunta Beta + ONNX)
- [ ] `layer_runners` ejecuta Omega antes del Padre
- [ ] Padre: Omega fuera de familias salvo **referencia** (asertividad ≥ córum)
- [ ] `_dual_ask` metadata (quién alertó primero)
- [ ] Elevación a WATCH si Omega referencia alerta solo

### 7. Telegram (Centinela V2)
- [ ] Anti-spam `send_alert_gated` (cooldown 30 min)
- [ ] Prioridades: crítico / grieta Bz / tormenta / advertencia
- [ ] Dual-ask Omega, consenso, muro
- [ ] Credenciales **solo** env (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- [ ] orchestrator → `dispatch_cycle_alerts`

### 8. Dashboard
- [ ] Pestañas: Risk, Muro, Scanner, Topología, Sísmico, Schumann,
      **Eventos, Alfas, Betas, Omega, Padre, Juez**, Ciclos, Sistema, SNT

### 9. Deploy / ops
- [ ] `deploy/sentinel-omega-mantenimiento.service`
- [ ] flags launcher: --disciplina, --barrido, --entrenar, --backcast, --dry-run
- [ ] `requirements.txt`: ephem, onnxruntime, scikit-learn, skl2onnx

## Fuera de este paquete / pendiente documentado
- Correo alineado al gate Telegram (pausado a propósito)
- Snap de liberación + patrones por bot (`bot_name` en cimática)
- Landslide / catálogos oficiales tsunami-huracán
- `topologia_cascada.py` script ETL (si no estaba en repo base; cascada se invoca desde mantenimiento)
- Permiso GitHub write del conector Grok (403) — push manual

## Pruebas ya hechas en sesión
- Omega ONNX predict → ALERT ~0.80 con Bz=-12, Kp=7
- Padre dual-ask + elevación WATCH con Omega referencia
- Retrain omega bootstrap-only escribe `.onnx`
- Compile de módulos clave OK

## Archivos tocados (núcleo)
schema, repository, data_pipeline, backcast, entrenamiento, mantenimiento,
verificacion, layer_runners, launcher, orchestrator, juez, padre, omega/,
onnx_*, telegram, dashboard/app, models/*, requirements, deploy service.
