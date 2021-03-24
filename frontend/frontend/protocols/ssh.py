"""This module contains logic related to SSH"""
import socket
import queue
import threading
import urllib.request
from ipaddress import ip_address
from typing import List, Optional

from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
                             OPEN_SUCCEEDED)
import paramiko

from frontend.protocols.sshevents import ServerEvent, ShellRequest, ExecRequest
import frontend.honeylogger as logger

SSH_VERSION = "SSH-2.0-dropbear_2020.80"


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    :type paramiko: paramiko.ServerInterface
    """

    def __init__(
            self, session: logger.SSHSession,
            usernames: Optional[List[str]],
            passwords: Optional[List[str]],
            event_queue: queue.Queue[ServerEvent]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords
        self._session = session
        self._chan_id = None
        self._recieved_shell_or_exec_request = False
        self._event_queue = event_queue

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
        return 'password'  # If we don't allow publickey auth

    # This is called after successfull auth
    def check_channel_request(self, kind: str, chanid: int) -> int:
        # Only allow one session to be opened
        if kind == "session" and self._chan_id is None:
            self._chan_id = chanid
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        if channel.get_id() == self._chan_id and not self._recieved_shell_or_exec_request:
            self._recieved_shell_or_exec_request = True
            self._event_queue.put(ShellRequest())
            return True
        return False

    def check_channel_pty_request(self, channel: paramiko.Channel, term: bytes,
                                  width: int, height: int, pixelwidth: int,
                                  pixelheight: int, modes: bytes) -> bool:
        self._session.log_pty_request(term.decode("utf-8"), width, height, pixelwidth, pixelheight)
        return channel.get_id() == self._chan_id

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        if channel.get_id() == self._chan_id and not self._recieved_shell_or_exec_request:
            self._recieved_shell_or_exec_request = True
            self._event_queue.put(ExecRequest(command))
            return True
        return False


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
        self._usernames = usernames
        self._passwords = passwords
        self._host_key = host_key
        self._transport = transport
        self._session = session
        self._auth_timeout = auth_timeout
        self._lock = threading.Lock()
        self._server_event_queue = queue.Queue(maxsize=0)  # infinite capacity

    def _setup_server(self, host_key: paramiko.PKey,
                      usernames: Optional[List[str]],
                      passwords: Optional[List[str]]) -> None:
        if not self._transport.load_server_moduli():
            print("Could not load moduli")

        self._transport.add_server_key(host_key)
        server = Server(self._session, usernames, passwords, self._server_event_queue)
        self._transport.start_server(server=server)

    def stop(self) -> None:
        """Stops the `handle` method handling SSH connections"""
        with self._lock:
            self._terminate = True
        # It may be the case that the handle method is blocking on the queue
        # so putting something in it will force it to continue
        self._server_event_queue.put(None)

    # todo check if session.end can be called through decerator
    def handle(self) -> None:
        """Waits for an SSH channel to be established and handles
        the connection"""

        # Setup the server
        try:
            self._setup_server(self._host_key, self._usernames, self._passwords)
        except:
            # todo log
            self._session.end()
            return

        chan = self._transport.accept(self._auth_timeout)
        if chan is None:
            # todo log this
            print("Authentication timeout")
            self._transport.close()
            self._session.end()
            return

        event = None
        try:
            # The 30 seconds acts as a safety precaution if someone were to
            # connect and disconnect without sending a session or exec request
            event = self._server_event_queue.get(block=True, timeout=30)
        except queue.Empty:
            with self._lock:
                self._terminate = True

        if self._terminate:
            self._transport.close()
            self._session.end()
        elif isinstance(event, ShellRequest):
            # Here we the user sent a shell request
            chan.settimeout(2)
            while True:
                with self._lock:
                    if not self._transport.active or self._terminate:
                        break

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
        elif isinstance(event, ExecRequest):
            # Here we the user sent an exec request
            chan.sendall(event.get_command())
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
        with self._lock:
            self._terminate = True

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
            with self._lock:
                if self._terminate:
                    break

            # Try accepting connections
            try:
                client, addr = sock.accept()
                transport = paramiko.Transport(client)
                transport.local_version = SSH_VERSION
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
