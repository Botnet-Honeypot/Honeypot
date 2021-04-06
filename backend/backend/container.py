"""Contains class and methods used for handling docker containers"""

import io
import tarfile
import logging
from enum import Enum
from typing import cast
import docker
from docker.models.containers import Container


logger = logging.getLogger(__name__)


class Status(Enum):
    """Enum for the status of a container"""
    UNDEFINED = "undefined"
    NOTFOUND = "not found"
    PAUSED = "paused"
    RESTARTING = "restarting"
    EXITED = "exited"
    RUNNING = "running"


class Containers:
    """Class for handling docker containers, as well as format the parameters for them"""

    ID_PREFIX = "openssh-server"

    def __init__(self):
        self._client = docker.from_env()
        self._client.images.pull('ghcr.io/linuxserver/openssh-server:latest')
        self._client.images.build(path="backend", dockerfile="Dockerfile", tag="target-container")

    def _get_container(self, container_id: str) -> Container:
        return cast(Container, self._client.containers.get(container_id))

    def create_container(self, config: dict):
        """Creates a docker container with the specified container_id, exposes the specified SSH port,
           and has SSH login credentials user/password

        :param config: Dictionary, preferrably formatted using format_config,
        containing all environment variables and config needed for setting up a container.
        """

        container = cast(Container, self._client.containers.create(
            config["Image"],
            environment=config["Environment"],
            hostname=config["Hostname"],
            name=config["ID"],
            ports=config["Port"],
            volumes=config["Volumes"]))

        self.copy_init_to_volume(config["ID"])
        container.start()

        # reload to get the correct port in config
        container.reload()

        logger.info("Started container %s, waiting for it to be ready...", config["ID"])

        # Wait for container SSH-server to be ready
        while True:
            exit_code, _ = container.exec_run(
                '/bin/bash -c "$(s6-svstat -u /run/s6/services/openssh-server) || exit 1"',
                stdout=False, stderr=False)
            if exit_code == 0:
                break

        logger.info("Container %s ready", config["ID"])

    def get_container_port(self, container_id: str) -> int:
        """Returns the port bound to a container. Undefined if multiple ports are used.

        :param container_id: The container id
        :return: The port bound to container container_id
        """
        return int(self._client.containers.get(container_id).attrs["NetworkSettings"]["Ports"][
            "2222/tcp"][0]["HostPort"])

    def stop_container(self, container_id: str):
        """Stop a specified container

        :param container_id: ID (name) of container to be stopped
        """
        self._get_container(container_id).stop()
        logger.info("Stopped container %s", container_id)

    def destroy_container(self, container_id: str):
        """Destroy a specified container

        :param container_id: ID (name) of container to be destroyed
        """
        self._get_container(container_id).remove()
        logger.info("Destroyed container %s", container_id)

    def prune_volumes(self):
        """Removes storage volumes for all inactive (destroyed) containers

        :param container_id: ID (name) of which container's storage directory to remove
        """
        self._client.volumes.prune()
        logger.info("Pruned all unused volumes")

    def get_volume(self, volume_id: str):
        """Returns the specified volume in form <Volume: short_id>,
        where short_id is the volume id truncated to 10 characters

        :param volume_id: The name of the volume
        """
        return self._client.volumes.get(volume_id)

    def status_container(self, container_id: str) -> Status:
        """Return the status of a specific container with the container_id argument

        :param container_id: ID (name) of container
        :return: Returns an enum describing the status of a container
        """
        try:
            sts = self._client.containers.get(container_id).attrs['State']['Status']
        except Exception:
            return Status.NOTFOUND
        else:
            if sts == "running":
                return Status.RUNNING
            elif sts == "restarting":
                return Status.RESTARTING
            elif sts == "paused":
                return Status.PAUSED
            elif sts == "exited":
                return Status.EXITED
        return Status.UNDEFINED

    def format_config(self, container_id: int, user: str, password: str,
                      hostname='Dell-T140', user_id='1000', group_id='1000',
                      timezone='Europe/London', sudo_access='true',
                      image='target-container', port=None) -> dict:
        """Formats the given parameters as a dictionary that fits docker-py.
        Creates the volumes for the config and home dirs of the container

        :param container_id: Unique ID for container
        :param user: Username for container
        :param password: Password for container
        :param volumes: Volumes on host to mount to the container.
        :param hostname: Hostname for container, defaults to 'Dell-T140'
        :param user_id: UID for container user, defaults to '1000'
        :param group_id: GID for container user, defaults to '1000'
        :param timezone: Timezone for container, defaults to 'Europe/London'
        :param sudo_access: Sudo access for container, defaults to 'true'
        :param image: Image for container, defaults to 'ghcr.io/linuxserver/openssh-server'
        :param port: Exposed port for container, defaults to None
        :return: Dictionary that can be easily used for docker-py
        """

        # Format the container id to ID_PREFIX + id
        _container_id = Containers.ID_PREFIX + str(container_id)
        _config_path = _container_id + "config"
        _home_path = _container_id + "home"

        # Format the config dict of this container
        config = {
            'Image': image,
            'ID': _container_id,
            'Environment': self.format_environment(
                user, password, user_id, group_id, timezone, sudo_access
            ),
            'Port': {'2222/tcp': port},
            'User': user, 'Password': password,
            'Hostname': hostname,
            'UID': user_id,
            'GID': group_id,
            'Timezone': timezone,
            'SUDO': sudo_access,
            'Volumes': {
                _config_path: {'bind': '/config', 'mode': 'rw'},
                _home_path: {'bind': '/home', 'mode': 'rw'}
            },
        }
        return config

    def format_environment(
            self, user: str, password: str, user_id: str, group_id: str, timezone: str,
            sudo_access: str) -> list:
        """Formats the given parameters into a list of environment variables used by the container

        :param user: Username for container
        :param password: Password for the user inside the container
        :param user_id: User id for user inside container
        :param group_id: Group id for user inside container
        :param timezone: Timezone for the container
        :param sudo_access: Sudo access for container
        :return: List of variables used by the container
        """
        return ['PUID='+user_id, 'PGID='+group_id, 'TZ='+timezone, 'SUDO_ACCESS='+sudo_access,
                'PASSWORD_ACCESS=true', 'USER_PASSWORD='+password, 'USER_NAME='+user]

    def copy_init_to_volume(self, container_id: str):
        """Copies the init script from
            backend/custom-cont-init.d/ to the container's volume.

        :param container_id: container id to copy files to
        """

        # Creates tar archive of local directory ./custom-cont-init.d and
        # transfers it into target container at path /config
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode='w') as tar:
            tar.add('custom-cont-init.d/')
        tar_data.seek(0)
        self._get_container(container_id).put_archive('/config', tar_data)
