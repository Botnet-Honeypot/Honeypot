"""This module contains logic for handling the SSH server docker instances for the backend"""
import docker
import os
import shutil


class Containers:

    def __init__(self):
        self._client = docker.from_env()

    def create_container(self, id: int, port: int, user: str, password: str):
        """Creates a docker container with the specified id, exposes the specified SSH port, and has SSH login credentials user/password
        :param id: ID (name) of container
        :type id: int
        :param port: SSH port that is exposed
        :type port: int
        :param user: Username for SSH
        :type user: string
        :param password: Password for SSH
        :type password: string

        """

        self._client.containers.run("ghcr.io/linuxserver/openssh-server",
                                    environment=["PUID=1000", "PGID=1000", "TZ=Europe/London", "SUDO_ACCESS=true",
                                                 "PASSWORD_ACCESS=true", "USER_PASSWORD="+password, "USER_NAME="+user],
                                    hostname="Dell-T140", name="openssh-server" + str(id), ports={"2222/tcp": str(port)},
                                    volumes={"C:/Users/Oskar/Honeypot/backend/backend/containerconfig": {"bind": "/config", "mode": "rw"}}, detach=True)

    def stop_container(self, id: int):
        """Stop a specified container
        :param id: ID (name) of container
        :type id: int
        """
        try:
            self._client.containers.get("openssh-server"+str(id)).stop()
        except:
            raise Exception("Could not find or stop the specified container")

    def gather_file_diff(self, id: int):
        print("TODO")

    def destroy_container(self, id: int):
        """Destroy a specified container
        :param id: ID (name) of container
        :type id: int
        """
        try:
            self._client.containers.get("openssh-server"+str(id)).remove()
        except:
            raise Exception("Could not find or kill the specified container")
