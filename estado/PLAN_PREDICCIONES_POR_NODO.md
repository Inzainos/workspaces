# Plan de Implementación: Predicciones por Nodo (Nodal Predictions)

**Fecha:** 2026-07-20 · **Estado:** En Ejecución · **Rama:** `claude/rejected-requests-branches-36m5lt`

**Objetivo:** Transformar alertas globales ("WATCH en la Tierra") a predicciones específicas por nodo ("WATCH en nodos 14, 21, 57") para mejorar ganancia Molchan de 0.44× a 1.6–2.0×.

---

## ✅ IMPLEMENTADO (Commit cdaa487)

### 1. Core Infrastructure (sentinel_omega/core/nodal/)

#### node_aggregation.py
- **Función:** `aggregate_nodes_from_signals()`
  - Extrae nodos únicos de todas las AgentSignals
  - Maneja int, list, y tipos convertibles
  - Retorna lista ordenada de node_ids

- **Función:** `nodes_from_firma_matches()`
  - Extrae nodos de resultado de signature_engine.match_estado_actual()
  - Cada match contiene "id_nodo" — la ubicación del nodo donde la firma se correlaciona

- **Función:** `mark_alert_with_nodes()`
  - Enriquece una AgentSignal con lista de nodos
  - Mantiene metadata original de la señal

#### nodal_validation.py
- **Función:** `validate_prediction_per_node()`
  - Valida predicción SOLO contra eventos sísmicos en nodos especificados
  - Reemplaza tasa base global (98%) con tasa base local (15–25%)
  - Retorna ACIERTO/FALLO por zona, no global

- **Función:** `validate_prediction_global()`
  - Preserva modo de validación global para línea base Molchan

- **Helpers:** `_get_node_coordinates()`, `_query_eventos_por_nodos()`, `_haversine_distance()`
  - Busca eventos sísmicos en radio especificado de nodos (5°)
  - Usa cálculo Haversine para distancias geográficas

### 2. Padre Agent Enhancement

**Archivo:** `sentinel_omega/layers/geodynamic/padre/agent.py`

- **Nuevo método:** `_aggregate_nodos(validated)`
  - Itera sobre todos los AgentSignals validados
  - Extrae "nodos" de signal.data si está presente
  - Retorna sorted list de nodos únicos

- **Modificación:** `evaluate_consensus()`
  - Llama `_aggregate_nodos()` DESPUÉS de validación de pesos
  - Incluye "nodos" en metadata de CADA ConsensusResult
  - Los nodos fluyen hacia Juez.registrar_prediccion() en launcher.py

---

## 📊 DATA AUDIT (Bootstrap en Ejecución)

### Bootstrap Status
- **Backcast:** ✅ COMPLETE (30 años de datos: 1994–2025)
- **Fase 1 (Reconocimiento):** 🔄 EN CURSO
  - Progreso: ~3000/178584 eventos procesados
  - Firmas extraídas: 207
  - Recurrencias: 11,793
  - ETA: ~45 minutos más

### Audit Checklist (A Ejecutar Post-Bootstrap)

#### Database Population
```sql
-- 1. Nodes
SELECT COUNT(*) FROM TBL_NODOS_TOPOLOGIA WHERE activo=1;
-- Esperado: 50 nodos reales (de los 125 totales)

-- 2. Firmas Entrenadas
SELECT COUNT(*) FROM TBL_FIRMAS WHERE estado='consolidada';
-- Esperado: >100 consolidadas (5+ recurrencias)

-- 3. Audit Table
SELECT COUNT(*) FROM TBL_JUEZ_AUDITORIA;
-- Esperado: >1000 filas tras entrenamiento

-- 4. Seismic Data
SELECT COUNT(*) FROM TBL_HISTORICO_SISMICO WHERE magnitude >= 4.5;
-- Esperado: >3000 eventos M4.5+
```

#### Key Metrics
- **Datos en TBL_NODOS_TOPOLOGIA:** 125 nodos (50 real, 50 ghost, 25 geobatteries)
- **Datos en TBL_HISTORICO_SISMICO:** ~178K eventos M3.3+ (piso del backcast)
- **Firmas consolidadas:** >150 firmas por nodo (si hay cobertura)
- **Cobertura geográfica:** ≥80% de nodos con ≥5 firmas cada uno

---

## 🔄 TAREAS RESTANTES

### Fase 2: Agente → Nodo Linkage

**Prioridad:** ALTA · **Complejidad:** MEDIA

Los bots (alfa1, beta1, delta, etc.) deben marcar nodos cuando generen alertas basadas en firma matching.

```python
# Hoy (INCOMPLETO):
bot_signal = self.emit_signal(
    SignalType.ALERT, 0.85,
    data={"bz_mean": -12.5},  # ← Sin nodos
    reasoning="Bz umbral"
)

# Necesario:
matches = memoria.match_estado_actual(features)  # match_estado_actual retorna id_nodo
nodos = [m["id_nodo"] for m in matches[:3]]       # Extraer nodos de matches

bot_signal = self.emit_signal(
    SignalType.ALERT, 0.85,
    data={
        "bz_mean": -12.5,
        "nodos": nodos,               # ← AGREGADO
        "firma_matches": matches[:3]  # Opcional: context completo
    },
    reasoning=f"Bz umbral en nodos {nodos}"
)
```

