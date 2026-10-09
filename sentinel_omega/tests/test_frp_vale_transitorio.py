"""Un vale con la hora mal no es una credencial mala.

Medido el 2026-10-08 en el ciclo vivo: la BÚSQUEDA de Copernicus funciona y
encuentra el producto, y la descarga falla con `The token is not yet valid
(iat)`. eodag lo envuelve en `AuthenticationError`, que `_es_fatal` daba por
fatal, así que un desfase de segundos entre quien emite el vale y quien lo
valida **mataba la fuente FRP entera en cada ciclo** --- y en el log se leía
«fallo de autenticación», que manda a revisar una contraseña que está bien.

Y la causa **sí es el reloj**, medida de punta a punta: el texto sale de PyJWT
(`jwt/api_jwt.py:481`), o sea validación LOCAL; el `iat` del vale nace +4,9 s en
nuestro futuro y este reloj va ~5 s por detrás de Copernicus; y una petición
directa con el mismo vale llega hasta devolver 416 por la cabecera `Range`, así
que el servidor lo acepta. PyJWT compara `iat` con el reloj local sin margen.

Aquí no se arregla el reloj: se evita el daño colateral. Y NO se reintenta ---
probado con 3 s y 10 s, no recupera, y pedir vales seguidos hizo que Copernicus
devolviera 403 en el endpoint de tokens.
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


def test_un_vale_rechazado_por_la_hora_no_corta_el_resto_del_ciclo(
        monkeypatch, tmp_path):
    """Antes un producto con el vale rechazado mataba la fuente entera."""
    vistos = []

    def producto_local(dag, prod):
        vistos.append(str(prod.properties.get("id")))
        raise AuthenticationError("The token is not yet valid (iat)")

    monkeypatch.setattr(esa_frp, "_producto_local", producto_local)
    monkeypatch.setattr(esa_frp, "_bbox_de",
                        lambda zonas: [("z1", (0, 0, 1, 1)), ("z2", (2, 2, 3, 3))])
    monkeypatch.setattr(esa_frp, "_dag", lambda: _DagFalso())
    monkeypatch.setattr(esa_frp, "_podar_cache", lambda dias: None)
    monkeypatch.setattr(esa_frp, "CACHE_DIR", tmp_path / "cache")

    # `None` es «no lo sé»; un 0 diría «el satélite miró y no había nada».
    assert esa_frp.medir_frp(["z1", "z2"]) is None
    assert len(vistos) == 2, "las DOS zonas se intentan; antes se cortaba en la 1.ª"

    # Y el envoltorio que usa el ciclo tampoco inventa un cero. (Cuenta aparte:
    # esta llamada vuelve a recorrer las zonas.)
    assert esa_frp.contar_anomalias_termicas(["z1"]) is None


def test_no_se_pide_un_vale_de_mas_reintentando(monkeypatch, tmp_path):
    """Pedir vales seguidos devolvió 403 de Copernicus: un reintento empeora."""
    intentos = {"n": 0}

    def producto_local(dag, prod):
        intentos["n"] += 1
        raise AuthenticationError("The token is not yet valid (iat)")

    dormido = []
    monkeypatch.setattr(esa_frp, "_producto_local", producto_local)
    monkeypatch.setattr(esa_frp, "_bbox_de", lambda zonas: [("z", (0, 0, 1, 1))])
    monkeypatch.setattr(esa_frp, "_dag", lambda: _DagFalso())
    monkeypatch.setattr(esa_frp, "_podar_cache", lambda dias: None)
    monkeypatch.setattr(esa_frp, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(esa_frp.time, "sleep", lambda s: dormido.append(s))

    esa_frp.medir_frp(["z"])

    assert intentos["n"] == 1, "un solo intento por producto"
    assert dormido == [], "y sin esperas que no sirven"


def test_el_403_del_endpoint_de_vales_si_es_fatal():
    """Ese sí hay que respetarlo: seguir pidiendo lo empeora."""
    assert esa_frp._es_fatal(
        AuthenticationError("403 Client Error: Forbidden for url: …/token")) is True


class _Prod:
    properties = {"id": "S3B_SL_2_FRP_prueba_NR_003"}


class _DagFalso:
    def search(self, **kw):
        return [_Prod()]
