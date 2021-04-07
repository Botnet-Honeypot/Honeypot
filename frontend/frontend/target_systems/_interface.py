"""Public interface classes for target systems module"""

from typing import Iterator, Protocol, Optional, Union
from ipaddress import IPv4Address, IPv6Address
from abc import abstractmethod
from datetime import datetime

IPAddress = Union[IPv4Address, IPv6Address]


class TargetSystem(Protocol):
    """A target system where attacker commands can be forwarded to."""

    address: str
    port: int


class Event:
    timestamp: datetime


class Download(Event):
    src_address: IPAddress
    url: str
    type: str
    data: memoryview


class TargetSystemProvider(Protocol):
    """A service that manages and provides target systems."""

    class YieldResult:
        """The result of yielding with collected information."""
        events: Iterator[Event]

    @abstractmethod
    def acquire_target_system(self, user: str, password: str) -> Optional[TargetSystem]:
        """Request to be given a target system.

        If no target system is currently available for acquisition,
        this method may be called again.

        :param user: The user to access the system using.
        :param password: The password of the user.
        :return: The acquired target system, if available, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def yield_target_system(self, target_system: TargetSystem) -> YieldResult:
        """Yield a previously acquired target system.

        :param target_system: The target system to yield.
        :return: The result of yielding with collected information.
        """
        raise NotImplementedError
