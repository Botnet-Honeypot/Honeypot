# pytest . --cov-report term-missing

import threading
import socket
from ipaddress import ip_address
from unittest.mock import MagicMock, create_autospec, patch

import pytest
import paramiko

from frontend.protocols.ssh._proxy_handler import ProxyHandler, try_send_data, proxy_data
from frontend.honeylogger import SSHSession
from frontend.honeylogger._console import ConsoleLogSSHSession
import frontend.protocols.ssh._proxy_handler
from frontend.target_systems import TargetSystemProvider

debug_log = frontend.protocols.ssh._proxy_handler.logger


@pytest.fixture()
def logger() -> SSHSession:
    return ConsoleLogSSHSession(ip_address("1.1.1.1"), 1, ip_address("2.2.2.2"), 2)


@pytest.fixture()
def target_system_provider(logger) -> ProxyHandler:
    return create_autospec(TargetSystemProvider)


def test_try_send_data():
    data = 5
    mocked_method = MagicMock(return_value=True)
    assert try_send_data(data, mocked_method)
    mocked_method.assert_called_once_with(data)

    mocked_method.side_effect = socket.timeout()
    assert try_send_data(data, mocked_method) == False

    mocked_method.side_effect = socket.error()
    assert try_send_data(data, mocked_method) == False


@patch.object(paramiko.SSHClient, 'connect', return_value=None)
def test_error_transport_none_connect(connect_mock, logger, target_system_provider):
    debug_log.exception = MagicMock()
    debug_log.error = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    p._open_proxy_transport("", 0, "", "", max_retries=0)

    connect_mock.assert_called_once_with("", port=0, username="", password="",
                                         allow_agent=False, look_for_keys=False)
    debug_log.error.assert_not_called()
    debug_log.exception.assert_called_once()


@patch.object(paramiko.SSHClient, 'get_transport', return_value=1)
@patch.object(paramiko.SSHClient, 'connect', return_value=None)
def test_connect(connect_mock, get_transport_mock, logger, target_system_provider):
    debug_log.exception = MagicMock()
    debug_log.error = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    result = p._open_proxy_transport("", 0, "", "", max_retries=0)

    connect_mock.assert_called_once_with("", port=0, username="", password="",
                                         allow_agent=False, look_for_keys=False)
    debug_log.error.assert_not_called()
    debug_log.exception.assert_not_called()
    assert result is not None


@patch.object(paramiko.SSHClient, 'connect', side_effect=paramiko.SSHException)
def test_ssh_exception(connect_mock, logger, target_system_provider):
    debug_log.exception = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    p._open_proxy_transport("", 0, "", "", max_retries=0)

    connect_mock.assert_called_once_with("", port=0, username="", password="",
                                         allow_agent=False, look_for_keys=False)
    debug_log.exception.assert_called_once()


@patch.object(paramiko.SSHClient, 'connect', side_effect=socket.error)
def test_socket_error(connect_mock, logger, target_system_provider):
    debug_log.exception = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    p._open_proxy_transport("", 0, "", "", max_retries=0)

    connect_mock.assert_called_once_with("", port=0, username="", password="",
                                         allow_agent=False, look_for_keys=False)
    debug_log.exception.assert_called_once()


def test_get_corresponding_backend_channel_error(logger, target_system_provider):
    p = ProxyHandler(logger, target_system_provider)

    # No such channel available
    with pytest.raises(KeyError):
        p._get_corresponding_backend_channel(1)


def test_get_corresponding_backend_channel_ok(logger, target_system_provider):
    debug_log.error = MagicMock()
    debug_log.exception = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    c = paramiko.Channel(0)
    p._backend_chan_proxies[1] = c

    assert p._get_corresponding_backend_channel(1) == c

    debug_log.exception.assert_not_called()
    debug_log.error.assert_not_called()


def test_handle_exec_keyerror(logger, target_system_provider):
    p = ProxyHandler(logger, target_system_provider)
    p._get_corresponding_backend_channel = MagicMock(side_effect=KeyError)

    assert p.handle_exec_request(paramiko.Channel(0), b"") == False


def test_handle_exec_unicodeerror(logger, target_system_provider):
    debug_log.error = MagicMock()

    p = ProxyHandler(logger, target_system_provider)
    p._get_corresponding_backend_channel = MagicMock(
        side_effect=UnicodeDecodeError("", b"", 0, 0, ""))

    assert p.handle_exec_request(paramiko.Channel(0), b"") == False
    debug_log.error.assert_called_once()


def test_handle_exec_error(logger, target_system_provider):
    debug_log.error = MagicMock()

    p = ProxyHandler(logger, target_system_provider)

    channel_mock = MagicMock()
    channel_mock.exec_command.side_effect = paramiko.SSHException

    p._get_corresponding_backend_channel = MagicMock(return_value=channel_mock)

    assert p.handle_exec_request(paramiko.Channel(0), b"") == False
    debug_log.error.assert_called_once()


def test_handle_exec_ok(logger, target_system_provider):
    with patch("threading.Thread"):
        debug_log.error = MagicMock()
        logger.log_command = MagicMock()
        p = ProxyHandler(logger, target_system_provider)

        channel_mock = MagicMock()
        channel_mock.exec_command = MagicMock()

        p._get_corresponding_backend_channel = MagicMock(return_value=channel_mock)

        data = b"hi"
        assert p.handle_exec_request(paramiko.Channel(0), data) == True
        channel_mock.exec_command.assert_called_once()
        logger.log_command.assert_called_once()


