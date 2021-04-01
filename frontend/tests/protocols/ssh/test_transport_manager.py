import datetime
import time
from unittest.mock import MagicMock

import pytest

from frontend.protocols.ssh.connection_manager import ConnectionManager
from frontend.protocols.ssh._transport_manager import TransportManager, TransportPair


@pytest.fixture()
def transport_manager() -> TransportManager:
    return TransportManager()


def test_shutdown(transport_manager: TransportManager):
    assert transport_manager._handle_thread.is_alive()
    transport_manager.stop()
    transport_manager._handle_thread.join(1)
    assert transport_manager._handle_thread.is_alive() == False


def test_shutdown_transports(transport_manager: TransportManager):
    attacker_transport_mock = MagicMock()
    attacker_transport_mock.is_active = MagicMock(return_value=True)
    attacker_transport_mock.close = MagicMock()

    proxyhandler_mock = MagicMock()
    proxyhandler_mock.close_connection = MagicMock()

    server_mock = MagicMock()
    server_mock.get_last_activity = MagicMock(return_value=datetime.datetime.now())

    transport_manager.add_transport(TransportPair(
        attacker_transport_mock, proxyhandler_mock, server_mock))
    transport_manager.stop()
    transport_manager._handle_thread.join(1)

    attacker_transport_mock.close.assert_called()
    proxyhandler_mock.close_connection.assert_called()


def test_attacker_transport_not_alive(transport_manager: TransportManager):
    attacker_transport_mock = MagicMock()
    attacker_transport_mock.is_active = MagicMock(return_value=False)
    attacker_transport_mock.close = MagicMock()

    proxyhandler_mock = MagicMock()
    proxyhandler_mock.close_connection = MagicMock()

    server_mock = MagicMock()
    server_mock.get_last_activity = MagicMock(return_value=datetime.datetime.now())

    transport_manager.add_transport(TransportPair(
        attacker_transport_mock, proxyhandler_mock, server_mock))

    time.sleep(0.6)
    proxyhandler_mock.close_connection.assert_called()
    transport_manager.stop()
    transport_manager._handle_thread.join(1)


def test_attacker_transport_inactive(transport_manager: TransportManager):
    attacker_transport_mock = MagicMock()
    attacker_transport_mock.is_active = MagicMock(return_value=True)
    attacker_transport_mock.close = MagicMock()

    proxyhandler_mock = MagicMock()
    proxyhandler_mock.close_connection = MagicMock()

    server_mock = MagicMock()
    server_mock.get_last_activity = MagicMock(return_value=datetime.datetime(1900, 1, 1))

    transport_manager.add_transport(TransportPair(
        attacker_transport_mock, proxyhandler_mock, server_mock))

    time.sleep(0.6)
    proxyhandler_mock.close_connection.assert_called()
    attacker_transport_mock.close.assert_called()
    transport_manager.stop()
    transport_manager._handle_thread.join(1)


def test_attacker_transport_inactive_no_timeout(transport_manager: TransportManager):
    attacker_transport_mock = MagicMock()
    attacker_transport_mock.is_active = MagicMock(return_value=True)
    attacker_transport_mock.close = MagicMock()

    proxyhandler_mock = MagicMock()
    proxyhandler_mock.close_connection = MagicMock()

    server_mock = MagicMock()
    server_mock.get_last_activity = MagicMock(return_value=datetime.datetime.now())

    transport_manager.add_transport(TransportPair(
        attacker_transport_mock, proxyhandler_mock, server_mock))

    time.sleep(0.6)
    proxyhandler_mock.close_connection.assert_not_called()
    attacker_transport_mock.close.assert_not_called()
    transport_manager.stop()
    transport_manager._handle_thread.join(1)
