import datetime
import logging
import pytest
from ipaddress import ip_address
from unittest.mock import MagicMock

import paramiko
from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL, )

from frontend.protocols.ssh._proxy_handler import ProxyHandler
from frontend.honeylogger import SSHSession
from frontend.honeylogger._console import ConsoleLogSSHSession
from frontend.protocols.ssh._ssh_server import Server
import frontend.protocols.ssh._ssh_server

debug_log = logging.getLogger(frontend.protocols.ssh._ssh_server.__name__)


def time_in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


@pytest.fixture()
def logger() -> SSHSession:
    return ConsoleLogSSHSession(ip_address("1.1.1.1"), 1, ip_address("2.2.2.2"), 2)


@pytest.fixture()
def proxy_handler(logger) -> ProxyHandler:
    return ProxyHandler(logger)


@pytest.fixture()
def ssh_server(logger, proxy_handler) -> Server:
    transport_mock = MagicMock()
    transport_mock.remote_version = "ExampleVersion"
    return Server(transport_mock, logger, proxy_handler, [""], [""])


def test_update_last_activity_without_started_session(ssh_server: Server, logger: SSHSession):
    logger.begin = MagicMock()

    now = datetime.datetime.now()

    ssh_server._update_last_activity()

    logger.begin.assert_called_once()
    assert ssh_server._logging_session_started

    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)


def test_update_last_activity_exception(ssh_server: Server, logger: SSHSession):
    logger.begin = MagicMock(side_effect=Exception)

    debug_log.exception = MagicMock()
    now = datetime.datetime.now()

    ssh_server._update_last_activity()

    logger.begin.assert_called_once()
    assert ssh_server._logging_session_started == False
    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)
    debug_log.exception.assert_called_once()


def test_get_last_activity(ssh_server: Server):
    time = datetime.datetime.now()
    ssh_server._last_activity = time
    assert ssh_server.get_last_activity() == time


def test_check_username_password(ssh_server: Server):
    ssh_server._usernames = ["linus"]
    ssh_server._passwords = ["torvalds"]
    now = datetime.datetime.now()

    assert ssh_server.check_auth_password("linus", "torvalds") == AUTH_SUCCESSFUL
    assert ssh_server.check_auth_password("inus", "torvalds") == AUTH_FAILED
    assert ssh_server.check_auth_password("linus", "lol") == AUTH_FAILED
    assert ssh_server.check_auth_password("inus", "") == AUTH_FAILED
    assert ssh_server.check_auth_password("", "") == AUTH_FAILED
    assert ssh_server.check_auth_password("Linus", "") == AUTH_FAILED

    ssh_server._usernames = None

    assert ssh_server.check_auth_password("", "torvalds") == AUTH_SUCCESSFUL
    assert ssh_server.check_auth_password("TSRA%$#B$WQ", "torvalds") == AUTH_SUCCESSFUL

    ssh_server._usernames = None
    ssh_server._passwords = None

    assert ssh_server.check_auth_password("TSRA%$#B$WQ", "") == AUTH_SUCCESSFUL
    assert ssh_server.check_auth_password("", "") == AUTH_SUCCESSFUL
    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)


def test_check_auth_publickey(ssh_server: Server):
    now = datetime.datetime.now()
    key = paramiko.RSAKey(filename="./host.key")

    assert ssh_server.check_auth_publickey("", key) == AUTH_FAILED
    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)


def test_check_channel_request_and_exec_once_per_channel(ssh_server: Server):
    now = datetime.datetime.now()
    cmd = b"ls -la"
    ssh_server._channels_done = set([1, 2])
    ssh_server._proxy_handler.handle_exec_request = MagicMock(return_value=True)

    assert ssh_server.check_channel_exec_request(paramiko.Channel(1), cmd) == False
    assert ssh_server.check_channel_shell_request(paramiko.Channel(2)) == False

    channel = paramiko.Channel(3)
    assert ssh_server.check_channel_exec_request(channel, cmd) == True
    assert ssh_server.check_channel_shell_request(channel) == False

    ssh_server._proxy_handler.handle_exec_request.assert_called_once_with(channel, cmd)
    ssh_server._proxy_handler.handle_exec_request.assert_called_once()
    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)


def test_channel_pty_request(ssh_server: Server):
    now = datetime.datetime.now()
    ssh_server._session.log_pty_request = MagicMock()
    ssh_server._proxy_handler.handle_pty_request = MagicMock(return_value=True)

    channel = paramiko.Channel(3)
    term = b"screen"
    height = 432
    width = 32
    pixel_width = 432
    pixel_height = 432

    ssh_server.check_channel_pty_request(
        channel, term, width, height, pixel_width, pixel_height, b"")

    ssh_server._session.log_pty_request.assert_called_with(
        term.decode("utf-8"), width, height, pixel_width, pixel_height)
    ssh_server._proxy_handler.handle_pty_request.assert_called_once_with(
        channel, term.decode("utf-8"), width, height, pixel_width, pixel_height)
    assert time_in_range(now,  datetime.datetime.now(), ssh_server._last_activity)
