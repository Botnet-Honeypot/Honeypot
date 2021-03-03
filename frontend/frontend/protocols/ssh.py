"""This module contains logic related to SSH"""
import socket
import threading
import urllib.request
from ipaddress import ip_address
from typing import Iterable, List, Optional

from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
                             OPEN_SUCCEEDED)
import paramiko
import frontend.honeylogger as logger


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    :type paramiko: paramiko.ServerInterface
    """

    def __init__(
            self, session: logger.SSHSession,
            usernames: Optional[List[str]],
            passwords: Optional[List[str]]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords
        self._session = session

    # Normal auth method
    def check_auth_password(self, username: str, password: str) -> int:
        self._session.log_login_attempt(username, password)
        if self._usernames is not None and not username in self._usernames:
            return AUTH_FAILED
        if self._passwords is None or password in self._passwords:
            return AUTH_SUCCESSFUL
        return AUTH_FAILED

    # Public key auth method
    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        # return 'publickey' # If we allow publickey auth
        return 'password'  # If we don't allow publickey auth

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
        self._session.log_pty_request(term.decode("utf-8"), width, height, pixelwidth, pixelheight)
        return True


class ConnectionHandler(threading.Thread):
    # todo move these to some constants file or something
    CR = b"\r"  # Carriage return (CR)
    LF = b"\n"  # Line feed (LF)

    def __init__(self, transport: paramiko.Transport,
                 session: logger.SSHSession,
                 host_key: paramiko.PKey,
                 usernames: Optional[List[str]],
                 passwords: Optional[List[str]],
                 auth_timeout: float) -> None:
        super().__init__(target=self.handle, daemon=False)
        self._terminate = False
        self._transport = transport
        self._session = session
        self._auth_timeout = auth_timeout
        self._setup_server(host_key, usernames, passwords)
        self._lock = threading.Lock()

    def _setup_server(self, host_key: paramiko.PKey,
                      usernames: Optional[List[str]],
                      passwords: Optional[List[str]]) -> None:
        if not self._transport.load_server_moduli():
            print("Could not load moduli")

        self._transport.add_server_key(host_key)
        server = Server(self._session, usernames, passwords)
        self._transport.start_server(server=server)

    def stop(self) -> None:
        """Stops the `handle` method handling SSH connections"""
        self._lock.acquire()
        self._terminate = True
        self._lock.release()

    # todo check if session.end can be called through decerator
    def handle(self) -> None:
        """Waits for an SSH channel to be established and handles
        the connection"""
        chan = self._transport.accept(self._auth_timeout)
        if chan is None:
            # todo log this
            print("Authentication timeout")
            self._transport.close()
            self._session.end()
            return

        chan.send(
            b"\r\nWelcome to the Chalmers blueprint server. Please do not steal anything.\r\n")

        # todo wait for user to send shell request
        # todo don't hardcode
        chan.settimeout(2)
        while True:
            self._lock.acquire()
            if not self._transport.active or self._terminate:
                self._lock.release()
                break
            self._lock.release()

            try:
                received_bytes = chan.recv(1024)
                print(received_bytes.decode("utf-8"), end='')
                chan.send(received_bytes)
            except socket.timeout:
                continue
            except:
                # todo log this
                continue
            # When we receive CR show LF as well
            if received_bytes == self.CR:
                print("\n", end='')
                chan.send(self.LF)

        if self._terminate:
            self._transport.close()

        self._session.end()


# todo should be singleton if the class does what it says in the docstring
class ConnectionManager(threading.Thread):
    """ConnectionManager contains logic for listening for TCP connections
    and creating new threads of class:`ConnectionHandler`"""

    def __init__(self, host_key: paramiko.PKey,
                 usernames: Optional[List[str]] = None,
                 passwords: Optional[List[str]] = None,
                 auth_timeout: float = 60,
                 socket_timeout: float = 5,
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
        super().__init__(target=self.listen, args=(socket_timeout,), daemon=False)
        self._terminate = False
        self._host_key = host_key
        self._port = port
        self._usernames = usernames
        self._passwords = passwords
        self._auth_timeout = auth_timeout
        self._max_unaccepted_connections = max_unaccepted_connetions
        self._lock = threading.Lock()

        # todo is there any better way to get the public facing ip?
        self._ip = ip_address(urllib.request.urlopen('https://ident.me').read().decode('utf8'))

    def stop(self) -> None:
        """Stops the `listen` method listening for TCP connections and returns when
        all threads that has been created has shut down.
        """
        self._lock.acquire()
        self._terminate = True
        self._lock.release()

    def listen(self, socket_timeout: float = 5) -> None:
        """Starts listening for TCP connections on the given ports.
        runs new instances of class:`ConnectionHandler` in new threads.

        :param socket_timeout:
            Seconds to wait before timeouting a connection attempt, defaults to 5
        :type socket_timeout: int, optional
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
        except Exception as exc:
            print(f"Failed to accept connection\nError{exc}")
            raise

        # This provides type hinting
        instance_list:  List[ConnectionHandler]
        instance_list = []

        sock.settimeout(socket_timeout)
        while True:
            self._lock.acquire()
            if self._terminate:
                self._lock.release()
                break
            self._lock.release()

            # Try accepting connections
            try:
                client, addr = sock.accept()
                transport = paramiko.Transport(client)
            except Exception as exc:
                # todo log
                continue

            session = logger.begin_ssh_session(
                src_address=ip_address(addr[0]),
                src_port=addr[1],
                dst_address=self._ip,
                dst_port=self._port)

            # Start the connectionhandler with the new connection
            conn_handler = ConnectionHandler(
                transport, session, self._host_key,  self._usernames, self._passwords,
                self._auth_timeout)
            conn_handler.start()
            instance_list.append(conn_handler)

        # Kill all threads it has created
        for instance in instance_list:
            instance.stop()

        # Make sure all threads have exited
        for instance in instance_list:
            instance.join()
