import socket
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

import paramiko
from frontend.protocols.ssh.connection_manager import ConnectionManager
from frontend.protocols.ssh._transport_manager import TransportManager


@pytest.fixture()
def connection_manager() -> ConnectionManager:
    key = paramiko.RSAKey(filename="./host.key")
    return ConnectionManager(key, [""], [""], port=2222, socket_timeout=0.2)


def test_shutdown(connection_manager: ConnectionManager):
    with patch('threading.Thread'):
        connection_manager.start()

        assert connection_manager.is_alive()
        connection_manager.stop()
        connection_manager.join(1)
        assert connection_manager.is_alive() == False


# def test_session_started(connection_manager: ConnectionManager):
#     with patch('threading.Thread'):
#         # with patch.object(socket.socket, 'accept', side_effect=[None, socket.timeout]):
#         with patch("socket.socket") as socket_mock:
#             mock = MagicMock()
#             mock.listen = MagicMock(return_value=None)
#             mock.accept = MagicMock(return_value=(None, None))

#             socket_mock.return_value = mock
#             with patch.object(paramiko.Transport, 'start_server', return_value=None):
#                 with patch.object(TransportManager, 'add_transport', return_value=None) as mocked:
#                     connection_manager.start()
#                     assert connection_manager.is_alive()

#                     time.sleep(0.01)
#                     connection_manager.stop()
#                     connection_manager.join(1)
#                     assert connection_manager.is_alive() == False
#                     mocked.assert_called_once()
