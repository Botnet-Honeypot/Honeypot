import logging
import uuid
from concurrent import futures
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
import backend.container as container

logger = logging.getLogger(__name__)


class TargetSystemProvider(tsp.TargetSystemProviderServicer):
    containerHandler: container.Containers

    def __init__(self, containerHandler: container.Containers):
        self.containerHandler = containerHandler

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

        self.containerHandler.create_container(
            container_id, port, user, password, hostname, uid, gid, timezone, sudo)

        return messages.AcquisitionResult(
            id=container_id,
            address='TEMP',  # TODO: Find network address of host that runs container
            port=port)

    def YieldTargetSystem(self, request, context):
        self.containerHandler.stop_container(request.id)
        self.containerHandler.destroy_container(request.id)

        return messages.YieldResult()


def start_http_server(containerHandler: container.Containers, port: int = 50051) -> grpc.Server:
    logger.info('Starting gRPC HTTP Server...')

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tsp.add_TargetSystemProviderServicer_to_server(TargetSystemProvider(containerHandler), server)
    server.add_insecure_port('[::]:' + str(port))
    server.start()
    # server.wait_for_termination()
    return server
