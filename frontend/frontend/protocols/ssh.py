"""This module contains logic related to SSH"""
import socket
import threading
from time import sleep
import urllib.request
from ipaddress import ip_address
from typing import Callable,  List, Optional, Set


from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
                             OPEN_SUCCEEDED)
import paramiko
from paramiko.ssh_exception import SSHException
from paramiko.transport import Transport
from paramiko.channel import Channel

from frontend.honeylogger import SSHSession
import frontend.honeylogger as logger


def try_send_data(data: bytes, send_method: Callable[[bytes], None]) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        return False
    except socket.error:
        return False
    return True


def shell_session(
        attacker_channel: paramiko.Channel, backend_channel: paramiko.Channel, log: SSHSession):
    """This will proxy data between two channels and log the data

    :param attacker_channel: The attacker channel
    :param backend_channel: The backend channeel
    """

    attacker_channel.settimeout(10)
    backend_channel.settimeout(10)
    # attacker_fd = attacker_channel.fileno()
    # backend_fd = backend_channel.fileno()
    while not attacker_channel.eof_received and not backend_channel.eof_received:
        if attacker_channel.recv_ready():
            data = attacker_channel.recv(1024)
            try_send_data(data, backend_channel.sendall)
        if backend_channel.recv_ready():
            data = backend_channel.recv(1024)
            try_send_data(data, attacker_channel.sendall)
        if backend_channel.recv_stderr_ready():
            data = backend_channel.recv_stderr(1024)
            try_send_data(data, attacker_channel.sendall_stderr)

        sleep(0.1)

    # If one is channel has recieeved eof make sure to send it to the other
    if attacker_channel.eof_received and not backend_channel.eof_sent:
        backend_channel.close()
    if backend_channel.eof_received and not attacker_channel.eof_sent:
        attacker_channel.close()


