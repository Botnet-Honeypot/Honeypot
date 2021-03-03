"""This module contains logic related to SSH"""
import socket
from typing import Iterable, Optional

import paramiko
from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
                             OPEN_SUCCEEDED)


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    :type paramiko: paramiko.ServerInterface
    """

    def __init__(
            self, usernames: Optional[Iterable[str]],
            passwords: Optional[Iterable[str]]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords

    # Normal auth method
    def check_auth_password(self, username: str, password: str) -> int:
        if self._usernames is not None and not username in self._usernames:
            return AUTH_FAILED
        if self._passwords is None or password in self._passwords:
            return AUTH_SUCCESSFUL
        else:
            return AUTH_FAILED

    # Public key auth method
    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        # return 'publickey' # If we allow publickey auth
        return 'password'  # If we don't allow publickey auth

    # SSH Server banner
    # def get_banner(self) -> Tuple[str, str]:
    #     return ("SSH-2.0-OpenSSH_5.9p1 Debian-5ubuntu1.4", "en-US")

    # This is called after successfull auth
    def check_channel_request(self, kind: str, chanid: int) -> int:
        # print("Channel request received")
        if kind == "session":
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        # print("Request for shell received")
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
class ConnectionManager():
    """ConnectionManager contains logic for connecting incoming
    SSH connections to instances of Server"""

    # todo move these to some constants file or something
    CR = b"\r"  # Carriage return (CR)
    LF = b"\n"  # Line feed (LF)

    def __init__(self, host_key: paramiko.PKey,
                 usernames: Optional[Iterable[str]] = None,
                 passwords: Optional[Iterable[str]] = None,
                 auth_timeout: float = 60,
                 max_unaccepted_connetions: int = 100,
                 port: int = 22) -> None:
        """Creates an instance of the ConnectionManager class

        :param host_key: The public key used by the server
        :type host_key: paramiko.PKey
        :param usernames: Allowed usernames, if it is None everything is allowed, defaults to None
        :type usernames: Optional[Iterable[str]], optional
        :param passwords: Allowed passwords, if it is None everything is allowed, defaults to None
        :type passwords: Optional[Iterable[str]], optional
        :param auth_timeout: Timeout in seconds for clients to authenticate, defaults to 60
        :type auth_timeout: float, optional
        :param max_unaccepted_connetions: Max unaccepted connections, defaults to 100
        :type max_unaccepted_connetions: int, optional
        :param port: The port to listen on, defaults to 22
        :type port: int, optional
        """
        self._host_key = host_key
        self._port = port
        self._usernames = usernames
        self._passwords = passwords
        self._auth_timeout = auth_timeout
        self._max_unaccepted_connections = max_unaccepted_connetions

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
            sock.bind(("", self._port))
        except Exception as exc:
            print(f"Failed to bind port.\nError:{exc}")
            raise

        try:
            sock.listen(self._max_unaccepted_connections)
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
        transport.add_server_key(self._host_key)
        server = Server(self._usernames, self._passwords)
        transport.start_server(server=server)

        chan = transport.accept(self._auth_timeout)
        if chan is None:
            print("Authentication timeout")
            transport.close()
            return

        chan.send(
            b"Welcome to the Chalmers blueprint server. Please do not steal anything.\r\n")
        while transport.active:
            received_bytes = chan.recv(1024)
            print(received_bytes.decode("utf-8"), end='')
            # The client might've abruptly closed the channel
            try:
                chan.send(received_bytes)
            except:
                pass
            # When we receive CR show LF as well
            if received_bytes == self.CR:
                print("\n", end='')
                chan.send(self.LF)
