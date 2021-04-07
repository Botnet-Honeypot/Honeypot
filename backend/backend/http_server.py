"""Module implementing a gRPC HTTP API.

Currently handles requests to acquire and yield target systems.
"""

import tempfile
import logging
from typing import Any, cast
import uuid
from concurrent import futures
from pyshark.capture.file_capture import FileCapture
from pyshark.capture.pipe_capture import PipeCapture
import grpc
from pyshark.packet.layer import Layer
from pyshark.packet.packet import Packet
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from backend.container import Containers

logger = logging.getLogger(__name__)

__all__ = ['start_http_server']


class TargetSystemProvider(tsp.TargetSystemProviderServicer):
    """Implementation of gRPC TargetSystemProvider service"""

    container_handler: Containers
    target_system_address: str

    def __init__(self, container_handler: Containers, target_system_address: str):
        self.container_handler = container_handler
        self.target_system_address = target_system_address

    def AcquireTargetSystem(self, request, context):
        container_id = uuid.uuid4().int % (2**32)
        user = request.user
        password = request.password

        # Start container
        config = self.container_handler.format_config(container_id, user, password)
        self.container_handler.create_container(config)

        # TODO:
        # if no target system available:
        #    context.abort(grpc.StatusCode.UNAVAILABLE, "No target system is available to be acquired")
        #    return messages.AcquisitionResult()

        # Get the assigned port, for returning to frontend
        assigned_port = self.container_handler.get_container_port(config['ID'])

        return messages.AcquisitionResult(
            id=config['ID'],
            address=self.target_system_address,
            port=assigned_port)

    def YieldTargetSystem(self, request, context):
        try:
            self.container_handler.stop_container(request.id)

            # try:
            # Collect downloads
            with tempfile.NamedTemporaryFile() as temp:
                with self.container_handler.get_container_netlog(request.id) as netlog_file:
                    temp.write(netlog_file.read())

                tshark_params = {
                    '-J': 'http ip ipv6'
                }
                with FileCapture(input_file=temp.name,
                                 display_filter='http.response',
                                 custom_parameters=tshark_params) as cap:
                    for packet in cap:
                        result = messages.YieldResult()
                        event = result.event
                        event.timestamp.FromDatetime(packet.sniff_time)

                        if 'ip' in packet:
                            ipv4: Layer = packet['ip']
                            event.download.src_address_v4 = ipv4.get_field('src').hex_value
                        elif 'ipv6' in packet:
                            ipv6: Layer = packet['ipv6']
                            event.download.src_address_v6 = ipv6.get_field('src').binary_value
                        else:
                            raise RuntimeError(
                                f'No IPv4 or IPv6 header on HTTP response for {request.id}')

                        http: Layer = packet['http']
                        event.download.url = http.get_field_value('response_for_uri')
                        event.download.type = http.get('content_type',
                                                       default='application/octet-stream')
                        event.download.data = http.get_field('file_data').binary_value

                        yield result

                    logger.debug('Extracted netlog!')
            # finally:
                self.container_handler.destroy_container(request.id)

            # TODO: Properly cleanup after information is preserved and sent back to client
            # self.container_handler.prune_volumes()
        except Exception as exception:
            logger.exception("Could not find, stop, destroy or cleanup container %s", request.id)
            raise exception


def start_http_server(container_handler: Containers,
                      target_system_address: str,
                      bind_address: str = 'localhost:80') -> grpc.Server:
    """Starts a gRPC HTTP server with pre-configured services.

    :param container_handler: Container handler to use for
                              managing containers in response to service requests.
    :param port: The TCP port to run the server on, defaults to 80.
    :return: The gRPC server that was started.
    """

    logger.info('Starting gRPC HTTP Server on %s...', bind_address)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tsp.add_TargetSystemProviderServicer_to_server(
        TargetSystemProvider(container_handler, target_system_address), server)
    server.add_insecure_port(bind_address)  # TODO: ADD TLS!
    server.start()

    return server
