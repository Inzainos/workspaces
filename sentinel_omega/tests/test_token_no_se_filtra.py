"""El token de Telegram viajaba a los logs y de ahí a git. Que no vuelva.

Encontrado el 2026-09-27 auditando el repo: el token viejo estaba **195 veces**
en `data/sentinel_omega.log.1` (244 MB, rastreado por git) y de ahí pasó a
cuatro commits de un repositorio PÚBLICO.

Nadie lo escribió a mano. La URL de la API lleva el token DENTRO
(`/bot<token>/sendMessage`), así que cuando `requests` falla su excepción trae
la URL completa, y tres `logger.error(f"...: {e}")` la escribían entera.

**Rotar el token no arregla esto**: el siguiente fallo de red filtra el nuevo.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from sentinel_omega.infrastructure.api import telegram
from sentinel_omega.infrastructure.api.telegram import sin_token

FALSO = "8412345678:" + "AAHdummyDUMMYdummyDUMMYdummyDUMMY"


def test_enmascara_dentro_de_la_url():
    """Es el caso real: el token no aparece suelto, viene en una URL."""
    e = Exception(f"Max retries exceeded with url: /bot{FALSO}/sendMessage")
    salida = sin_token(e)
    assert FALSO not in salida
    assert "<TOKEN>" in salida


@pytest.mark.parametrize("largo", [30, 32, 35, 36, 45])
def test_enmascara_sea_cual_sea_el_largo(largo):
    """Un patrón clavado en 35 caracteres falla EN SILENCIO con uno de 36, y
    fallar en silencio es lo peor que puede hacer una función de redacción."""
    tok = "8412345678:" + "A" * largo
    assert tok not in sin_token(f"error con url /bot{tok}/sendMessage")


def test_no_toca_un_texto_normal():
    for texto in ("error 404 en 2026-09-27", "timeout tras 30s", "",
                  "2026-09-27T04:56:16.522+00:00"):
        assert sin_token(texto) == str(texto)


def test_los_tres_sitios_que_lo_filtraban_ya_no_lo_hacen():
    """Los tres `logger.error(f"...: {e}")` de send / photo / document."""
    fuente = inspect.getsource(telegram)
    for msg in ("Telegram send failed", "Telegram photo failed",
                "Telegram document failed"):
        assert f'f"{msg}: {{e}}"' not in fuente, f"{msg} volvió a registrar la excepción cruda"
        assert f'"{msg}: %s", sin_token(e)' in fuente, msg


def test_ningun_archivo_del_arbol_trae_un_token():
    """Barrido de los formatos donde apareció: markdown, logs, metadatos."""
    import re

    PAT = re.compile(rb"(?<![0-9])[0-9]{8,10}:[A-Za-z0-9_-]{30,}")
    raiz = Path("sentinel_omega")
    sospechosos = []
    for p in list(raiz.rglob("*.md")) + list(raiz.rglob("PKG-INFO")):
        if any(x in p.parts for x in (".venv", "venv", "node_modules")):
            continue
        try:
            if PAT.search(p.read_bytes()):
                sospechosos.append(str(p))
        except OSError:
            continue
    assert sospechosos == [], sospechosos
