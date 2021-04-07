"""Implementations of target system module interfaces for gRPC remote service"""

from ipaddress import IPv4Address, IPv6Address
import logging
from typing import Optional, cast
from collections.abc import Iterator
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from ._interface import TargetSystem, TargetSystemProvider, Event, Download

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

    def yield_target_system(
            self, target_system: _GrpcTargetSystem) -> TargetSystemProvider.YieldResult:
        if self.channel is None:
            raise RuntimeError('gRPC channel was closed')

        try:
            stub = tsp.TargetSystemProviderStub(self.channel)
            stream = stub.YieldTargetSystem(
                messages.YieldRequest(id=target_system.target_id))

            def events() -> Iterator[Event]:
                for item in stream:
                    event: Optional[Event] = None

                    if item.event.WhichOneof('type') == 'download':
                        event = download_event_from_message(item.event.download)
                    else:
                        logger.warning('Unhandled event type recieved from target system provider')

                    if event is not None:
                        event.timestamp = item.event.timestamp.ToDatetime()
                        yield event

            result = TargetSystemProvider.YieldResult()
            result.events = events()
            return result
        except grpc.RpcError as err:
            raise Exception(
                f'Failed to yield target system {target_system.address}:{target_system.port}'
                ' to remote TargetSystemProvider') from err


def download_event_from_message(message: messages.Event.Download) -> Download:
    download = Download()

    if message.WhichOneof('src_address') == 'src_address_v4':
        download.src_address = IPv4Address(message.src_address_v4)
    elif message.WhichOneof('src_address') == 'src_address_v6':
        download.src_address = IPv6Address(message.src_address_v6)
    else:
        raise Exception('No src_address set in download message')

    download.url = message.url
    download.type = message.type
    download.data = message.data

    return download
