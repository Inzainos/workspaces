"""El cartel del arranque tiene que decir lo que va a pasar.

Medido el 2026-10-08: el banner imprimía `Telegram: OFF (dry run)` y ese mismo
proceso registró `CONSENSO digest horario (sent, buffered=56, dry_run=False)` y
17 intentos de envío reales. Leía `config.telegram.enabled`, que viene de
`sentinel.yaml` con `false` y cuyo ÚNICO lector era ese print; la decisión real
la toman `SENTINEL_DRY_RUN` y la presencia de credenciales.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sentinel_omega import launcher  # noqa: E402


class _Tg:
    def __init__(self, token="t", chat="c"):
        self.bot_token = token
        self.chat_id = chat
        # Lo que traía el yaml: `false`. No debe decidir nada.
        self.enabled = False

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)


class _Config:
    def __init__(self, tg):
        self.telegram = tg


def test_con_credenciales_y_sin_dry_run_dice_ON(monkeypatch):
    monkeypatch.delenv("SENTINEL_DRY_RUN", raising=False)

    estado = launcher._estado_telegram(_Config(_Tg()))

    assert estado == "ON", (
        "el yaml dice enabled:false y aun así se envía: el cartel debe decir ON")


@pytest.mark.parametrize("valor", ["1", "true", "YES"])
def test_el_dry_run_de_verdad_se_ve(monkeypatch, valor):
    monkeypatch.setenv("SENTINEL_DRY_RUN", valor)

    estado = launcher._estado_telegram(_Config(_Tg()))

    assert "OFF" in estado and "SENTINEL_DRY_RUN" in estado


def test_sin_credenciales_dice_por_que(monkeypatch):
    """No es lo mismo no tener token que estar en dry-run."""
    monkeypatch.delenv("SENTINEL_DRY_RUN", raising=False)

    estado = launcher._estado_telegram(_Config(_Tg(token="", chat="")))

    assert "OFF" in estado and "TELEGRAM_BOT_TOKEN" in estado
    assert "DRY_RUN" not in estado


def test_el_yaml_sigue_trayendo_la_bandera_decorativa():
    """Si algún día alguien la cablea, que este test lo haga visible."""
    import yaml

    ruta = Path(launcher.__file__).resolve().parent / "config" / "sentinel.yaml"
    cfg = yaml.safe_load(ruta.read_text(encoding="utf-8"))

    assert cfg["telegram"]["enabled"] is False
    # …y el estado NO depende de ella.
    assert launcher._estado_telegram(_Config(_Tg())) == "ON"
