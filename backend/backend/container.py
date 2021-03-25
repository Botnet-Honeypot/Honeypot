"""Contains class and methods used for handling docker containers

    :raises exception: May raise exceptions on IOError (when appropriate) and Docker api failure
    :return: Returns a container handler that can start, stop, destroy containers as well as manage storage
    """
import os
import shutil
from enum import Enum
import docker
import backend.filehandler as filehandler


class Status(Enum):
    """Enum for the status of a container
    """
    UNDEFINED = "undefined"
    NOTFOUND = "not found"
    PAUSED = "paused"
    RESTARTING = "restarting"
    EXITED = "exited"
    RUNNING = "running"


class Containers:
    """Class for handling docker containers, as well as format the parameters for them
    """
    ID_PREFIX = "openssh-server"

    def __init__(self):
        self._client = docker.from_env()
        self._filehandler = filehandler.FileHandle()

    def create_container(self, config: dict):
        """Creates a docker container with the specified container_id, exposes the specified SSH port,
           and has SSH login credentials user/password

        :param config: Dictionary, preferrably formatted using format_config,
        containing all environment variables and config needed for setting up a container.
        """
        # Creates shared folder between host and SSH server container
        Containers.create_shared_folder(self, config["ID"], config["User"])

        try:
            self._client.containers.run(
                config["Image"],
                environment=config["Environment"],
                hostname=config["Hostname"],
                name=config["ID"],
                ports=config["Port"],
                volumes=config["Volumes"],
                detach=True)
        except Exception as exception:
            raise exception
        else:
            print("Successfully started container ")

    def stop_container(self, container_id: str):
        """Stop a specified container

        :param container_id: ID (name) of container to be stopped
        """
        try:
            self._client.containers.get(container_id).stop()
        except Exception as exception:
            raise exception
        else:
            print("Stopped container " + str(container_id))

    def destroy_container(self, container_id: str):
        """Destroy a specified container

        :param container_id: ID (name) of container to be destroyed
        """
        try:
            self._client.containers.get(container_id).remove()
        except Exception as exception:
            raise exception

    def remove_folder(self, container_id: str):
        """Removes storage folder for the specified container

        :param container_id: ID (name) of which container's storage directory to remove
        """
        try:
            current_path = os.getcwd()
            shutil.rmtree(os.path.join(current_path, container_id))
        except IOError as exception:
            print(f"Failed to open file \n Error: {exception}")
            raise exception

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
            elif sts == "exited":
                return Status.EXITED
            elif sts == "restarting":
                return Status.RESTARTING
            elif sts == "paused":
                return Status.PAUSED
        return Status.UNDEFINED

    def create_shared_folder(self, container_id: str, user: str):
        """Creates a directory for the docker container with the specified container_id,
           exposes the specified SSH port, and has SSH login credentials user/password.
           Inside it creates a script for initialization that uses the specified username
           for the home directory

        :param container_id: ID (name) of container
        :param port: SSH port that is exposed
        :param user: Username for SSH
        :param password: Password for SSH
        """
        # Save current working directory, must be able to restore later
        current_dir = os.getcwd()

        # Makes a shared folder named with the container_id
        os.mkdir(container_id)

        # Paths to files needed by the container
        src = current_dir + "/template/"
        dst = current_dir + "/" + container_id
        config_file = current_dir + "/" + container_id + "/config/custom-cont-init.d/init.sh"

        # Copy files and modify config to SSH server container
        self._filehandler.copytree(src, dst)
        self._filehandler.replaceStringInFile(config_file, "user", user)

    def format_config(
            self, container_id: int, port: int, user: str, password: str, volumes: dict,
            hostname='Dell-T140', user_id='1000', group_id='1000', timezone='Europe/London',
            sudo_access='true', image='ghcr.io/linuxserver/openssh-server') -> dict:
        """Formats the given parameters as a dictionary that fits docker-py

        :param container_id: Unique ID for container
        :param port: Unique external port for container
        :param user: Username for container
        :param password: Password for container
        :param volumes: Volumes on host to mount to the container.
        :param hostname: Hostname for container, defaults to 'Dell-T140'
        :param user_id: UID for container user, defaults to '1000'
        :param group_id: GID for container user, defaults to '1000'
        :param timezone: Timezone for container, defaults to 'Europe/London'
        :param sudo_access: Sudo access for container, defaults to 'true'
        :param image: Image for container, defaults to 'ghcr.io/linuxserver/openssh-server'
        :return: Dictionary that can be easily used for docker-py
        """

        config = {
            'Image': image, 'ID': Containers.ID_PREFIX + str(container_id),
            'Environment': self.format_environment(
                user, password, user_id, group_id, timezone, sudo_access),
            'Port': {'2222/tcp': str(port)},
            'User': user, 'Password': password, 'Hostname': hostname, 'UID': user_id, 'GID': group_id,
            'Timezone': timezone, 'SUDO': sudo_access, 'Volumes': volumes}
        return config

    def format_environment(
            self, user: str, password: str, user_id: str, group_id: str, timezone: str,
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
        return ['PUID='+user_id, 'PGID='+group_id, 'TZ='+timezone, 'SUDO_ACCESS='+sudo_access,
                'PASSWORD_ACCESS=true', 'USER_PASSWORD='+password, 'USER_NAME='+user]
