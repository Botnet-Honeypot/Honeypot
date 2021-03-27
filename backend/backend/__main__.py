import time
import threading
import logging
from backend.container import Containers, Status


logger = logging.getLogger(__name__)

LOW_PORT = 2222  # Lowest port allowed
HIGH_PORT = 2232  # Highest port allowed

container_handler = Containers()
lock = threading.Lock()
ports = list(range(LOW_PORT, HIGH_PORT + 1))

# Example code for showing multiple containers started and stopped
# Some of the parameters should be given by the frontend of the honeypot via HTTP API.


def main():

    container_id = 0
    user = "user"
    password = "password"

    for container_id in range(5):
        port = acquire_port()
        config = container_handler.format_config(container_id, port, user, password)
        container_handler.create_container(config)

    # Close and destroy containers after a delay
    time.sleep(30)

    for container_id in range(5):
        try:
            port = container_handler.get_container_port(Containers.ID_PREFIX + str(container_id))
            container_handler.stop_container(Containers.ID_PREFIX + str(container_id))
            container_handler.destroy_container(Containers.ID_PREFIX + str(container_id))
            container_handler.prune_volumes()
            release_port(port)

        except Exception as exception:
            logging.error("Could not find or stop container %s", container_id)
            raise exception


def acquire_port() -> int:
    """Tries to acquire a free port from the list ports. May lock if there are no available ports.

    :return: A free port
    """
    lock.acquire()
    port = ports.pop()
    lock.release()
    return port


def release_port(port: int):
    """Releases the specified port, appending it to list ports.

    :param port: The port to be released
    """
    lock.acquire()
    ports.append(port)
    lock.release()


if __name__ == '__main__':
    main()
