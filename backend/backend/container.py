"""This module contains logic for handling the SSH server docker instances for the backend"""
import os
import ast
import shutil
from enum import Enum
import docker
import backend.filehandler as filehandler


class Status(Enum):
    UNDEFINED = "undefined"
    NOTFOUND = "not found"
    PAUSED = "paused"
    RESTARTING = "restarting"
    EXITED = "exited"
    RUNNING = "running"


DICT_KEYS = ["Image", "ID", "Environment", "Port", "User", "Password",
             "Hostname", "UID", "GID", "Timezone", "SUDO", "Volumes"]


class Containers:

    def __init__(self):
        self._client = docker.from_env()
        self._filehandler = filehandler.FileHandle()

    def create_container(self, config: dict):
        """Creates a docker container with the specified container_id, exposes the specified SSH port,
           and has SSH login credentials user/password
        :param container_id: container_id (name) of container
        :type container_id: int
        :param port: SSH port that is exposed
        :type port: int
        :param user: Username for SSH
        :type user: string
        :param password: Password for SSH
        :type password: string
        :param hostname: Name of the device
        :type hostname: string
        :param uid: User container_id
        :type uid: int
        :param gid: Group container_id
        :type gid: int
        :param timezone: Timezone for container
        :type timezone: string
        :param sudo: Sudo access, true or false as a string
        :type sudo: string

        """
        # Creates shared folder between host and SSH server container
        Containers.create_shared_folder(self, config["ID"], config["User"])

        # Get current dir and set paths for shared folders
        #current_dir = os.getcwd()
        #host_config_dir = current_dir + "/" + str(container_id) + "/config"
        #host_home_dir = current_dir + "/" + str(container_id) + "/home/"

        #container_name = "openssh-server"+str(container_id)

        # Environment variables for the container
        # env = ["PUID="+str(uid), "PGID="+str(gid), "TZ="+timezone, "SUDO_ACCESS="+sudo,
        #       "PASSWORD_ACCESS=true", "USER_PASSWORD="+password, "USER_NAME="+user]

        # Start the container using the specified image,
        # using the environment list and with the options specified
        #config = self.load_config_from_file("./containerconfigs/default.txt")
        config = self.format_config("backend/containerconfigs/defaulttest.txt", config)
        try:
            self._client.containers.run(
                config["Image"],
                environment=config["Environment"],
                hostname=config["Hostname"],
                name=config["ID"],
                ports=config["Port"],
                volumes=config["Volumes"],
                detach=True)
            # self._client.containers.run(
            #    "ghcr.io/linuxserver/openssh-server", environment=env, hostname=hostname,
            #    name=container_name, ports={"2222/tcp": str(port)},
            #    volumes={host_config_dir: {"bind": "/config", "mode": "rw"},
            #             host_home_dir: {"bind": "/home/", "mode": "rw"}},
            #    detach=True)
        except Exception as e:
            raise e
        else:
            print("Successfully started container ")

    def stop_container(self, container_id: int):
        """Stop a specified container
        :param container_id: container_id (name) of container
        :type container_id: int
        """
        try:
            container_name = "openssh-server"+str(container_id)
            self._client.containers.get(container_name).stop()
        except Exception as exception:
            raise exception
        else:
            print("Stopped container " + str(container_id))

    def gather_file_diff(self, container_id: int):
        print("not implemented yet")

    def destroy_container(self, container_id: int):
        """Destroy a specified container
        :param container_id: container_id (name) of container
        :type container_id: int
        """
        try:
            container_name = "openssh-server"+str(container_id)
            self._client.containers.get(container_name).remove()
        except:
            raise Exception(
                "Could not find or destroy the specified container")

    def remove_folder(self, container_id: int):
        try:
            current_path = os.getcwd()
            shutil.rmtree(os.path.join(current_path, str(container_id)))
        except IOError as ioe:
            print(f"Failed to open file \n Error: {ioe}")
            raise

    def status_container(self, container_id: int) -> Status:
        """Return the status of a specific container with the container_id argument
        :param container_id: container_id (name) of container
        :type container_id: int
        :return: Returns an enum describing the status of a container
        :rtype: Status
        """
        try:
            container_name = "openssh-server"+str(container_id)
            sts = self._client.containers.get(
                container_name).attrs['State']['Status']
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
            else:
                return Status.UNDEFINED

    def create_shared_folder(self, container_id: int, user: str):
        """Creates a directory for the docker container with the specified container_id,
           exposes the specified SSH port, and has SSH login credentials user/password.
           Inside it creates a script for initialization that uses the specified username
           for the home directory.
        :param container_id: container_id (name) of container
        :type container_id: int
        :param port: SSH port that is exposed
        :type port: int
        :param user: Username for SSH
        :type user: string
        :param password: Password for SSH
        :type password: string

        """
        # Save current working directory, must be able to restore later
        current_dir = os.getcwd()

        # Makes a shared folder named with the container_id
        os.mkdir(str(container_id))

        # Paths to files needed by the container
        src = current_dir + "/template/"
        dst = current_dir + "/" + str(container_id)
        config_file = current_dir + "/" + \
            str(container_id) + "/config/custom-cont-init.d/init.sh"

        # Copy files and modify config to SSH server container
        self._filehandler.copytree(src, dst)
        self._filehandler.replaceStringInFile(config_file, "user", user)

    def config_as_dict(self, config_file: str) -> dict:
        # Credit https://www.geeksforgeeks.org/how-to-read-dictionary-from-file-in-python/
        with open(config_file) as file:
            return ast.literal_eval(file.read())

    def string_to_dict(self, string: str) -> dict:
        return ast.literal_eval(string)

    def replace_substring(self, substring, new_string, full_string) -> str:
        full_string = full_string.replace(substring, str(new_string))
        return full_string

    def config_as_string(self, config_to_use):
        file = open(config_to_use, "r")
        return file.read()

    def format_config(self, config_to_use: str, config_params: dict) -> dict:
        config_string = self.config_as_string(config_to_use)
        for string in DICT_KEYS:
            config_string = self.replace_substring(
                "@" + string, config_params[string],
                config_string)
        return self.string_to_dict(config_string)
