# pytest . --cov-report term-missing
import time
from threading import Thread
from typing import List

import frontend.protocols.ssh as ssh
import paramiko
import pytest
from frontend.protocols.ssh import ConnectionManager
from paramiko import SSHClient

key = paramiko.RSAKey(filename="./host.key")
server = "127.0.0.1"
port = 2222


@pytest.fixture()
def ssh_clients() -> List[SSHClient]:
    # Setup paramiko SSH client
    c1 = paramiko.SSHClient()
    c2 = paramiko.SSHClient()
    c3 = paramiko.SSHClient()
    c1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return [c1, c2, c3]


def test_connection_manager_shutdown(ssh_clients: List[SSHClient]):
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=1, socket_timeout=1)
    conn_manager.start()

    time.sleep(0.1)  # Wait for server to start
    ssh_clients[0].connect(server, port, "", "")
    ssh_clients[1].connect(server, port, "", "")
    ssh_clients[2].connect(server, port, "", "")

    conn_manager.stop()
    conn_manager.join(20)
    assert not conn_manager.is_alive()


def test_valid_logins(ssh_clients: List[SSHClient]):
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=1, socket_timeout=1,
        usernames=["masada", "linus"],
        passwords=["1234", "torvalds"])
    conn_manager.start()

    time.sleep(0.1)  # Wait for server to start

    ssh_clients[0].connect(server, port, "masada", "1234")
    ssh_clients[1].connect(server, port, "linus", "torvalds")
    ssh_clients[2].connect(server, port, "masada", "torvalds")

    conn_manager.stop()
    conn_manager.join(20)


def test_invalid_logins(ssh_clients: List[SSHClient]):
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=1, socket_timeout=1,
        usernames=["masada", "linus"],
        passwords=["1234", "torvalds"])
    conn_manager.start()

    time.sleep(0.1)  # Wait for server to start

    with pytest.raises(paramiko.SSHException):
        ssh_clients[0].connect(server, port, None, "1")
    with pytest.raises(paramiko.SSHException):
        ssh_clients[1].connect(server, port, "linus", "masada")
    with pytest.raises(paramiko.SSHException):
        ssh_clients[2].connect(server, port, "masada")

    conn_manager.stop()
    conn_manager.join(20)


def test_request_shell_timeout(ssh_clients: List[SSHClient]):
    auth_timeout = 1
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=auth_timeout, socket_timeout=1)
    conn_manager.start()

    time.sleep(0.1)  # Wait for server to start
    ssh_clients[0].connect(server, port, "", "")

    time.sleep(auth_timeout + 0.1)
    # Make sure the server has closed the connection
    with pytest.raises(paramiko.SSHException):
        ssh_clients[0].invoke_shell()

    conn_manager.stop()
    conn_manager.join(20)


def test_channel_request(ssh_clients: List[SSHClient]):
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=1, socket_timeout=1)
    conn_manager.start()
    time.sleep(0.2)
    ssh_clients[0].connect(server, port, "", "")
    ssh_clients[0].invoke_shell()
    ssh_clients[0].get_transport()
    ssh_clients[0].close()

    conn_manager.stop()
    conn_manager.join(20)


def test_invalid_channel_request(ssh_clients: List[SSHClient]):
    conn_manager = ssh.ConnectionManager(
        host_key=key, port=port, auth_timeout=1, socket_timeout=1)
    conn_manager.start()
    time.sleep(0.2)
    ssh_clients[0].connect(server, port, "", "")
    ssh_clients[0].invoke_shell()
    with pytest.raises(paramiko.SSHException):
        ssh_clients[0].get_transport().open_channel("sssion", timeout=2)
    ssh_clients[0].close()

    conn_manager.stop()
    conn_manager.join(20)