**Archivos a Modificar:**
- `sentinel_omega/layers/geodynamic/alfa1/agent.py`
- `sentinel_omega/layers/geodynamic/beta1/agent.py`
- `sentinel_omega/layers/geodynamic/alfa2/agent.py`
- `sentinel_omega/layers/geodynamic/delta/agent.py`
- `sentinel_omega/layers/geodynamic/beta2/agent.py` (si aplica)

### Fase 3: Juez → Validación Nodal

**Prioridad:** MEDIA · **Complejidad:** MEDIA

El Juez ya recibe "nodos" en detalles (launcher.py:~750). Conectar con nodal_validation.py:

```python
# Hoy (parcial):
juez.registrar_prediccion(
    bot_name="padre",
    prediccion=geo.final_signal.value,
    detalles={
        "firma_matches": matches[:5],
        "nodos": nodos_pred,  # ← YA PRESENTE EN LAUNCHER
    },
)

# Necesario en juez.py registrar_prediccion():
from sentinel_omega.core.nodal.nodal_validation import validate_prediction_per_node

if detalles.get("nodos"):
    validacion = validate_prediction_per_node(
        conn,
        nodos_prediccion=[n["id"] for n in detalles["nodos"]],
        ts_evento_inicio=ts_inicio,
        ts_evento_fin=ts_fin,
    )
    veredicto = validacion["validacion"]  # ACIERTO | FALLO
```

**Archivo a Modificar:**
- `sentinel_omega/core/juez/juez.py`

### Fase 4: Backcast Re-Run (Opcional pero Recomendado)

**Prioridad:** BAJA · **Complejidad:** ALTA

Una vez entrenadas las firmas con nodos, re-ejecutar backcast (1994–2025) con validación nodal:

```bash
python sentinel_omega/launcher.py --backcast --entrenar --disciplina --once
```

Esto:
1. Re-entrena firmas con Padre aware de nodos
2. Disciplina pondera bots con tasa nodal (no global)
3. Molchan ganancia recalculada contra tasa base local (~15%)

---

## 🎯 Validación Post-Implementación

### Tests a Ejecutar
```bash
# 1. Unit tests (nodal module)
python -m pytest sentinel_omega/tests/test_nodal*.py -v

# 2. Integration: launcher + Padre + Juez
python sentinel_omega/launcher.py --once

# 3. Reporte de ganancia Molchan
python deploy/reporte_ejecutivo.py
# Esperar: ganancia > 0.6× en sección Molchan
```

### Checklist de Éxito
- [ ] ConsensusResult incluye "nodos" en metadata
- [ ] Juez registra predicción con nodos_prediccion != []
- [ ] Validación nodal ejecuta sin erro (SQLite queries exitosos)
- [ ] Molchan ganancia > 0.5× (antes de re-training)
- [ ] Molchan ganancia > 1.2× (después de re-training nodal)
- [ ] Reportes muestran nodos en "Firmas predichas por zona"

---

## 📈 Timeline Estimado

| Fase | Tarea | Tiempo | Inicio | Fin |
|------|-------|--------|--------|-----|
| 0 | Bootstrap + Audit | 2h | 2026-07-20 01:00 | **03:00** |
| 1 | Node Infrastructure | ✅ DONE | — | 2026-07-20 01:05 |
| 2 | Agent Linkage | 2h | **03:00** | **05:00** |
| 3 | Juez Integration | 1h | 05:00 | **06:00** |
| 4 | Testing + Debugging | 1.5h | 06:00 | **07:30** |
| 5 | Backcast Re-Training | 2h | 07:30 | **09:30** |
| 6 | Final Validation | 0.5h | 09:30 | **10:00** |

**Total:** ~10–12 horas de desarrollo + 2–3 horas de backcast = **14–15 horas desde ahora**

---

## 🔑 Decisiones Arquitectónicas

### 1. Nodos NO en dataclass AgentSignal
- **Razón:** Evitar cambios masivos en toda la codebase
- **Solución:** Usar signal.data["nodos"] (ya esperado por launcher.py)
- **Ventaja:** Backwards compatible; los agentes sin nodos siguen funcionando

### 2. Validación Nodal Apenas en Juez, No en Padre
- **Razón:** Padre decide CONSENSUS (cross-family validation)
- **Juez** valida ACCURACY (real vs predicted)
- **Ventaja:** Padre agnóstico a geografía; Juez audita por zona

### 3. Haversine Distancia, No Voronoi
- **Razón:** Simplidad; 5° ≈ 500km en el ecuador
- **Alternativa:** Clip Voronoi de cada nodo (más preciso, complejidad +40%)
- **Decisión:** Haversine es suficiente; Voronoi es futuro

---

## 🚀 Próximos Pasos

1. **Ahora:** Esperar bootstrap → correr audit
2. **Si audit OK:** Comenzar Fase 2 (agentes)
3. **Si audit FAIL:** Diagnosticar y re-ejecutar bootstrap parcial

**Usuario:** `inzainos/workspaces` · **Branch:** `claude/rejected-requests-branches-36m5lt`
