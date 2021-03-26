"""This module contains logic related to SSH"""
import logging
import socket
import signal
import sys
import threading
from time import sleep
import time
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
from frontend.protocols.transport_list import TransportList

debug_log = logging.getLogger(__name__)
debug_log.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log_handler.setFormatter(formatter)
debug_log.addHandler(log_handler)
debug_log.addHandler(logging.FileHandler("./honeypot.log", encoding="UTF-8"))


def handler(signum, frame):
    raise Exception("Timeout")


def check_alive(transport: paramiko.Transport):
    if transport.is_authenticated():
        transport.global_request("keepalive@lag.net", wait=False)
        transport.global_request("keepalive@lag.net", wait=False)
        transport.global_request("keepalive@lag.net", wait=True)


def check_transports_alive(transport_list: TransportList):
    while True:
        transports = transport_list.get_transports()
        debug_log.info("There are %s active transports", len(transports))
        # for transport_tuple in transports:
        #     signal.signal(signal.SIGALRM, handler)
        #     signal.alarm(10)
        #     try:
        #         print("Checking if the transport is alive")
        #         check_alive(transport_tuple[0])
        #     except Exception:
        #         print("killing one seemingly dead session")
        #         transport_tuple[0].close()
        #         transport_tuple[0].active = False
        #         transport_tuple[1].end()
        time.sleep(60*10)


def try_send_data(
        data: bytes,
        send_method: Callable[[bytes], None]) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        debug_log.warning("Timed out while trying to send data")
        return False
    except socket.error:
        debug_log.warning("Failed data")
        return False
    return True


def try_send_int(
        data: int,
        send_method: Callable[[int], None]) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        debug_log.warning("Timed out while trying to send data")
        return False
    except socket.error:
        debug_log.warning("Failed data")
        return False
    return True


