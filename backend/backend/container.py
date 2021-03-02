"""This module contains logic for handling the SSH server docker instances for the backend"""
import docker
import os
from string import Template


class Containers:

    def __init__(self):
        self._client = docker.from_env()

    def create_container(self, id: int, port: int, user: str, password: str, hostname: str, uid: int, gid: int, timezone: str, sudo: str):
        """Creates a docker container with the specified id, exposes the specified SSH port, and has SSH login credentials user/password
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

        Containers.create_shared_folder(self, id, user)

        # Current path of system running
        current_path = os.getcwd() + "\\"

        # Start container using specified arguments
        env = ["PUID="+str(uid), "PGID="+str(gid), "TZ="+timezone, "SUDO_ACCESS="+sudo,
               "PASSWORD_ACCESS=true", "USER_PASSWORD="+password, "USER_NAME="+user]

        self._client.containers.run("ghcr.io/linuxserver/openssh-server",
                                    environment=env,
                                    hostname=hostname, name="openssh-server"+str(id), ports={"2222/tcp": str(port)},
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

        # Template for container programs and default directory
        # This script also deletes itself and the /config/logs
        # directory from the container at the very end of execution
        scripttemplate = Template("""
                            #!/bin/bash   
                            apk add htop lighttpd perl
                            lighttpd -D -f /etc/lighttpd/lighttpd.conf &
                            $perl usr/bin/pihole-FTL 100000 &
                            $perl /sbin/init 100000 &
                            $perl /usr/sbin/lighttpd 100000 &
                            $perl /etc/lighttpd/lighttpd.conf 100000 &
                            $perl amarokapp 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /usr/lib/snapd/snapd 100000 &
                            $perl /lib/systemd/systemd-logind 100000 &
                            $perl /lib/systemd/systemd-journald 100000 &
                            $perl /lib/systemd/systemd-udevd 100000 &
                            $perl snapfuse /var/lib/snapd/snaps/ 100000 &
                            $perl snapfuse /var/lib/snapd/snaps/ 100000 &
                            $perl snapfuse /var/lib/snapd/snaps/ 100000 &
                            $perl /usr/sbin/atd -f 100000 &
                            $perl /usr/bin/php-cgi 100000 &
                            $perl /usr/bin/php-cgi 100000 &
                            $perl /usr/bin/php-cgi 100000 &
                            $perl /usr/bin/php-cgi 100000 &
                            $perl /usr/lib/policykit-l/plkitd 100000 &
                            $perl /usr/lib/policykit-l/plkitd 100000 &
                            $perl /usr/lib/policykit-l/plkitd 100000 &
                            $perl /usr/bin/python3 100000 &
                            $perl /usr/bin/python3 100000 &
                            $perl /usr/bin/python3 100000 &
                            $perl ssh:/usr/sbin/sshd 100000 &
                            $perl ssh:/usr/sbin/sshd 100000 &
                            $perl /usr/sbin/irqbalance 100000 &
                            $perl /usr/sbin/NetworkManager 100000 &
                            $perl /usr/lib/accountsservice/accounts-daemon 100000 &
                            $perl /usr/sbin/ModemManager 100000 &
                            $perl /usr/sbin/dnsmasq 100000 &
                            $perl /usr/sbin/uuidd 100000 &
                            $perl /usr/bin/perl 100000 &
                            $perl /usr/bin/perl 100000 &
                            $perl /usr/bin/perl 100000 &
                            $perl npviewer.bin 100000 &
                            $perl dbus-daemon 100000 &
                            $perl netspeed_apple 100000 &
                            mkdir /home/$username/ 
                            chmod 777 /home/$username/ 
                            sed -i "s/\/config/\/home\/$username/" "/etc/passwd" 
                            rm -rf /config/custom-cont-init.d
                            rm -rf /config/logs/
                            """)
        # Perl script contains a dollar sign, so we substitute
        # in the beginning of the script
        script = scripttemplate.substitute(
            username=user, perl="perl -wle '$0=shift;sleep shift'")
        # Create folder structure, add file with contents
        os.mkdir(str(id))
        os.chdir(str(id))
        os.mkdir("custom-cont-init.d")
        os.chdir("custom-cont-init.d")
        file = open("init.sh", "w", newline='\n')
        file.write(script)

        # Close file
        file.close()
        # Restore original working dir
        os.chdir(original_dir)
