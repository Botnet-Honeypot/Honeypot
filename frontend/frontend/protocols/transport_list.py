import threading
from typing import List, Tuple
import paramiko
from frontend.honeylogger import SSHSession


class TransportList:
    def __init__(self) -> None:
        self._transport_list: List[Tuple[paramiko.Transport, SSHSession]]
        self._transport_list = []
        self._lock = threading.Lock()

    def get_transports(self) -> List[Tuple[paramiko.Transport, SSHSession]]:
        with self._lock:
            return self._transport_list

    def add_transport(self, transport_tuple: Tuple[paramiko.Transport, SSHSession]) -> None:
        with self._lock:
            self._transport_list.append(transport_tuple)
