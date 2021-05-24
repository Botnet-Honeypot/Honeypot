"""Contains class and methods used for handling docker containers"""

import threading
import tarfile
import logging
from enum import Enum
from typing import IO, Union, cast
import docker
from docker.client import DockerClient
from docker.models.containers import Container
from docker.models.volumes import Volume
from backend.io import byte_stream_from_iterable
import backend.config


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

    HOME_VOLUME_SUFFIX = 'home'

    TCPDUMP_IMAGE = 'itsthenetwork/alpine-tcpdump'  # TODO: Might want a custom image
    NETLOG_CONTAINER_SUFFIX = '_netlog'
    NETLOG_DIR = '/netlog'
    NETLOG_FILE_PATH = NETLOG_DIR + '/log.pcap'

    LABEL_ROLE = 'botnet-honeypot.role'
    ROLE_TARGET_CONTAINER = 'target-container'

    # Docker API client
    _client: DockerClient

    def __init__(self):
        self._client = docker.from_env()
        self._client.images.build(path="target-systems/ssh-server",
                                  dockerfile="Dockerfile",
                                  tag="target-container")
        self._client.images.pull(self.TCPDUMP_IMAGE)

    def _get_container(self, container_id: str) -> Container:
        return cast(Container, self._client.containers.get(container_id))

    def _get_target_container_ids(
            self,
            filters: dict[str, Union[str, list[str], int]] = {}) -> set[str]:
        filters['label'] = [f'{Containers.LABEL_ROLE}={Containers.ROLE_TARGET_CONTAINER}']
        containers = self._client.api.containers(
            all=True,
            quiet=True,
            filters=filters
        )
        return set(c['Id'] for c in containers)

    def _safely_run_container(self, *args, **kwargs) -> Container:
        """Atomically starts and runs container.
        If either fails, destroys container.
        :return: The started container.
        """
        try:
            # Label container so we know that it is a target container
            if 'labels' not in kwargs:
                kwargs['labels'] = dict()
            kwargs['labels'][Containers.LABEL_ROLE] = Containers.ROLE_TARGET_CONTAINER

            return cast(Container, self._client.containers.run(*args, **kwargs))
        except Exception:
            try:
                # Creating or running failed, so make sure container is destroyed
                self._client.api.remove_container(
                    resource_id=kwargs['name'],
                    v=True,  # Destroy volumes since they were never used
                    force=True
                )
            except docker.errors.APIError:
                pass
            raise

    def create_container(self, config: dict) -> None:
        """Creates a docker container with the specified container_id, exposes the specified SSH port,
           and has SSH login credentials user/password

        :param config: Dictionary, preferrably formatted using format_config,
        containing all environment variables and config needed for setting up a container.
        """

        container = None
        netlog_container = None
        try:
            network_id = 'bridge'
            if backend.config.ENABLE_ISOLATED_TARGET_CONTAINER_NETWORKS:
                # Setup dedicated network for target container
                self._client.networks.create(
                    name=config["ID"],
                    labels={Containers.LABEL_ROLE: Containers.ROLE_TARGET_CONTAINER}
                )
                network_id = config["ID"]

            container = self._safely_run_container(
                config["Image"],
                environment=config["Environment"],
                hostname=config["Hostname"],
                name=config["ID"],
                ports=config["Port"],
                volumes=config["Volumes"],
                network=network_id,
                detach=True)

            # Start network logging container, has to happen after
            # starting main container to allow attaching to network
            netlog_container = self._start_netlog_container(config['ID'])

            logger.info("Started container %s, waiting for it to be ready...", config["ID"])

            # Reload to get the correct port in config
            container.reload()

            # Wait for target container SSH server to be ready
            while True:
                exit_code, _ = container.exec_run(
                    '/bin/bash -c "$(s6-svstat -u /run/s6/services/openssh-server) || exit 1"',
                    stdout=False, stderr=False)
                if exit_code == 0:
                    break

            logger.info("Container %s ready", config["ID"])
        except Exception:
            if container is not None:
                container.remove(force=True)
            if netlog_container is not None:
                netlog_container.remove(force=True)
            raise

    def _start_netlog_container(self, for_container_id: str) -> Container:
        netlog_volume = for_container_id + self.NETLOG_CONTAINER_SUFFIX

        return self._safely_run_container(
            self.TCPDUMP_IMAGE,
            name=for_container_id + self.NETLOG_CONTAINER_SUFFIX,
            network_mode='container:' + for_container_id,
            volumes={
                netlog_volume: {'bind': self.NETLOG_DIR, 'mode': 'rw'}
            },
            command=['-i', 'any', '-w', self.NETLOG_FILE_PATH],
            detach=True
        )

    def get_container_netlog(self, container_id: str) -> IO[bytes]:
        """Returns byte stream of pcap file for container with the given ID.

        :param container_id: The target container to get the netlog file for.
        :raises ValueError: If container is not stopped or does not exist.
        :return: Byte stream of pcap file
        """

        if self.status_container(container_id) != Status.EXITED:
            raise ValueError(
                'Container has to be stopped (but not destroyed) before getting netlog')

        netlog_container = self._get_container(container_id + self.NETLOG_CONTAINER_SUFFIX)
        tar_chunks, fileinfo = netlog_container.get_archive(self.NETLOG_FILE_PATH)
        tar_file = byte_stream_from_iterable(tar_chunks)
        logger.debug('Reading netlog for %s: %s', container_id, fileinfo)

        # Extract netlog file stream from tar by streaming tar data
        tar = tarfile.open(fileobj=tar_file, mode='r|')
        info = tar.next()
        assert info is not None
        netlog_file = tar.extractfile(info)
        assert netlog_file is not None
        return netlog_file

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
        self._get_container(container_id).stop()
        self._get_container(container_id + self.NETLOG_CONTAINER_SUFFIX).stop()

        logger.info("Stopped container %s", container_id)

    def destroy_container(self, container_id: str) -> None:
        """Destroy a specified container

        :param container_id: ID (name) of container to be destroyed
        :raises ValueError: If container does not exist.
        """
        self._get_container(container_id).remove(force=True)
        self._get_container(container_id + self.NETLOG_CONTAINER_SUFFIX).remove(force=True)

        logger.info("Destroyed container %s", container_id)

        self._prune_target_container_networks()

    def destroy_target_containers(self):
        """Clean up any remaining, previously started, containers."""

        ids = self._get_target_container_ids()
        for container_id in ids:
            try:
                self._client.api.remove_container(
                    resource_id=container_id,
                    force=True
                )
            except docker.errors.APIError:
                pass

        self._prune_target_container_networks()

    def _prune_target_container_networks(self):
        """Removes all unused networks with target-container role."""

        try:
            result = self._client.networks.prune(
                filters={'label': f'{Containers.LABEL_ROLE}={Containers.ROLE_TARGET_CONTAINER}'}
            )
            deleted = result['NetworksDeleted']
            logger.debug('Pruned %d target container networks',
                         0 if deleted is None else len(deleted))
        except docker.errors.APIError:
            pass

    def prune_volumes(self):
        """Removes storage volumes for all inactive (destroyed) containers."""
        self._client.volumes.prune()
        logger.info("Pruned all unused volumes")

    def remove_container_volumes(self, container_id: str):
        """Removes all volumes associated with a specific
        target container.

        :param container_id: The ID of the container whose
        volumes should be removed.
        """

        self.get_volume(container_id + Containers.HOME_VOLUME_SUFFIX).remove(force=True)
        self.get_volume(container_id + Containers.NETLOG_CONTAINER_SUFFIX).remove(force=True)
        logger.debug('Removed volumes for %s', container_id)

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
        except docker.errors.NotFound:
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

    @staticmethod
    def format_config(container_id: int, user: str, password: str,
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
        :param image: Image for container, defaults to 'target-container' which is based on 'ghcr.io/linuxserver/openssh-server'
        :param port: Exposed port for container, defaults to None
        :return: Dictionary that can be easily used for docker-py
        """

        # Format the container id to ID_PREFIX + id
        _container_id = Containers.ID_PREFIX + str(container_id)
        _home_path = _container_id + Containers.HOME_VOLUME_SUFFIX

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
