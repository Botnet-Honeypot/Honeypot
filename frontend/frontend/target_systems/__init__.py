from typing import Protocol, Optional
from abc import abstractmethod
from ._grpc import _GrpcTargetSystemProvider

__all__ = ['TargetSystem', 'TargetSystemProvider', 'create_grpc_target_system_provider']


class TargetSystem(Protocol):
    """A target system where attacker commands can be forwarded to."""

    address: str
    port: int


class TargetSystemProvider(Protocol):
    @abstractmethod
    def acquire_target_system(self, user: str, password: str) -> Optional[TargetSystem]:
        """Request to be given a target system.

        :param user: The user to access the system using.
        :param password: The password of the user.
        :return: The acquired target system, if available, otherwise None.
        """
        raise NotImplementedError

    @abstractmethod
    def yield_target_system(self, target_system: TargetSystem) -> None:
        """Yield a previously acquired target system.

        :param target_system: The target system to yield.
        :raises ValueError: If given target system has already been yielded.
        :raises ValueError: If given target system was not acquired from this provider.
        """
        raise NotImplementedError


def create_grpc_target_system_provider(server_address: str) -> TargetSystemProvider:
    """Factory for a TargetSystemProvider that connects to a remote gRPC service.

    Should be used in a with-statement to open and close connection channel.

    :param server_address: The address of the gRPC server.
    :return: The constructed TargetSystemProvider.
    """

    return _GrpcTargetSystemProvider(server_address)
