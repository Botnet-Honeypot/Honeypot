"""This module contains logic related to SSH"""
import logging
import random
import socket
import sys
import threading
import time
import urllib.request
from ipaddress import ip_address
from typing import List, Optional, Set


from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, )
import paramiko
from paramiko.channel import Channel
from paramiko.ssh_exception import SSHException

import frontend.honeylogger as logger
from frontend.protocols.ssh_utils import TransportManager, ProxyHandler

debug_log = logging.getLogger("debuglogger")
debug_log.setLevel(logging.INFO)
log_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh = logging.FileHandler("./honeypot.log", encoding="UTF-8")
log_handler.setFormatter(formatter)
fh.setFormatter(formatter)
debug_log.addHandler(log_handler)
debug_log.addHandler(fh)


def check_alive(transport: paramiko.Transport):
    if transport.is_authenticated():
        transport.global_request("keepalive@lag.net", wait=False)
        transport.global_request("keepalive@lag.net", wait=False)
        transport.global_request("keepalive@lag.net", wait=True)


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

        r = random.randint(2, 8)
        debug_log.info(
            "[AUTH] Sleeping %s seconds and accepting, hopefully we see a shell/exec attempt", r)
        time.sleep(r)
        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        return 'password'

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return self._proxy_handler.open_channel(kind, chanid)

        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        debug_log.info("Wow this is rare, we got a shell request")
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_shell_request(
                channel):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        r = random.randint(2, 8)
        debug_log.info(
            "[CHANNEL] Sleeping %s seconds and then running, hopefully we see another shell/exec attempt",
            r)
        time.sleep(r)
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

        transport_manager = TransportManager()

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

            proxy_handler = ProxyHandler(session)
            transport.add_server_key(self._host_key)
            server = Server(session, proxy_handler, self._usernames, self._passwords)
            try:
                transport.start_server(server=server)
            except SSHException:
                debug_log.error("Failed to start the SSH server for %s", addr[0])
                session.end()
                continue

            transport_manager.add_transport((transport, proxy_handler))
