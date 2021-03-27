from typing import Protocol, Optional
from abc import abstractmethod


class TargetSystem(Protocol):
    """A target system where attacker commands can be forwarded to."""

    address: str
    port: int


class TargetSystemProvider(Protocol):
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
    def yield_target_system(self, target_system: TargetSystem) -> None:
        """Yield a previously acquired target system.

        :param target_system: The target system to yield.
        """
        raise NotImplementedError
