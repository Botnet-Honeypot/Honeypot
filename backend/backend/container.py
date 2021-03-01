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
        Containers.create_shared_folder(self, id, user)
        # Current path of system running
        current_path = os.getcwd() + "\\"
        # Start container using specified arguments
        self._client.containers.run("ghcr.io/linuxserver/openssh-server",
                                    environment=["PUID=1000", "PGID=1000", "TZ=Europe/London", "SUDO_ACCESS=true",
                                                 "PASSWORD_ACCESS=true", "USER_PASSWORD="+password, "USER_NAME="+user],
                                    hostname="Dell-T140", name="openssh-server" + str(id), ports={"2222/tcp": str(port)},
                                    volumes={current_path + str(id): {"bind": "/config", "mode": "rw"}}, detach=True)

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

    def create_shared_folder(self, id: int, user: str):
        """Creates a directory for the docker container with the specified id, exposes the specified SSH port, and has SSH login credentials user/password. 
           Inside it creates a script for initialization that uses the specified username for the home directory.
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
        original_dir = os.getcwd()

        # Create folder structure, add file with contents
        os.mkdir(str(id))
        os.chdir(str(id))
        os.mkdir("custom-cont-init.d")
        os.chdir("custom-cont-init.d")
        file = open("init.sh", "w", newline='\n')
        file.write("""#!/bin/bash 
        USERNAME=""" + user + """  
        apk add htop  
        mkdir /home/$USERNAME/ 
        chmod 777 /home/$USERNAME/ 
        sed -i "s/\/config/\/home\/$USERNAME/" "/etc/passwd" """)

        # Close file
        file.close()
        # Restore original working dir
        os.chdir(original_dir)
