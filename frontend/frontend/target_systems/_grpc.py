from typing import Optional
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from ._interface import TargetSystem, TargetSystemProvider


class _GrpcTargetSystem(TargetSystem):
    """Internal gRPC implementation of TargetSystem"""

    target_id: int

    def __init__(self, target_id: int, address: str, port: int) -> None:
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
        """Closes the underlying gRPC channel"""
        self.channel.close()
        self.channel = None

    def acquire_target_system(self, user: str, password: str) -> Optional[TargetSystem]:
        if self.channel is None:
            raise RuntimeError('gRPC channel was closed')

        # TODO: Error handling when acquisition failed, should return None

        stub = tsp.TargetSystemProviderStub(self.channel)
        response = stub.AcquireTargetSystem(
            messages.AcquisitionRequest(
                user=user,
                password=password
            ))

        return _GrpcTargetSystem(response.id, response.address, response.port)

    def yield_target_system(self, target_system: _GrpcTargetSystem) -> None:
        if self.channel is None:
            raise RuntimeError('Cannot be used outside with-statement')

        stub = tsp.TargetSystemProviderStub(self.channel)
        stub.YieldTargetSystem(messages.YieldRequest(id=target_system.target_id))
