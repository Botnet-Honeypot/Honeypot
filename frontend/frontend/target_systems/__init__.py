"""Module for acquiring target systems that attacker commands can be sent to
and execution information can be collected from."""

from contextlib import contextmanager
from typing import Iterator
from ._interface import TargetSystem, TargetSystemProvider
from ._grpc import _GrpcTargetSystemProvider

__all__ = ['TargetSystem', 'TargetSystemProvider', 'create_grpc_target_system_provider']


def create_grpc_target_system_provider(server_address: str) -> TargetSystemProvider:
    """Factory for a TargetSystemProvider that connects to a remote gRPC service.

    :param server_address: The address of the gRPC server.
    :return: The constructed TargetSystemProvider.
    """

    return _GrpcTargetSystemProvider(server_address)
