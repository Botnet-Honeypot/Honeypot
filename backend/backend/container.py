import subprocess

# Sketch
# ID (incrementing, unique) - Used for folder name and container name
# Port (unique) - Used to connect to via ssh
# User - Same as what the attacker used
# Password - Same as what the attacker used
#


class Containers:
    def __init__(self, ID: int, Port: int, User: str, Password: str):
        self.ID = ID
        self.Port = Port
        self.User = User
        self.Password = Password

    def create_container(self, ID: int, Port: int, User: str, Password: str):  # -> ?
        """[summary]

        :param input: [description]
        :type input: float
        :return: [description]
        :rtype:
        """

        print("container should try to start?")

        c1 = "mkdir " + str(self.ID)
        p1 = subprocess.Popen(c1.split(), stdout=subprocess.PIPE)
        c3 = "cp -r containerconfig " + str(self.ID)
        p3 = subprocess.Popen(c3.split(), stdout=subprocess.PIPE)

        print("container should have started?")

       # bash_command = 'docker run -d --name=openssh-server' + str(self.ID) + ' '\
       #     '--hostname=Dell-T140 -e PUID=1000 -e PGID=1000 -e '\
       #     'TZ=Europe/London -e SUDO_ACCESS=true -e PASSWORD_ACCESS=true '\
       #     '-e USER_PASSWORD=' + self.Password + ' -e USER_NAME=' + self.User + ' -p ' + str(self.Port) + ':2222 '\
       #     '-v /' + \
       #     str(self.ID)

        bash_command = 'docker run --detach --name=openssh-serverID --hostname=Dell-T140 --env PUID=1000 --env PGID=1000 --env TZ=Europe/London --env SUDO_ACCESS=true --env PASSWORD_ACCESS=true --env USER_PASSWORD=password --env USER_NAME=user --publish 2222:2222 ghcr.io/linuxserver/openssh-server'

        # 'docker run --detach --name=openssh-serverID --hostname=Dell-T140 --env PUID=1000 --env PGID=1000 --env TZ=Europe/London --env SUDO_ACCESS=true --env PASSWORD_ACCESS=true --env USER_PASSWORD=password --env USER_NAME=user --publish 2222:2222 ghcr.io/linuxserver/openssh-server'

        process = subprocess.Popen(
            bash_command.split(), stdout=subprocess.PIPE)
        #output, error = process.communicate()
