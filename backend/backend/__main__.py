import time
import backend.container as container


containerHandler = container.Containers()

# Example code for showing multiple containers started and stopped
# These are the environment variables that needs to be provided to
# the container to start an instance.
# Some of these should be given by the frontend of the honeypot.


def main():
    container_id = 0
    port = 2222
    user = "testuser"
    password = "password"
    hostname = "Dell-T140"
    uid = 1000
    gid = 1000
    timezone = "Europe/London"
    sudo = "true"

    for container_id in range(5):
        containerHandler.create_container(
            container_id, port, user, password, hostname, uid, gid, timezone, sudo)
        port += 1

    time.sleep(60)

    # Close and destroy containers after 60 seconds
    for container_id in range(5):
        try:
            containerHandler.stop_container(container_id)
            containerHandler.destroy_container(container_id)
        except Exception as exception:
            print("Could not find or stop the specified container")
            raise exception


if __name__ == '__main__':
    main()
