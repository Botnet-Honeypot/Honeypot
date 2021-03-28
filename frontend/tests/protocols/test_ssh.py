# pytest . --cov-report term-missing
from typing import List
from unittest.mock import MagicMock, patch
import time
import pytest

import paramiko
from paramiko import SSHClient
import pytest

import frontend.protocols.ssh as ssh

import frontend.protocols.ssh as ssh


# key = paramiko.RSAKey(filename="./host.key")
# server = "127.0.0.1"
# port = 2222
# server_start_delay = 0.1
# shutdown_timeout = 10


# class MockedSSHSession():
#     def __init__(self, *args):
#         return

#     def log_pty_request(self, *args):
#         return

#     def log_login_attempt(self, *args):
#         return

#     def log_command(self, *args):
#         return

#     def log_download(self, *args):
#         return

#     def end(self, *args):
#         return


# @pytest.fixture()
# def ssh_clients() -> List[SSHClient]:
#     # Setup paramiko SSH client
#     c1 = paramiko.SSHClient()
#     c2 = paramiko.SSHClient()
#     c3 = paramiko.SSHClient()
#     c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     c3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     return [c1, c2, c3]


# @patch("frontend.honeylogger.begin_ssh_session", return_value=MockedSSHSession())
# def test_connection_manager_shutdown(ssh_clients: List[SSHClient]):
#     conn_manager = ssh.ConnectionManager(
#         host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#     conn_manager.start()

#     time.sleep(server_start_delay)
#     ssh_clients[0].connect(server, port, "", "")
#     ssh_clients[1].connect(server, port, "", "")
#     ssh_clients[2].connect(server, port, "", "")

#     conn_manager.stop()
#     conn_manager.join(shutdown_timeout)
#     assert not conn_manager.is_alive()


# @patch("frontend.honeylogger.begin_ssh_session", return_value=MockedSSHSession())
# def test_valid_logins(ssh_clients: List[SSHClient]):
#     conn_manager = ssh.ConnectionManager(
#         host_key=key, port=port, auth_timeout=1, socket_timeout=1,
#         usernames=["masada", "linus"],
#         passwords=["1234", "torvalds"])
#     conn_manager.start()

#     time.sleep(server_start_delay)

#     ssh_clients[0].connect(server, port, "masada", "1234")
#     ssh_clients[1].connect(server, port, "linus", "torvalds")
#     ssh_clients[2].connect(server, port, "masada", "torvalds")

#     conn_manager.stop()
#     conn_manager.join(shutdown_timeout)


# def test_invalid_logins(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         mock.return_value = MockedSSHSession()

#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=1, socket_timeout=1,
#             usernames=["masada", "linus"],
#             passwords=["1234", "torvalds"])
#         conn_manager.start()

#         time.sleep(server_start_delay)

#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[0].connect(server, port, None, "1")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[1].connect(server, port, "linus", "masada")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, "masada")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, "linus", "torvald")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, "")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, "\r\n")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, "\r")
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[2].connect(server, port, None)

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# def test_request_shell_timeout(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         mock.return_value = MockedSSHSession()

#         auth_timeout = 1
#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=auth_timeout, socket_timeout=1)
#         conn_manager.start()
#         time.sleep(server_start_delay)

#         ssh_clients[0].connect(server, port, "", "")

#         time.sleep(auth_timeout + 0.1)
#         # Make sure the server has closed the connection
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[0].invoke_shell()

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# @patch("frontend.honeylogger.begin_ssh_session", return_value=MockedSSHSession())
# def test_channel_request(ssh_clients: List[SSHClient]):
#     conn_manager = ssh.ConnectionManager(
#         host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#     conn_manager.start()
#     time.sleep(server_start_delay)
#     ssh_clients[0].connect(server, port, "", "")
#     ssh_clients[0].invoke_shell()
#     ssh_clients[0].get_transport()
#     ssh_clients[0].close()

#     conn_manager.stop()
#     conn_manager.join(shutdown_timeout)


# def test_invalid_channel_request(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         mock.return_value = MockedSSHSession()

#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#         conn_manager.start()
#         time.sleep(server_start_delay)
#         ssh_clients[0].connect(server, port, "", "")
#         ssh_clients[0].invoke_shell()
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[0].get_transport().open_channel("sssion", timeout=2)
#         ssh_clients[0].close()

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# def test_sessions_started_logged(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         mock.return_value = MockedSSHSession()

#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#         conn_manager.start()
#         time.sleep(server_start_delay)

#         ssh_clients[0].connect(server, port, "", "")
#         ssh_clients[1].connect(server, port, "", "")
#         ssh_clients[2].connect(server, port, "", "")
#         assert mock.call_count == 3

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# def test_sessions_ended_logged(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         instance = MockedSSHSession()
#         instance.end = MagicMock()
#         mock.return_value = instance

#         auth_timeout = 1
#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=auth_timeout, socket_timeout=1, usernames=["hi"])
#         conn_manager.start()
#         time.sleep(server_start_delay)

#         # Client 0 will fail to login
#         # Client 1 will fail to send a shell request
#         # Client 2 will close the session himself
#         with pytest.raises(paramiko.SSHException):
#             ssh_clients[0].connect(server, port, "", "")

#         ssh_clients[1].connect(server, port, "hi", "")
#         time.sleep(auth_timeout + 0.1)

#         ssh_clients[2].connect(server, port, "hi", "")
#         ssh_clients[2].close()

#         assert mock.call_count == 3
#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# def test_logins_logged(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         instance = MockedSSHSession()
#         instance.log_login_attempt = MagicMock()
#         mock.return_value = instance

#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#         conn_manager.start()
#         time.sleep(server_start_delay)

#         username = "this is a"
#         password = "te\nst"
#         ssh_clients[0].connect(server, port, username, password)
#         instance.log_login_attempt.assert_called_with(username, password)
#         username += " good"
#         ssh_clients[1].connect(server, port, username, password)
#         instance.log_login_attempt.assert_called_with(username, password)

#         assert instance.log_login_attempt.call_count == 2

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)


# def test_pty_request_logged(ssh_clients: List[SSHClient]):
#     with patch("frontend.honeylogger.begin_ssh_session") as mock:
#         instance = MockedSSHSession()
#         instance.log_pty_request = MagicMock()
#         mock.return_value = instance

#         conn_manager = ssh.ConnectionManager(
#             host_key=key, port=port, auth_timeout=1, socket_timeout=1)
#         conn_manager.start()
#         time.sleep(server_start_delay)

#         ssh_clients[0].connect(server, port, "", "")
#         t = "t"
#         w, h = 1, 5
#         wp, hp = 12, 15
#         ssh_clients[0].get_transport().open_channel("session").get_pty(
#             term=t, width=w, height=h, width_pixels=wp, height_pixels=hp)
#         ssh_clients[0].close()

#         instance.log_pty_request.assert_called_with(t, w, h, wp, hp)
#         instance.log_pty_request.assert_called_once()

#         conn_manager.stop()
#         conn_manager.join(shutdown_timeout)
