import datetime
import logging
import threading
from time import sleep
from typing import List, NamedTuple

import paramiko
from frontend.config import config
from ._proxy_handler import ProxyHandler
from ._ssh_server import Server


logger = logging.getLogger(__name__)


class TransportPair(
    NamedTuple("TransportPair",
               [("attacker_transport", paramiko.Transport),
                ("proxy_handler", ProxyHandler),
                ("server", Server)])):
    """Class for holding the attacker transport and the ProxyHandler as a tuple"""


class TransportManager:
    """TransportManager manages all the SSH transports and will end a session
    when it finds that the attacker transport has either closed or there has 
    been no activity for x minutes and they don't have any channels open.
    When the stop method is called, all transports managed my TransportManager
    are shut down.
    """

    _transport_list: List[TransportPair]

    def __init__(self) -> None:
        """Create a new Transpormanager instance that starts
        managing connections in a new thread
        """
        self._transport_list = []
        self._lock = threading.Lock()

        self._terminate_lock = threading.Lock()
        self._terminate = False

        self._handle_thread = threading.Thread(
            target=self.check_transports, args=(), name="Transport_Manager")
        self._handle_thread.start()

    def get_transports(self) -> List[TransportPair]:
        """Return the list of active SSH sessions (transports)

        :return: The active SSH sessions
        """
        with self._lock:
            return self._transport_list

    def add_transport(
            self, transport_pair: NamedTuple("TransportPair",
                                             [("attacker_transport", paramiko.Transport),
                                              ("proxy_handler", ProxyHandler),
                                              ("server", Server)])) -> None:
        """Add a new SSH session to the active list

        :param transport_tuple: The SSH session ot add
        """
        with self._lock:
            self._transport_list.append(transport_pair)

    def _remove_transport(
            self, transport_pair: TransportPair) -> None:
        """Remove a SSH session from the list

        :param transport_tuple: The session to remove
        """
        with self._lock:
            self._transport_list.remove(transport_pair)

    def stop(self):
        """Stop the TransportManager
        """
        logger.debug("Shutting down TransportManager")
        with self._terminate_lock:
            self._terminate = True

    def _end_attacker_transport(self, transport_pair: TransportPair):
        """Tries to end the attackers transport

        :param transport_pair: The transport pair
        """
        try:
            transport_pair.attacker_transport.close()
        except Exception as exc:
            logger.exception("Failed to close attacker transport", exc_info=exc)

    def _end_proxy_handler(self, transport_pair: TransportPair):
        """Ends the proxy_handler which in turn will end the transport to
        the backend and and the SSH logging session

        :param transport_pair: The transport pair
        """
        self._remove_transport(transport_pair)
        threading.Thread(
            target=transport_pair.proxy_handler.close_connection, args=()).start()

    def check_transports(self):
        """Methods that loops indefinitely and checks if there are SSH sessions
        that have ended
        """
        i = 0
        while True:
            with self._terminate_lock:
                if self._terminate:
                    break
            sleep(0.3)
            i += 1
            if i == 3000:
                i = 0
                logger.debug("There are %s active transports", len(self.get_transports()))
            for transport_pair in self.get_transports():
                # End the session if the attacker transport isn't active anymore
                if not transport_pair.attacker_transport.is_active():
                    logger.debug("Shutting down a session due to attacker transport being inactive")
                    self._end_proxy_handler(transport_pair)

                # If there are no channels open
                # pyright: reportGeneralTypeIssues=false
                elif len(transport_pair.attacker_transport._channels.values()) == 0:  # pylint: disable=protected-access
                    curr_time = datetime.datetime.now()
                    last_activity_time = transport_pair.server.get_last_activity()
                    difference = curr_time - last_activity_time

                    # If no activity end both sides
                    if difference.seconds > config.SSH_SESSION_TIMEOUT:
                        logger.debug(
                            "Shutting down a session due to no channels open and a timeout")
                        self._end_attacker_transport(transport_pair)
                        self._end_proxy_handler(transport_pair)

        # End all transports since we broke out of the while loop
        # and the thread is shutting down
        for transport_pair in self.get_transports():
            logger.debug("Shutting down a session due to TransportManager shutdown")
            if transport_pair.attacker_transport.is_active():
                self._end_attacker_transport(transport_pair)
            self._end_proxy_handler(transport_pair)

        logger.debug("TransportManager has shut down")
