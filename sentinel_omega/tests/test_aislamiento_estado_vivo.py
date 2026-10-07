"""La suite no debe escribir el estado vivo del sistema.

El 2026-10-07, al persistir la marca del digesto para que `TG_DIGEST_MINUTES`
dejara de ser un mando muerto, correr `pytest` empezó a reescribir
`sentinel_omega/data/estado_digesto.json`. Comprobado moviendo el archivo a un
lado y volviendo a correr la suite: reapareció con el sello de la corrida.

Ningún mensaje real salió --- el transporte estaba sustituido --- pero el
estado sí se tocaba, y eso bastaba para dejar al operador **una hora sin
reporte horario**. Un arreglo contra un mando muerto convertido en un silencio
nuevo, que en este sistema es el fallo que menos se ve.

Lo cierra `tests/conftest.py`. Esta prueba es la que avisa si alguien lo borra:
el instrumento de verificación también hay que verificarlo.
"""
from __future__ import annotations

import os
from pathlib import Path

from sentinel_omega.infrastructure.messaging.consenso_vigilante import (
    DIGEST_STATE_FILE,
    ConsensoVigilante,
)


def test_la_cadencia_del_digesto_apunta_fuera_del_repo():
    ruta = os.environ.get("TG_DIGEST_STATE")
    assert ruta, (
        "TG_DIGEST_STATE no está puesto: sin él un test con dry_run=False "
        "escribe la marca de PRODUCCIÓN y silencia el reporte horario una "
        "hora. Lo pone el fixture de sesión de tests/conftest.py")
    partes = Path(ruta).resolve().parts
    assert "data" not in partes or "sentinel_omega" not in partes, (
        f"la marca del digesto apunta dentro del repo: {ruta}")


def test_una_instancia_de_produccion_no_escribe_en_data():
    """Construida como en producción (`dry_run=False`), su estado sigue cayendo
    en el temporal de la sesión, no en `sentinel_omega/data/`."""
    v = ConsensoVigilante(dry_run=False, digest_minutes_override=60)
    ruta = v._digest_state_path()
    assert ruta is not None
    assert ruta.name == DIGEST_STATE_FILE
    assert "data" not in Path(ruta).resolve().parts[:-1] or (
        "sentinel_omega" not in Path(ruta).resolve().parts), ruta


def test_el_guardarrail_de_dry_run_sigue_en_su_sitio(monkeypatch):
    """Segunda línea de defensa, independiente del conftest: sin override, una
    instancia dry-run no tiene archivo de estado que tocar."""
    monkeypatch.delenv("TG_DIGEST_STATE", raising=False)
    assert ConsensoVigilante(dry_run=True)._digest_state_path() is None