def test_shell_request_keyerror(logger, target_system_provider):
    p = ProxyHandler(logger, target_system_provider)
    p._get_corresponding_backend_channel = MagicMock(side_effect=KeyError)

    assert p.handle_shell_request(paramiko.Channel(0)) == False


def test_shell_request_sshexception(logger, target_system_provider):
    debug_log.error = MagicMock()
    p = ProxyHandler(logger, target_system_provider)
    p._get_corresponding_backend_channel = MagicMock(side_effect=paramiko.SSHException)

    assert p.handle_shell_request(paramiko.Channel(0)) == False
    debug_log.error.assert_called_once()


def test_shell_request_ok(logger, target_system_provider):
    with patch("threading.Thread"):
        debug_log.error = MagicMock()

        backend_mock = MagicMock()
        backend_mock.invoke_shell = MagicMock()
        p = ProxyHandler(logger, target_system_provider)
        p._get_corresponding_backend_channel = MagicMock(return_value=backend_mock)

        assert p.handle_shell_request(paramiko.Channel(0))
        debug_log.error.assert_not_called()
        backend_mock.invoke_shell.assert_called_once()


def test_close_connection_not_active(logger, target_system_provider):
    logger.end = MagicMock()
    p = ProxyHandler(logger, target_system_provider)
    p._connection = None
    p.close_connection()

    logger.end.assert_called_once()


def test_proxy_eof_received(logger):
    with patch("os.name", return_value="nt"):
        debug_log.error = MagicMock()
        debug_log.exception = MagicMock()

        attacker_channel = MagicMock()
        backend_channel = MagicMock()

        # Mock stuff
        attacker_channel.eof_received = True
        attacker_channel.close = MagicMock()
        backend_channel.eof_received = True
        backend_channel.close = MagicMock()

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, logger))
        handle_thread.start()

        handle_thread.join(1)

        # Both should be closed since both has sent eof
        attacker_channel.close.assert_called_once()
        backend_channel.close.assert_called_once()
        debug_log.exception.assert_not_called()
        debug_log.error.assert_not_called()


def test_open_channel_send_exit_code(logger):
    with patch("os.name", return_value="nt"):
        debug_log.error = MagicMock()
        debug_log.exception = MagicMock()

        attacker_channel = MagicMock()
        backend_channel = MagicMock()

        # Mock stuff
        attacker_channel.close = MagicMock()
        attacker_channel.eof_received = False
        attacker_channel.closed = False
        attacker_channel.send_exit_status = MagicMock()

        backend_channel.close = MagicMock()
        backend_channel.eof_received = True
        backend_channel.recv_ready = MagicMock(return_value=False)
        backend_channel.recv_stderr_ready = MagicMock(return_value=False)
        backend_channel.exit_status_ready = MagicMock(return_value=True)
        backend_channel.recv_exit_status = MagicMock(return_value=1337)

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, logger))
        handle_thread.start()

        handle_thread.join(1)

        attacker_channel.close.assert_called_once()
        backend_channel.close.assert_not_called()
        attacker_channel.send_exit_status.assert_called_once_with(1337)

        debug_log.exception.assert_not_called()
        debug_log.error.assert_not_called()


def test_proxy_to_backend(logger):
    with patch("os.name", return_value="nt"):
        debug_log.error = MagicMock()
        debug_log.exception = MagicMock()
        logger.log_ssh_channel_output = MagicMock()

        attacker_channel = MagicMock()
        backend_channel = MagicMock()
        data = b"432153425"

        # Mock stuff
        attacker_channel.close = MagicMock()
        attacker_channel.recv_ready = MagicMock(side_effect=[True, False])
        attacker_channel.recv = MagicMock(return_value=data)
        attacker_channel.eof_received = False
        attacker_channel.closed = False

        backend_channel.close = MagicMock()
        backend_channel.sendall = MagicMock()
        backend_channel.eof_received = False
        backend_channel.closed = False

        backend_channel.recv_ready = MagicMock(return_value=False)
        backend_channel.recv_stderr_ready = MagicMock(return_value=False)
        backend_channel.exit_status_ready = MagicMock(return_value=True)

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, logger))
        handle_thread.start()

        # Simulate closing the attacker channel so the thread doesn't go on forever
        attacker_channel.eof_received = True

        handle_thread.join(2)

        backend_channel.close.assert_called_once()
        backend_channel.sendall.assert_called_once_with(data)

        debug_log.exception.assert_not_called()
        debug_log.error.assert_not_called()


def test_proxy_to_attacker(logger):
    with patch("os.name", return_value="nt"):
        debug_log.error = MagicMock()
        debug_log.exception = MagicMock()
        logger.log_ssh_channel_output = MagicMock()

        backend_channel = MagicMock()
        attacker_channel = MagicMock()
        data = b"432153425"

        # Mock stuff
        attacker_channel.eof_received = False
        attacker_channel.closed = False
        attacker_channel.close = MagicMock()
        attacker_channel.sendall = MagicMock()

        backend_channel.close = MagicMock()
        backend_channel.eof_received = True
        backend_channel.closed = True

        backend_channel.recv_ready = MagicMock(
            side_effect=[True, True, False, False, False, False, False, False])
        backend_channel.recv = MagicMock(return_value=data)
        backend_channel.recv_stderr_ready = MagicMock(return_value=False)

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, logger))
        handle_thread.start()

        handle_thread.join(2)

        attacker_channel.close.assert_called_once()
        attacker_channel.sendall.assert_called_once_with(data)

        debug_log.error.assert_not_called()
        debug_log.exception.assert_not_called()
