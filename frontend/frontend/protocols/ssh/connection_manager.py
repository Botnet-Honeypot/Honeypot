"""This module contains logic related to SSH"""
import logging
import socket
import sys
import threading
import urllib.request
from ipaddress import ip_address
from typing import List, Optional


import paramiko
from paramiko.ssh_exception import SSHException

import frontend.honeylogger as logger
from frontend.config import config
from ._proxy_handler import ProxyHandler
from ._transport_manager import TransportManager, TransportPair
from ._ssh_server import Server

debug_log = logging.getLogger(config.SSH_DEBUG_LOG)


class ConnectionManager(threading.Thread):
    """ConnectionManager contains logic for listening for TCP connections
    and creating new threads of :class:`frontend.protocols.ssh.ConnectionManager`"""

    def __init__(self, host_key: paramiko.PKey,
                 usernames: Optional[List[str]] = None,
                 passwords: Optional[List[str]] = None,
                 socket_timeout: float = 5,
                 max_unaccepted_connetions: int = 100,
                 port: int = 22) -> None:
        """Creates an instance of the ConnectionManager class which will start listening
        on the given port once the `start` method is called.


        :param host_key: The public key used by the server
        :param usernames: Allowed usernames, if it is None everything is allowed, defaults to None
        :param passwords: Allowed passwords, if it is None everything is allowed, defaults to None
        :param socket_timeout: The timeout of the socket, defaults to 5
        :param max_unaccepted_connetions: Max unaccepted connections, defaults to 100
        :param port: The port to listen on, defaults to 22
        """
        super().__init__(target=self.listen, args=(socket_timeout,), daemon=False)
        self._terminate = False
        self._host_key = host_key
        self._port = port
        self._usernames = usernames
        self._passwords = passwords
        self._max_unaccepted_connections = max_unaccepted_connetions
        self._lock = threading.Lock()

        # todo is there any better way to get the public facing ip?
        self._ip = ip_address(urllib.request.urlopen('https://ident.me').read().decode('utf8'))

    def stop(self) -> None:
        """Stops the `listen` method listening for TCP connections
        """
        with self._lock:
            self._terminate = True

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
            with self._lock:
                if self._terminate:
                    break

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
            transport.local_version = config.SSH_LOCAL_VERSION

            session = logger.create_ssh_session(
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
                continue
            except EOFError:
                continue
            except Exception as exc:
                debug_log.exception("Failed to start the SSH server for %s", addr[0], exc_info=exc)
                continue

            debug_log.info("Remote SSH version %s", transport.remote_version)

            # Here we are sure an SSH session has been established
            session.begin_ssh_session()

            transport_manager.add_transport(TransportPair(transport, proxy_handler, server))
