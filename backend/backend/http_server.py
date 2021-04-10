"""Module implementing a gRPC HTTP API.

Currently handles requests to acquire and yield target systems.
"""

import logging
import uuid
from concurrent import futures
import threading
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from backend.container import Containers

logger = logging.getLogger(__name__)

__all__ = ['start_http_server']


class TargetSystemProvider(tsp.TargetSystemProviderServicer):
    """Implementation of gRPC TargetSystemProvider service"""

    _container_handler: Containers
    _target_system_address: str

    # All target systems which have successfully been acquired and not yet yielded
    # Must be accessed under lock
    _target_system_ids: set[str]
    _target_system_ids_lock: threading.Lock

    def __init__(self, container_handler: Containers, target_system_address: str):
        self._container_handler = container_handler
        self._target_system_address = target_system_address

        self._target_system_ids = set()
        self._target_system_ids_lock = threading.Lock()

    def AcquireTargetSystem(self, request, context):
        container_id = uuid.uuid4().int % (2**32)
        user = request.user
        password = request.password

        # Start container
        config = self._container_handler.format_config(container_id, user, password)
        self._container_handler.create_container(config)

        # TODO:
        # if no target system available:
        #    context.abort(grpc.StatusCode.UNAVAILABLE, "No target system is available to be acquired")
        #    return messages.AcquisitionResult()

        # Get the assigned port, for returning to frontend
        assigned_port = self._container_handler.get_container_port(config['ID'])

        # Keep track of which target systems have been acquired
        with self._target_system_ids_lock:
            self._target_system_ids.add(config['ID'])

        return messages.AcquisitionResult(
            id=config['ID'],
            address=self._target_system_address,
            port=assigned_port)

    def YieldTargetSystem(self, request, context):
        try:
            with self._target_system_ids_lock:
                # May not yield target system which was not
                # previously acquired from this provider
                if request.id not in self._target_system_ids:
                    context.abort(
                        grpc.StatusCode.NOT_FOUND,
                        f'Target system with ID {request.id} does not exist')
                    return messages.YieldResult()
                self._target_system_ids.remove(request.id)

            self._container_handler.stop_container(request.id)
            self._container_handler.destroy_container(request.id)

            # TODO: Properly cleanup after information is preserved and sent back to client
            # self.container_handler.prune_volumes()
        except Exception:
            logging.exception("Could not find, stop, destroy or cleanup container %s", request.id)
            raise

        return messages.YieldResult()


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
