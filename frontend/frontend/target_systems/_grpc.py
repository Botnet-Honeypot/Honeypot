"""Implementations of target system module interfaces for gRPC remote service"""

import logging
from typing import Optional, cast
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from ._interface import TargetSystem, TargetSystemProvider

logger = logging.getLogger(__file__)


class _GrpcTargetSystem(TargetSystem):
    """Internal gRPC implementation of TargetSystem"""

    target_id: str

    def __init__(self, target_id: str, address: str, port: int) -> None:
        super().__init__()
        self.target_id = target_id
        self.address = address
        self.port = port


class _GrpcTargetSystemProvider(TargetSystemProvider):
    """TargetSystemProvider implementation using the target_system_provider gRPC protocol
    for forwarding of requests to a remote service."""

    channel: Optional[grpc.Channel]

    def __init__(self, server_address: str) -> None:
        """Initalizes a new TargetSystemProvider connecting to a given server address.
        :param server_address: The address of a gRPC server.
        """
        super().__init__()
        self.channel = grpc.insecure_channel(server_address)  # TODO: TLS

    def close_channel(self):
        """Closes the underlying gRPC channel.

        :raises RuntimeError: If called more than once.
        """
        if self.channel is None:
            raise RuntimeError('gRPC channel was already closed')
        self.channel.close()
        self.channel = None

    def acquire_target_system(self, user: str, password: str) -> Optional[TargetSystem]:
        if self.channel is None:
            raise RuntimeError('gRPC channel was closed')

        try:
            stub = tsp.TargetSystemProviderStub(self.channel)
            response = stub.AcquireTargetSystem(
                messages.AcquisitionRequest(
                    user=user,
                    password=password
                ))
        except grpc.RpcError as err:
            call = cast(grpc.Call, err)
            code = call.code()  # pylint: disable=no-member
            details = call.details()  # pylint: disable=no-member
            if code == grpc.StatusCode.UNAVAILABLE:
                logger.debug(
                    'No target system was available from remote TargetSystemProvider: %s',
                    details)
                return None
            raise Exception('Failed to aqcuire target system') from err

        return _GrpcTargetSystem(response.id, response.address, response.port)

    def yield_target_system(self, target_system: _GrpcTargetSystem) -> None:
        if self.channel is None:
            raise RuntimeError('gRPC channel was closed')

        try:
            stub = tsp.TargetSystemProviderStub(self.channel)
            stub.YieldTargetSystem(messages.YieldRequest(id=target_system.target_id))
        except grpc.RpcError:
            logger.warning(
                'Failed to yield target system to remote TargetSystemProvider',
                exc_info=True)
