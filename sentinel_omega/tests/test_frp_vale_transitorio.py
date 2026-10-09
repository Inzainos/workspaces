"""Un vale con la hora mal no es una credencial mala.

Medido el 2026-10-08 en el ciclo vivo: la BÚSQUEDA de Copernicus funciona y
encuentra el producto, y la descarga falla con `The token is not yet valid
(iat)`. eodag lo envuelve en `AuthenticationError`, que `_es_fatal` daba por
fatal, así que un desfase de segundos entre quien emite el vale y quien lo
valida **mataba la fuente FRP entera en cada ciclo** --- y en el log se leía
«fallo de autenticación», que manda a revisar una contraseña que está bien.

El reloj de esta máquina no es la causa: va 6 s por detrás de los servidores,
que es el lado seguro.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sentinel_omega.infrastructure.api import esa_frp  # noqa: E402


class AuthenticationError(Exception):
    """El nombre es lo que mira `_es_fatal`, como hace eodag."""


@pytest.mark.parametrize("texto", [
    "The token is not yet valid (iat)",
    "token expired",
])
def test_el_vale_con_la_hora_mal_no_es_fatal(texto):
    e = AuthenticationError(texto)
    assert esa_frp._es_transitorio(e) is True
    assert esa_frp._es_fatal(e) is False, (
        "si es fatal, se cortan las descargas del ciclo entero")


@pytest.mark.parametrize("texto", [
    "invalid_grant",
    "Invalid user credentials",
    "HTTP 401 Unauthorized",
    "403 Forbidden",
])
def test_una_credencial_mala_sigue_siendo_fatal(texto):
    """Reintentar una contraseña mala solo satura a Copernicus."""
    assert esa_frp._es_fatal(AuthenticationError(texto)) is True


def test_un_error_cualquiera_de_autenticacion_sigue_siendo_fatal():
    assert esa_frp._es_fatal(AuthenticationError("no se pudo autenticar")) is True


def test_se_reintenta_una_vez_y_el_producto_entra(monkeypatch, tmp_path):
    """El caso real: falla con `iat`, se espera, y a la segunda baja."""
    intentos = {"n": 0}
    esperas = []

    def producto_local(dag, prod):
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise AuthenticationError("The token is not yet valid (iat)")
        return tmp_path / "producto"

    monkeypatch.setattr(esa_frp, "_producto_local", producto_local)
    monkeypatch.setattr(esa_frp, "leer_frp", lambda ruta, bbox: 6)
    monkeypatch.setattr(esa_frp, "leer_detecciones",
                        lambda ruta, bbox, zona, pid: [{"x": 1}] * 34)
    monkeypatch.setattr(esa_frp, "_bbox_de", lambda zonas: [("z", (0, 0, 1, 1))])
    monkeypatch.setattr(esa_frp, "_dag", lambda: _DagFalso())
    monkeypatch.setattr(esa_frp, "_podar_cache", lambda dias: None)
    monkeypatch.setattr(esa_frp, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(esa_frp.time, "sleep", lambda s: esperas.append(s))

    m = esa_frp.medir_frp(["z"])

    assert intentos["n"] == 2, "tiene que reintentar exactamente una vez"
    assert esperas == [esa_frp.ESPERA_REINTENTO_VALE_S]
    assert m is not None, "la anomalía térmica ya no queda AUSENTE por esto"
    assert m["conteo"] == 6 and len(m["detecciones"]) == 34


def test_si_el_reintento_tambien_falla_se_registra_y_no_se_inventa_un_cero(
        monkeypatch, tmp_path):
    def siempre_falla(dag, prod):
        raise AuthenticationError("The token is not yet valid (iat)")

    monkeypatch.setattr(esa_frp, "_producto_local", siempre_falla)
    monkeypatch.setattr(esa_frp, "_bbox_de", lambda zonas: [("z", (0, 0, 1, 1))])
    monkeypatch.setattr(esa_frp, "_dag", lambda: _DagFalso())
    monkeypatch.setattr(esa_frp, "_podar_cache", lambda dias: None)
    monkeypatch.setattr(esa_frp, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(esa_frp.time, "sleep", lambda s: None)

    # `None` es «no lo sé»; un 0 diría «el satélite miró y no había nada».
    assert esa_frp.medir_frp(["z"]) is None
    assert esa_frp.contar_anomalias_termicas(["z"]) is None


class _Prod:
    properties = {"id": "S3B_SL_2_FRP_prueba_NR_003"}


class _DagFalso:
    def search(self, **kw):
        return [_Prod()]