def proxy_data(
        attacker_channel: paramiko.Channel,
        backend_channel: paramiko.Channel,
        log: SSHSession):
    """This will proxy data between two channels and log the data

    :param attacker_channel: The attacker channel
    :param backend_channel: The backend channeel
    """
    debug_log.info("Proxy data function enter")
    attacker_channel.settimeout(10)
    backend_channel.settimeout(10)
    while not (attacker_channel.eof_received or attacker_channel.closed):
        # If the backend channel is shut down
        if backend_channel.eof_received or backend_channel.closed:
            # If we don't have data buffered from the backend
            if not (backend_channel.recv_ready() or backend_channel.recv_stderr_ready()):
                # Send a final exit code if there is one
                if backend_channel.exit_status_ready():
                    exit_code = backend_channel.recv_exit_status()
                    try_send_int(exit_code, attacker_channel.send_exit_status)
                debug_log.debug("Backend channel is closed and no more data is available to read")
                break

        if attacker_channel.recv_ready():
            data = attacker_channel.recv(1024)
            debug_log.info("Command sent %s", data.decode("utf-8"))
            if not try_send_data(data, backend_channel.sendall):
                debug_log.debug("Failed to send data to backend_channel")
        if backend_channel.recv_ready():
            data = backend_channel.recv(1024)
            if not try_send_data(data, attacker_channel.sendall):
                debug_log.debug("Failed to send data to attacker_channel")
        if backend_channel.recv_stderr_ready():
            data = backend_channel.recv_stderr(1024)
            if not try_send_data(data, attacker_channel.sendall_stderr):
                debug_log.debug("Failed to send data to attacker_channel stderr")

        sleep(0.1)

    # If one is channel has recieeved eof make sure to send it to the other
    if attacker_channel.eof_received:
        debug_log.info("Closing the backend channel since the attacker channel has sent eof")
        backend_channel.close()
    if backend_channel.eof_received:
        debug_log.info("Closing the attacker channel since the backend channel has sent eof")
        attacker_channel.close()
    debug_log.info("Proxy data function done")


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
        # todo will use the backend
        self._open_proxy_transport()  # Open the backend transport

    def _open_proxy_transport(self) -> None:
        # Here we need to open a SSH connection to the backend
        # This will be done with our backend API later
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect("dozy.dev", port=2223, username="manager", password="Superman12")
        except Exception as exc:
            debug_log.exception("Failed to connect to dozy", exc_info=exc)
            return

        transport = client.get_transport()
        if transport is not None:
            self._backend_connection_success = True
            self._backend_transport = transport
        else:
            debug_log.error("Failed to obtain transport for dozy")

    def _get_corresponding_backend_channel(self, attacker_chan_id: int) -> paramiko.Channel:
        """Retrieves the corresponding backend channel that is related to the attacker channel

        :param attacker_chan_id: The attacker channel id
        :raises ValueError: If the corresponding backend channel does not exist
        :return: The corresponding backend channel
        """
        chan = self._backend_chan_proxies[attacker_chan_id]
        if chan is None:
            debug_log.error(
                "Failed to obtain a backend channel correspoding to the attacker channel %s",
                attacker_chan_id)
            print("This should not happen since a attacker channel id should ", end="")
            print("always be related to a backend channel")
            raise ValueError
        return chan

    def create_backend_connection(self, username: str) -> bool:
        """Sets up the a SSH connection to the backend with the given username

        :param username: The username to use in the container
        :return: True if the connection was successful
        """
        # todo we don't use the api currently
        return True

    def open_channel(self, kind: str, chanid: int) -> int:
        """Tries to open a channel to the backend

        :param kind: The channel kind
        :param chanid: The channel id of the channel that the attacker requested
        :return: An int given by paramiko
        """
        try:
            chan = self._backend_transport.open_channel(kind)
        except SSHException:
            debug_log.error("Failed to open a new channel with kind %s on the backend", kind)
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        debug_log.info("Attacker opening the channel %s", kind)
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
            debug_log.error("Failed to invoke shell on the backend channel with id %s",
                            backend_channel.chanid)
            return False

        debug_log.info("Attacker opening a shell on the backend")
        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, None))
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
        except UnicodeDecodeError:
            debug_log.error("Failed to decode the command to utf8")
            return False

        try:
            backend_channel.exec_command(cmd)
        except SSHException:
            debug_log.error("Failed to execute the command %s on the backend", cmd)
            return False

        debug_log.info("Attacker executing %s on the backend", cmd)

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, None))
        handle_thread.start()

        return True

    def handle_pty_request(self, attacker_channel: paramiko.Channel, term_string: str,
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
            backend_channel.get_pty(term_string, width, height, pixelwidth, pixelheight)
        except SSHException:
            debug_log.error("Failed to get pty on the backend")
            return False

        debug_log.info("Attacker sent pty request on channel %s", attacker_channel.chanid)
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
            debug_log.error("Failed to resize pty on the backend")
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

        if self._proxy_handler.create_backend_connection(username):
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
        try:
            term_string = term.decode("utf-8")
            self._session.log_pty_request(term_string, width, height, pixelwidth, pixelheight)
        except UnicodeError:
            debug_log.error("Failed to decode the term to utf8")
            return False

        return self._proxy_handler.handle_pty_request(
            channel, term_string, width, height, pixelwidth, pixelheight)

    def check_channel_window_change_request(self, channel: Channel, width: int, height: int,
                                            pixelwidth: int, pixelheight: int) -> bool:
        print("window change")
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
            debug_log.exception("Failed to bind the port %s", self._port, exc_info=exc)
            raise

        try:
            sock.listen(self._max_unaccepted_connections)
        except Exception as exc:
            debug_log.exception("Failed to listen to the socket", exc_info=exc)
            raise

        transport_list = TransportList()

        handle_thread = threading.Thread(
            target=check_transports_alive, args=(transport_list, ))
        handle_thread.start()

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
            except socket.timeout:
                # debug_log.info("Weird EOF error on sock.accept()")
                continue
            except Exception as exc:
                debug_log.exception(
                    "Failed to accept a connection from somewhere",  exc_info=exc)
                continue
            transport = paramiko.Transport(client)

            session = logger.begin_ssh_session(
                src_address=ip_address(addr[0]),
                src_port=addr[1],
                dst_address=self._ip,
                dst_port=self._port)

            proxy_handler = ProxyHandler()
            transport.add_server_key(self._host_key)
            server = Server(session, proxy_handler, self._usernames, self._passwords)
            try:
                # transport.set_keepalive(1)
                transport.start_server(server=server)
            except:
                debug_log.error("Failed to start the SSH server for %s", addr[0])
                session.end()
                continue

            transport_list.add_transport((transport, session))

        print("Why am i here", flush=True)
