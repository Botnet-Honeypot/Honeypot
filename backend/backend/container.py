"""Contains class and methods used for handling docker containers"""

import io
import threading
import tarfile
import logging
from enum import Enum
from typing import cast
import docker
from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.volumes import Volume


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

    NETLOG_CONTAINER_SUFFIX = '_netlog'
    TCPDUMP_IMAGE = 'itsthenetwork/alpine-tcpdump'  # TODO: Might want a custom image

    # Docker API client
    _client: DockerClient

    # All containers which have successfully been started and not yet destroyed
    # Must be accessed under lock
    _containers: set[str]
    _containers_lock: threading.RLock

    def __init__(self):
        self._client = docker.from_env()
        self._client.images.pull('ghcr.io/linuxserver/openssh-server:latest')
        self._client.images.pull(self.TCPDUMP_IMAGE)

        self._containers = set()
        self._containers_lock = threading.RLock()

    def _get_container(self, container_id: str) -> Container:
        with self._containers_lock:
            if container_id not in self._containers:
                raise ValueError(f'Container with ID {container_id} does not exist')
            return cast(Container, self._client.containers.get(container_id))

    def _get_container_unchecked(self, container_id: str) -> Container:
        return cast(Container, self._client.containers.get(container_id))

    def create_container(self, config: dict) -> None:
        """Creates a docker container with the specified container_id, exposes the specified SSH port,
           and has SSH login credentials user/password

        :param config: Dictionary, preferrably formatted using format_config,
        containing all environment variables and config needed for setting up a container.
        """

        with self._containers_lock:
            if config['ID'] in self._containers:
                raise ValueError(f'Container ID {config["ID"]} is already in use')
            self._containers.add(config['ID'])

        container = None
        netlog_container = None
        try:
            container = cast(Container, self._client.containers.create(
                config["Image"],
                environment=config["Environment"],
                hostname=config["Hostname"],
                name=config["ID"],
                ports=config["Port"],
                volumes=config["Volumes"]))

            self._copy_init_to_volume(config["ID"])
            container.start()

            # Start network logging container, has to happen after
            # starting main container to allow attaching to network
            netlog_container = self._start_netlog_container(config['ID'])

            logger.info("Started container %s, waiting for it to be ready...", config["ID"])

            # Reload to get the correct port in config
            container.reload()

            # Wait for target container SSH-server to be ready
            while True:
                exit_code, _ = container.exec_run(
                    '/bin/bash -c "$(s6-svstat -u /run/s6/services/openssh-server) || exit 1"',
                    stdout=False, stderr=False)
                if exit_code == 0:
                    break

            logger.info("Container %s ready", config["ID"])
        except Exception:
            with self._containers_lock:
                self._containers.remove(config['ID'])
            if container is not None:
                container.remove(force=True)
            if netlog_container is not None:
                netlog_container.remove(force=True)
            raise

    def _start_netlog_container(self, for_container_id: str) -> Container:
        netlog_volume = for_container_id + self.NETLOG_CONTAINER_SUFFIX
        netlog_dir = '/netlog'
        return cast(Container, self._client.containers.run(
            self.TCPDUMP_IMAGE,
            name=for_container_id + self.NETLOG_CONTAINER_SUFFIX,
            network_mode='container:' + for_container_id,
            volumes={
                netlog_volume: {'bind': netlog_dir, 'mode': 'rw'}
            },
            command=['-i', 'any', '-w', netlog_dir + '/log.pcap'],
            detach=True
        ))

    def get_container_port(self, container_id: str) -> int:
        """Returns the port bound to a container. Undefined if multiple ports are used.

        :param container_id: The container id
        :return: The port bound to container container_id
        """
        return int(self._get_container(container_id).attrs["NetworkSettings"]["Ports"][
            "2222/tcp"][0]["HostPort"])

    def stop_container(self, container_id: str) -> None:
        """Stop a specified container

        :param container_id: ID (name) of container to be stopped
        """
        with self._containers_lock:
            self._get_container(container_id).stop()
            self._get_container_unchecked(container_id + self.NETLOG_CONTAINER_SUFFIX).stop()

        logger.info("Stopped container %s", container_id)

    def destroy_container(self, container_id: str) -> None:
        """Destroy a specified container

        :param container_id: ID (name) of container to be destroyed
        """
        with self._containers_lock:
            container = self._get_container(container_id)
            self._containers.remove(container_id)
            container.remove(force=True)
            self._get_container_unchecked(
                container_id + self.NETLOG_CONTAINER_SUFFIX).remove(force=True)

        logger.info("Destroyed container %s", container_id)

    def prune_volumes(self):
        """Removes storage volumes for all inactive (destroyed) containers

        :param container_id: ID (name) of which container's storage directory to remove
        """
        self._client.volumes.prune()
        logger.info("Pruned all unused volumes")

    def get_volume(self, volume_id: str) -> Volume:
        """Returns the specified volume in form <Volume: short_id>,
        where short_id is the volume id truncated to 10 characters

        :param volume_id: The name of the volume
        """
        return cast(Volume, self._client.volumes.get(volume_id))

    def status_container(self, container_id: str) -> Status:
        """Return the status of a specific container with the container_id argument

        :param container_id: ID (name) of container
        :return: Returns an enum describing the status of a container
        """
        try:
            sts = self._get_container(container_id).attrs['State']['Status']
        except ValueError:
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

    def shutdown(self):
        """Clean up any remaining, previously started, containers."""

        with self._containers_lock:
            for container_id in self._containers.copy():
                self.destroy_container(container_id)

    @staticmethod
    def format_config(container_id: int, user: str, password: str,
                      hostname='Dell-T140', user_id='1000', group_id='1000',
                      timezone='Europe/London', sudo_access='true',
                      image='ghcr.io/linuxserver/openssh-server', port=None) -> dict:
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
            'Environment': Containers._format_environment(
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

    @staticmethod
    def _format_environment(user: str, password: str,
                            user_id: str, group_id: str,
                            timezone: str,
                            sudo_access: str) -> list[str]:
        """Formats the given parameters into a list of environment variables used by the container

        :param user: Username for container
        :param password: Password for the user inside the container
        :param user_id: User id for user inside container
        :param group_id: Group id for user inside container
        :param timezone: Timezone for the container
        :param sudo_access: Sudo access for container
        :return: List of variables used by the container
        """
        return [
            'PUID=' + user_id,
            'PGID=' + group_id,
            'TZ=' + timezone,
            'SUDO_ACCESS=' + sudo_access,
            'PASSWORD_ACCESS=true',
            'USER_PASSWORD=' + password,
            'USER_NAME=' + user
        ]

    def _copy_init_to_volume(self, container_id: str):
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
