"""Module implementing a gRPC HTTP API.

Currently handles requests to acquire and yield target systems.
"""

import logging
import uuid
from concurrent import futures
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
import backend.container as container

logger = logging.getLogger(__name__)

__all__ = ['start_http_server']


class TargetSystemProvider(tsp.TargetSystemProviderServicer):
    """Implementation of gRPC TargetSystemProvider service"""

    container_handler: container.Containers

    def __init__(self, container_handler: container.Containers):
        self.container_handler = container_handler

    def AcquireTargetSystem(self, request, context):
        container_id = uuid.uuid4().int % (2**32)
        # TODO: Use a free port given by OS or Docker instead
        port = (2222 + container_id) % (2**16)
        user = request.user
        password = request.password
        hostname = "Dell-T140"
        uid = 1000
        gid = 1000
        timezone = "Europe/London"
        sudo = "true"

        self.container_handler.create_container(
            container_id, port, user, password, hostname, uid, gid, timezone, sudo)

        return messages.AcquisitionResult(
            id=container_id,
            address='TEMP',  # TODO: Find network address of host that runs container
            port=port)

    def YieldTargetSystem(self, request, context):
        self.container_handler.stop_container(request.id)
        self.container_handler.destroy_container(request.id)

        return messages.YieldResult()


def start_http_server(container_handler: container.Containers,
                      bind_address: str = 'localhost:80') -> grpc.Server:
    """Starts a gRPC HTTP server with pre-configured services.

    :param container_handler: Container handler to use for
                              managing containers in response to service requests.
    :param port: The TCP port to run the server on, defaults to 80.
    :return: The gRPC server that was started.
    """

    logger.info('Starting gRPC HTTP Server on %s...', bind_address)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tsp.add_TargetSystemProviderServicer_to_server(TargetSystemProvider(container_handler), server)
    server.add_insecure_port(bind_address)  # TODO: ADD TLS!
    server.start()

    return server
