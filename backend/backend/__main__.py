import time
import backend.container as container


containerHandler = container.Containers()

# Example code for showing multiple containers started and stopped
# These are the environment variables that needs to be provided to
# the container to start an instance.
# Some of these should be given by the frontend of the honeypot.


def main():
    data = {
        'Image': 'ghcr.io/linuxserver/openssh-server', 'ID': 1002,
        'Environment': "['PUID=1000', 'PGID=1000', 'TZ=Europe/London', 'SUDO_ACCESS=true', \
                        'PASSWORD_ACCESS=true', 'USER_PASSWORD=password', 'USER_NAME=user']",
        'Port': "{'2222/tcp': 2222}",
        'User': 'user', 'Password': 'password', 'Hostname': 'hostname', 'UID': 1001,
        'GID': 1001, 'Timezone': 'Europe/London', 'SUDO': True, 'Volumes': ""}
    containerHandler.create_container(data)
    # for container_id in range(5):
    #    containerHandler.create_container(
    #        container_id, port, user, password, hostname, uid, gid, timezone, sudo)
    #    port += 1
    exit()
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
