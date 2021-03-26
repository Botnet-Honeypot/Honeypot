import time
import backend.filehandler as filehandler
from backend.container import Containers, Status


container_handler = Containers()

# Example code for showing multiple containers started and stopped
# Some of the parameters should be given by the frontend of the honeypot via HTTP API.


def main():
    container_id = 0
    user = "user"
    password = "password"
    port = 2222

    for container_id in range(5):
        config = container_handler.format_config(container_id, port, user, password)

        container_handler.create_container(config)

        port += 1

    # Close and destroy containers after a delay (this does not remove the storage folders)
    time.sleep(60)

    for container_id in range(5):
        try:
            container_handler.stop_container(Containers.ID_PREFIX + str(container_id))
            container_handler.destroy_container(Containers.ID_PREFIX + str(container_id))
            #container_handler.remove_folder(Containers.ID_PREFIX + str(container_id))

        except Exception as exception:
            print("Could not find or stop the specified container")
            raise exception


if __name__ == '__main__':
    main()
