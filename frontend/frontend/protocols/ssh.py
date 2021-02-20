"""This module contains logic related to SSH"""
import socket
import threading
from typing import Tuple

import paramiko
from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
                             OPEN_SUCCEEDED)


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    :type paramiko: paramiko.ServerInterface
    """

    def __init__(self) -> None:
        self.event = threading.Event()

    # Normal auth method
    def check_auth_password(self, username: str, password: str) -> int:
        print(f"username: {username}")
        print(f"password: {password}")
        return password == AUTH_SUCCESSFUL if password == "lol" else AUTH_FAILED

    # Public key auth method ()
    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        # return 'publickey' # If we allow publickey auth
        return 'password'  # If we don't allow publickey auth

    # SSH Server banner
    def get_banner(self) -> Tuple[str, str]:
        return ("SSH-2.0-OpenSSH_5.9p1 Debian-5ubuntu1.4", "en-US")

    # This is called after successfull auth
    def check_channel_request(self, kind: str, chanid: int) -> int:
        # print("Channel request received")
        if kind == "session":
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        # print("Request for shell received")
        self.event.set()
        return True

    def check_channel_pty_request(self, _: paramiko.Channel, term: bytes,
                                  width: int, height: int, pixelwidth: int,
                                  pixelheight: int, modes: bytes) -> bool:
        print("term:", term.decode("utf-8"))
        print("width:", width)
        print("height:", height)
        print("pixelwidth:", pixelwidth)
        print("pixelheight:", pixelheight)
        # print(type(modes).__name__)
        # print("modes:", modes.decode("utf-8"))
        # Allow everything
        return True


# todo should be singleton if the class does what it says in the docstring
# todo come up with a better name
class ConnectionManager():
    """ConnectionManager contains logic for connecting incoming
    SSH connections to instances of Server"""
    # todo move these to appropriate locations and allow them to be configured
    MAX_UNACCEPTED_CONNECTIONS = 100
    AUTH_TIMEOUT = 60
    SHELL_RQST_TIMEOUT = 10

    # todo move these to some constants file or something
    CR = b"\r"  # Carriage return (CR)
    LF = b"\n"  # Line feed (LF)

    def __init__(self, host_key: paramiko.PKey, port: int = 22) -> None:
        self.host_key = host_key
        self.port = port

    def listen(self) -> None:
        """Listens on the given port for an SSH connection
        and echoes out everything that is received in the socket
        """
        try:
            # SOCK_STREAM is TCP
            # AF_INET is IPv4
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Permit reuse of local addresses for this socket
            # More information on options can be found here
            # https://www.gnu.org/software/libc/manual/html_node/Socket_002dLevel-Options.html
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.port))
        except Exception as exc:
            print(f"Failed to bind port.\nError:{exc}")
            raise

        try:
            sock.listen(self.MAX_UNACCEPTED_CONNECTIONS)
            # todo Only accepts one client for now
            client, addr = sock.accept()
            transport = paramiko.Transport(client)
        except Exception as exc:
            print(f"Failed to accept connection\nError{exc}")
            raise

        print(f"Client {addr[0]}:{addr[1]} connected")

        if not transport.load_server_moduli():
            print("Could not load moduli")

        # Negotiate a new SSH session
        transport.add_server_key(self.host_key)
        server = Server()
        transport.start_server(server=server)

        chan = transport.accept(self.AUTH_TIMEOUT)
        if chan is None:
            print("Chan timeout")
            return

        # This is a 10 second timeout for them to send a shell request
        server.event.wait(self.SHELL_RQST_TIMEOUT)

        # Kick them out after 10 seconds of not sending a shell request
        if not server.event.is_set:
            transport.close()
            print("Timed out waiting for shell request")
            return

        chan.send(
            b"Welcome to Chalmers blueprint server. Please do not steal anything.\n")
        while True:
            received_bytes = chan.recv(1024)
            print(received_bytes.decode("utf-8"), end='')
            chan.send(received_bytes)
            # When we receive CR show LF as well
            if received_bytes == self.CR:
                print(self.LF.decode("utf-8"), end='')
                chan.send(self.LF)

        transport.close()
