import time
import logging
from backend.container import Containers, Status


logger = logging.getLogger(__name__)


container_handler = Containers()

# Example code for showing multiple containers started and stopped
# Some of the parameters should be given by the frontend of the honeypot via HTTP API.


def main():

    container_id = 0
    user = "user"
    password = "password"

    for container_id in range(5):
        config = container_handler.format_config(container_id, user, password)
        container_handler.create_container(config)
        # get the port, for returning to frontend
        port = container_handler.get_container_port(Containers.ID_PREFIX + str(container_id))

    # Close and destroy containers after a delay
    time.sleep(30)

    for container_id in range(5):
        try:
            container_handler.stop_container(Containers.ID_PREFIX + str(container_id))
            container_handler.destroy_container(Containers.ID_PREFIX + str(container_id))
            container_handler.prune_volumes()

        except Exception as exception:
            logging.error("Could not find or stop container %s", container_id)
            raise exception


if __name__ == '__main__':
    main()
