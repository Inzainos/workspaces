"""network_watchdog debe usar `systemctl --user` (Sentinel corre como units de
usuario; las de sistema estan enmascaradas) y funcionar sin XDG_RUNTIME_DIR
(cron / ssh sin sesion)."""
import inspect
import os
import re
import subprocess
from unittest import mock

from sentinel_omega.infrastructure.watchdog import network_watchdog as nw


def _fake_run(stdout=''):
    return mock.Mock(return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr=''))


def test_try_restart_sin_xdg_usa_user_y_run_user_uid(monkeypatch):
    monkeypatch.delenv('XDG_RUNTIME_DIR', raising=False)
    monkeypatch.delenv('DBUS_SESSION_BUS_ADDRESS', raising=False)
    fake = _fake_run()
    monkeypatch.setattr(nw.subprocess, 'run', fake)

    nw.try_restart(['sentinel-omega'])

    fake.assert_called_once()
    args, kwargs = fake.call_args
    assert args[0] == ['systemctl', '--user', 'restart', 'sentinel-omega']
    env = kwargs['env']
    uid = os.getuid()
    assert env['XDG_RUNTIME_DIR'] == f'/run/user/{uid}'
    assert env['DBUS_SESSION_BUS_ADDRESS'] == f'unix:path=/run/user/{uid}/bus'
    # no muta el entorno global
    assert 'XDG_RUNTIME_DIR' not in os.environ
    assert 'DBUS_SESSION_BUS_ADDRESS' not in os.environ


def test_service_active_usa_user(monkeypatch):
    monkeypatch.delenv('XDG_RUNTIME_DIR', raising=False)
    fake = _fake_run(stdout='active\n')
    monkeypatch.setattr(nw.subprocess, 'run', fake)

    assert nw.service_active('sentinel-omega') is True
    args, kwargs = fake.call_args
    assert args[0][:2] == ['systemctl', '--user']
    assert args[0][2:] == ['is-active', 'sentinel-omega']
    assert kwargs['env']['XDG_RUNTIME_DIR'] == f'/run/user/{os.getuid()}'


def test_respeta_xdg_existente(monkeypatch):
    monkeypatch.setenv('XDG_RUNTIME_DIR', '/tmp/xdg-prueba')
    monkeypatch.setenv('DBUS_SESSION_BUS_ADDRESS', 'unix:path=/tmp/xdg-prueba/bus')
    fake = _fake_run()
    monkeypatch.setattr(nw.subprocess, 'run', fake)

    nw.try_restart(['sentinel-omega'])
    env = fake.call_args.kwargs['env']
    assert env['XDG_RUNTIME_DIR'] == '/tmp/xdg-prueba'
    assert env['DBUS_SESSION_BUS_ADDRESS'] == 'unix:path=/tmp/xdg-prueba/bus'


def test_ninguna_llamada_systemctl_sin_user():
    src = inspect.getsource(nw)
    # ninguna lista literal que empiece con 'systemctl' seguido de algo != '--user'
    malas = re.findall(r"\[\s*['\"]systemctl['\"]\s*,\s*['\"](?!--user['\"])[^'\"]*['\"]", src)
    assert malas == []
    assert nw.SYSTEMCTL == ['systemctl', '--user']
