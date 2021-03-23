import logging
from concurrent import futures
import grpc
import target_system_provider_pb2_grpc

logger = logging.getLogger(__name__)


class TargetSystemProvider(target_system_provider_pb2_grpc.TargetSystemProviderServicer):
    def ProvideTargetSystem(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def YieldTargetSystem(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def start_http_server():
    logger.info('Starting gRPC HTTP Server...')

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    target_system_provider_pb2_grpc.add_TargetSystemProviderServicer_to_server(
        TargetSystemProvider(),
        server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


"""
# Example code for showing multiple containers started and stopped
# These are the environment variables that needs to be provided to
# the container to start an instance.
# Some of these should be given by the frontend of the honeypot.
id = 0
port = 2222
user = "testuser"
password = "password"
hostname = "Dell-T140"
uid = 1000
gid = 1000
timezone = "Europe/London"
sudo = "true"

containerHandler = container.Containers()

for i in range(5):
    containerHandler.create_container(
        id, port, user, password, hostname, uid, gid, timezone, sudo)
    id += 1
    port += 1

time.sleep(60)

# Close and destroy containers after 60 seconds
ID = 0
for i in range(5):
    try:
        containerHandler.stop_container(ID)
        containerHandler.destroy_container(ID)
    except:
        print("Could not find or stop the specified container, continuing anyways")
    ID += 1 """
