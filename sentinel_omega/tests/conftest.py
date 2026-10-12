"""Aislamiento de la suite respecto del estado VIVO del sistema.

Por qué existe este archivo (2026-10-07)
----------------------------------------
Al persistir la marca del digesto para que `TG_DIGEST_MINUTES` dejara de ser un
mando muerto, apareció el efecto secundario: **la suite escribía la marca de
producción**. Medido --- se movió `sentinel_omega/data/estado_digesto.json` a un
lado, se corrió `pytest sentinel_omega/tests/ -q` y el archivo reapareció con
el sello de la hora de la corrida.

No se mandó ningún mensaje real: algún test deja `send_alert_gated` sustituido
pero construye el vigilante con `dry_run=False`, así que `_send` devolvía True
sin tocar la red. El daño no era el envío, era el ESTADO: una corrida de tests
podía dejar al operador **una hora sin reporte horario**, y el arreglo de un
mando muerto se habría convertido en un silencio nuevo --- la peor forma de
fallar de este sistema, porque no se ve.

El guardarraíl de `dry_run` que lleva `_digest_state_path` no basta, y no puede
bastar: un test tiene derecho a usar `dry_run=False` con el transporte
sustituido. Quien tiene que aislarse es el instrumento, no el sistema medido.
La alternativa --- que el código de producción mire `PYTEST_CURRENT_TEST` ---
se descartó: el código no debe cambiar de comportamiento según quién lo corre.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _estado_vivo_fuera_de_la_suite(tmp_path_factory):
    """Apunta el estado de cadencia del digesto a un directorio temporal.

    Es `autouse` y de sesión a propósito: un test nuevo no debería tener que
    acordarse de esto para no silenciar las alertas del operador.
    """
    directorio = tmp_path_factory.mktemp("estado_vivo")
    previo = os.environ.get("TG_DIGEST_STATE")
    os.environ["TG_DIGEST_STATE"] = str(directorio / "estado_digesto.json")
    # Lo mismo para el modo tormenta (2026-10-12): `_tormenta_activa` lee la
    # DB que `SENTINEL_DB` apunte. Sin esto, una corrida de la suite DURANTE
    # una tormenta real bajaría la cadencia de los tests a 15 min y
    # `test_un_proceso_nuevo_NO_repite_el_digesto_dentro_de_la_ventana`
    # fallaría por el estado del mundo, no por el código. Un path que no
    # existe => sin dato => sin modo tormenta (regla 7): la suite mide la
    # cadencia de calma salvo que el test la inyecte a propósito.
    previo_db = os.environ.get("SENTINEL_DB")
    os.environ["SENTINEL_DB"] = str(directorio / "no_existe.db")
    try:
        yield
    finally:
        if previo is None:
            os.environ.pop("TG_DIGEST_STATE", None)
        else:
            os.environ["TG_DIGEST_STATE"] = previo
        if previo_db is None:
            os.environ.pop("SENTINEL_DB", None)
        else:
            os.environ["SENTINEL_DB"] = previo_db
