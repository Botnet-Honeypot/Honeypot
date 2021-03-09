import time
from threading import Thread

import paramiko
from paramiko import SSHClient
import pytest

import frontend.protocols.ssh as ssh


@pytest.fixture()
def ssh_client() -> SSHClient:
    # Setup paramiko SSH client
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return c


@pytest.fixture()
def conn_manager() -> Thread:
    key = paramiko.RSAKey(filename="./host.key")
    s = ssh.ConnectionManager(host_key=key, port=2222, auth_timeout=1)
    t = Thread(target=s.listen, args=())
    # Start ConnectionManager for SSH in a new thread
    t.start()
    return t


def test_request_shell_timeout(ssh_client: SSHClient, conn_manager: Thread):
    time.sleep(0.2)
    ssh_client.connect("127.0.0.1", 2222, "", "")

    time.sleep(1.1)
    # Make sure the server has closed the connection
    with pytest.raises(paramiko.SSHException):
        ssh_client.invoke_shell()

    assert not conn_manager.is_alive()


def test_request_shell(ssh_client: SSHClient, conn_manager: Thread):
    time.sleep(0.2)
    ssh_client.connect("127.0.0.1", 2222, "", "")
    ssh_client.invoke_shell()
    ssh_client.get_transport()
    ssh_client.close()
    assert conn_manager.is_alive()
