"""This module contains logic for handling the SSH server docker instances for the backend"""
import backend.filehandler as filehandler
import docker
import os


class Containers:

    def __init__(self):
        self._client = docker.from_env()
        self._filehandler = filehandler.FileHandle()

    def create_container(self, id: int, port: int, user: str, password: str, hostname: str, uid: int, gid: int, timezone: str, sudo: str):
        """Creates a docker container with the specified id, exposes the specified SSH port,
           and has SSH login credentials user/password
        :param id: ID (name) of container
        :type id: int
        :param port: SSH port that is exposed
        :type port: int
        :param user: Username for SSH
        :type user: string
        :param password: Password for SSH
        :type password: string
        :param hostname: Name of the device
        :type hostname: string 
        :param uid: User ID
        :type uid: int 
        :param gid: Group ID
        :type gid: int 
        :param timezone: Timezone for container
        :type timezone: string 
        :param sudo: Sudo access, true or false as a string
        :type sudo: string 

        """

        # Creates shared folder between host and SSH server container
        Containers.create_shared_folder(self, id, user)

        # Get current dir and set paths for shared folders
        current_dir = os.getcwd()
        host_config_dir = current_dir + "/" + str(id) + "/config"
        host_home_dir = current_dir + "/" + str(id) + "/home/"

        container_name = "openssh-server"+str(id)

        # Environment variables for the container
        env = ["PUID="+str(uid), "PGID="+str(gid), "TZ="+timezone, "SUDO_ACCESS="+sudo,
               "PASSWORD_ACCESS=true", "USER_PASSWORD="+password, "USER_NAME="+user]

        # Start the container using the specified image, using the environment list and with the options specified
        self._client.containers.run("ghcr.io/linuxserver/openssh-server",
                                    environment=env,
                                    hostname=hostname, name=container_name, ports={
                                        "2222/tcp": str(port)},
                                    volumes={host_config_dir: {"bind": "/config", "mode": "rw"},
                                             host_home_dir: {"bind": "/home/", "mode": "rw"}}, detach=True)

    def stop_container(self, id: int):
        """Stop a specified container
        :param id: ID (name) of container
        :type id: int
        """
        try:
            container_name = "openssh-server"+str(id)
            self._client.containers.get(container_name).stop()
        except:
            raise Exception("Could not find or stop the specified container")

    def gather_file_diff(self, id: int):
        print("not implemented yet")

    def destroy_container(self, id: int):
        """Destroy a specified container
        :param id: ID (name) of container
        :type id: int
        """
        try:
            self._client.containers.get("openssh-server"+str(id)).remove()
        except:
            raise Exception(
                "Could not find or destroy the specified container")

    def create_shared_folder(self, id: int, user: str):
        """Creates a directory for the docker container with the specified id, 
           exposes the specified SSH port, and has SSH login credentials user/password. 
           Inside it creates a script for initialization that uses the specified username 
           for the home directory.
        :param id: ID (name) of container
        :type id: int
        :param port: SSH port that is exposed
        :type port: int
        :param user: Username for SSH
        :type user: string
        :param password: Password for SSH
        :type password: string

        """
        # Save current working directory, must be able to restore later
        current_dir = os.getcwd()

        # Makes a shared folder named with the id
        os.mkdir(str(id))

        # Paths to files needed by the container
        src = current_dir + "/template/"
        dst = current_dir + "/" + str(id)
        config_file = current_dir + "/" + \
            str(id) + "/config/custom-cont-init.d/init.sh"

        # Copy files and modify config to SSH server container
        self._filehandler.copytree(src, dst)
        self._filehandler.replaceStringInFile(config_file, "user", user)