class ProxyHandler:
    """This class is responsible for proxying information from recieved attacker SSH channels
    to corresponding backend channels
    """

    def __init__(self) -> None:
        # This is the SSH transport to the backend
        self._backend_transport: Transport
        # This is the dict mapping the attacker channel ID's to a proxy channel to the backend
        self._backend_chan_proxies: dict[int, Channel]
        self._backend_chan_proxies = dict()

        # This is the session log we can log things to
        self._session_log: logger.SSHSession

        self._backend_connection_success = False
        self._open_proxy_transport()  # Open the backend transport

    def _open_proxy_transport(self) -> None:
        # Here we need to open a SSH connection to the backend
        # This will be done with our backend API later
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect("REDACTED", port=2223, username="REDACTED", password="REDACTED")
        except:
            print("Failed to connect to dozy")
            return

        transport = client.get_transport()
        if transport is not None:
            self._backend_connection_success = True
            self._backend_transport = transport

    def _get_corresponding_backend_channel(self, attacker_chan_id: int) -> paramiko.Channel:
        """Retrieves the corresponding backend channel that is related to the attacker channel

        :param attacker_chan_id: The attacker channel id
        :raises ValueError: If the corresponding backend channel does not exist
        :return: The corresponding backend channel
        """
        chan = self._backend_chan_proxies[attacker_chan_id]
        if chan is None:
            print("This should not happen")
            raise ValueError
        return chan

    def open_channel(self, kind: str, chanid: int) -> int:
        """Tries to open a channel to the backend

        :param kind: The channel kind
        :param chanid: The channel id of the channel that the attacker requested
        :return: An int given by paramiko
        """
        try:
            chan = self._backend_transport.open_channel(kind)
        except SSHException:
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        # Save the opened channel in our dict
        self._backend_chan_proxies[chanid] = chan
        return OPEN_SUCCEEDED

    def handle_shell_request(self, attacker_channel: paramiko.Channel):
        """Tries to send a shell request to the corresponding backend channel.
        If the shell request succeeds data will be proxied between the two channels

        :param attacker_channel: The attacker channel
        :return: True if we managed to send a shell request to the backend channel
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            backend_channel.invoke_shell()
        except SSHException:
            return False

        handle_thread = threading.Thread(
            target=shell_session, args=(attacker_channel, backend_channel, None))
        handle_thread.start()

        return True

    def handle_exec_request(self, attacker_channel: paramiko.Channel, command: bytes) -> bool:
        """Tries to send an exec request to the corresponding backend channel.
        If the exec request succeeds data will be proxied between the two channels

        :param attacker_channel: The attacker channel
        :param command: The command to execute
        :return: True if we managed to send an exec request to the backend channel
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            cmd = command.decode("utf-8")
            backend_channel.exec_command(cmd)
        except UnicodeDecodeError:
            return False
        except SSHException:
            return False

        # We have to create a method that connects the output of the proxy channel to the
        # attacker channel and run it in a new thread

        return True

    def handle_pty_request(self, attacker_channel: paramiko.Channel, term: bytes,
                           width: int, height: int, pixelwidth: int,
                           pixelheight: int) -> bool:
        """Tries to send a pty request to the corresponding backend channel.

        :param attacker_channel: The attacker channel
        :param term: The type of terminal requested
        :param width: The width of the screen in characters
        :param height: The height of the screen in characters
        :param pixelwidth: The width of the screen in pixels, if known (may be 0 if unknown)
        :param pixelheight: The height of the screen in pixels, if known (may be 0 if unknown)
        :return: True if the pty request succeeded
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            term_string = term.decode("utf-8")
            backend_channel.get_pty(term_string, width, height, pixelwidth, pixelheight)
        except SSHException:
            return False
        return True

    def handle_window_change_request(self, attacker_channel: Channel, width: int, height: int,
                                     pixelwidth: int, pixelheight: int) -> bool:
        """Tries to send a window change request to the corresponding backend channel.

        :param attacker_channel: The attacker channel
        :param width: The width of the screen in characters
        :param height: The height of the screen in characters
        :param pixelwidth: The width of the screen in pixels, if known (may be 0 if unknown)
        :param pixelheight: The height of the screen in pixels, if known (may be 0 if unknown)
        :return: True if the window change request succeeded
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            backend_channel.resize_pty(width, height, pixelwidth, pixelheight)
        except SSHException:
            return False
        return True


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    """

    def __init__(
            self, session: logger.SSHSession,
            proxy_handler: ProxyHandler,
            usernames: Optional[List[str]],
            passwords: Optional[List[str]]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords
        self._session = session
        self._proxy_handler = proxy_handler

        # The set of channels that have successfully issued a shell or exec request
        self._channels_done: Set[int]
        self._channels_done = set()

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
        return 'password'

    # This is called after successfull auth
    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return self._proxy_handler.open_channel(kind, chanid)

        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_shell_request(
                channel):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_exec_request(
                channel, command):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_pty_request(self, channel: paramiko.Channel, term: bytes,
                                  width: int, height: int, pixelwidth: int,
                                  pixelheight: int, _: bytes) -> bool:
        return self._proxy_handler.handle_pty_request(
            channel, term, width, height, pixelwidth, pixelheight)

    def check_channel_window_change_request(self, channel: Channel, width: int, height: int,
                                            pixelwidth: int, pixelheight: int) -> bool:
        return self._proxy_handler.handle_window_change_request(
            channel, width, height, pixelwidth, pixelheight)


# todo should be singleton if the class does what it says in the docstring
class ConnectionManager(threading.Thread):
    """ConnectionManager contains logic for listening for TCP connections
    and creating new threads of :class:`frontend.protocols.ssh.ConnectionManager`"""

    def __init__(self, host_key: paramiko.PKey,
                 usernames: Optional[List[str]] = None,
                 passwords: Optional[List[str]] = None,
                 auth_timeout: float = 60,
                 socket_timeout: float = 5,
                 max_unaccepted_connetions: int = 100,
                 port: int = 22) -> None:
        """Creates an instance of the ConnectionManager class

        :param host_key: The public key used by the server
        :param usernames: Allowed usernames, if it is None everything is allowed, defaults to None
        :param passwords: Allowed passwords, if it is None everything is allowed, defaults to None
        :param auth_timeout: Timeout in seconds for clients to authenticate, defaults to 60
        :param max_unaccepted_connetions: Max unaccepted connections, defaults to 100
        :param port: The port to listen on, defaults to 22
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
        runs new instances of :class:`frontend.protocols.ssh.ConnectionHandler` in new threads.

        :param socket_timeout:
            Seconds to wait before timeouting a connection attempt, defaults to 5
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

            proxy_handler = ProxyHandler()
            transport.add_server_key(self._host_key)
            server = Server(session, proxy_handler, self._usernames, self._passwords)
            transport.start_server(server=server)

        # Kill all threads it has created
        for instance in instance_list:
            instance.stop()

        # Make sure all threads have exited
        for instance in instance_list:
            instance.join()
