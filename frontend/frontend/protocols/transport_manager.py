import datetime
import logging
import threading
from time import sleep
from typing import List, NamedTuple, Tuple

import paramiko
from frontend.protocols.proxy_handler import ProxyHandler
from frontend.protocols.ssh_server import Server


debug_log = logging.getLogger("debuglogger")


class TransportPair(
    NamedTuple("Connection",
               [("attacker_transport", paramiko.Transport),
                ("proxy_handler", ProxyHandler),
                ("server", Server)])):
    """Class for holding the attacker transport and the ProxyHandler as a tuple
    """


class TransportManager:

    def __init__(self) -> None:
        # todo rewrite to named  tuple
        self._transport_list: List[TransportPair]
        self._transport_list = []
        self._lock = threading.Lock()

        handle_thread = threading.Thread(
            target=self.check_transports, args=())
        handle_thread.start()

    def get_transports(self) -> List[TransportPair]:
        """Return the list of active SSH sessions (transports)

        :return: The active SSH sessions
        """
        with self._lock:
            return self._transport_list

    def add_transport(
            self, transport_pair: TransportPair) -> None:
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

    def check_transports(self):
        """Methods that loops indefinitely and checks if there are SSH sessions
        that have ended
        """
        i = 0
        while True:
            sleep(0.3)
            i += 1
            if i == 2000:
                i = 0
                debug_log.debug("There are %s active transports", len(self.get_transports()))
            for transport_tuple in self.get_transports():
                # End the session if the attacker transport isn't active anymore
                if not transport_tuple.attacker_transport.is_active():
                    transport_tuple.proxy_handler.close_connection()
                    self._remove_transport(transport_tuple)

                # If there are no channels open
                # pyright: reportGeneralTypeIssues=false
                elif len(transport_tuple.attacker_transport._channels.values()) == 0:  # pylint: disable=protected-access
                    curr_time = datetime.datetime.now()
                    last_activity_time = transport_tuple.server.get_last_activity()
                    difference = curr_time - last_activity_time
                    if difference.seconds > 600:  # If no actvity in 10 minutes
                        debug_log.debug("Killing inactive session")
                        try:
                            transport_tuple[0].close()
                        except Exception as exc:
                            debug_log.exception("Failed to kill attacker transport", exc_info=exc)
                        transport_tuple.proxy_handler.close_connection()
                        self._remove_transport(transport_tuple)
