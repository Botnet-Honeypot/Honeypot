"""This module contains logic related to SSH"""
import logging
import socket
import threading
from time import time
import urllib.request
from re import Pattern
from ipaddress import ip_address
from typing import Optional


import paramiko
from paramiko.ssh_exception import SSHException

import frontend.honeylogger as honeylogger
from frontend.config import config
from ._proxy_handler import ProxyHandler
from ._transport_manager import TransportManager, TransportPair
from ._ssh_server import Server
from frontend.target_systems import TargetSystemProvider

logger = logging.getLogger(__name__)


class ConnectionManager(threading.Thread):
    """ConnectionManager contains logic for listening for TCP connections
    and creating new threads of :class:`frontend.protocols.ssh.ConnectionManager`"""

    # The provider used to acquire target systems for each attacker connection
    _target_system_provider: TargetSystemProvider

    def __init__(self,
                 target_system_provider: TargetSystemProvider,
                 host_key: paramiko.PKey,
                 usernames: Optional[Pattern] = None,
                 passwords: Optional[Pattern] = None,
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
        self._transport_manager = TransportManager()
        self._target_system_provider = target_system_provider
        self._host_key = host_key
        self._usernames = usernames
        self._passwords = passwords
        self._max_unaccepted_connections = max_unaccepted_connetions
        self._port = port

        self._terminate = False
        self._lock = threading.Lock()

        self._ip = ip_address(urllib.request.urlopen('https://ident.me').read().decode('utf-8'))

    def stop(self) -> None:
        """Stops the `listen` method listening for TCP connections
        """
        logger.debug("Shutting down ConnectionManager")
        with self._lock:
            self._terminate = True

    def start_ssh_server(self, client: socket.socket):
        """Starts the SSH server for the givent client

        :param client: The socket object of the client connecting
        """
        transport = paramiko.Transport(client)
        transport.local_version = config.SSH_LOCAL_VERSION
        transport.add_server_key(self._host_key)

        src = client.getpeername()[0]
        src_port = client.getpeername()[1]

        session = honeylogger.create_ssh_session(
            src_address=ip_address(src),
            src_port=src_port,
            dst_address=self._ip,
            dst_port=self._port)

        proxy_handler = ProxyHandler(session, self._target_system_provider)
        server = Server(
            transport,
            session,
            proxy_handler,
            self._usernames,
            self._passwords)

        start_time = time()
        logger.debug('Starting SSH server')
        try:
            transport.start_server(server=server)
        except SSHException:
            logger.exception("Failed to start the SSH server for %s", src)
            return
        except EOFError:
            return
        except Exception as exc:
            logger.exception("Failed to start the SSH server for %s", src, exc_info=exc)
            return
        finally:
            logger.debug('start_server took %fs', time()-start_time)

        if not transport.is_active():
            return
        self._transport_manager.add_transport(TransportPair(transport, proxy_handler, server))

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
        except Exception:
            logger.exception("Failed to bind the port %s", self._port)
            raise

        try:
            sock.listen(self._max_unaccepted_connections)
        except Exception:
            logger.exception("Failed to listen to the socket")
            raise

        sock.settimeout(socket_timeout)
        while True:
            with self._lock:
                if self._terminate:
                    break

            # Try accepting connections
            try:
                client, _ = sock.accept()
            except socket.timeout:
                continue
            except Exception:
                logger.exception(
                    "Failed to accept a connection from somewhere")
                continue

            client.settimeout(60)
            threading.Thread(target=self.start_ssh_server, args=(client,), daemon=True).start()

        logger.debug("ConnectionManager has shut down")
        self._transport_manager.stop()
