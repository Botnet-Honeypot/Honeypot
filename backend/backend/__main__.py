#import backend.container as container
import docker
import time

client = docker.from_env()

print("Hello World")


env = ["PUID=1000", "PGID=1000", "TZ=Europe/London", "SUDO_ACCESS=true",
       "PASSWORD_ACCESS=true", "USER_PASSWORD=password", "USER_NAME=user"]

ID = "johan"
port = "2222"

client.containers.run("ghcr.io/linuxserver/openssh-server",
                      environment=["PUID=1000", "PGID=1000", "TZ=Europe/London", "SUDO_ACCESS=true",
                                   "PASSWORD_ACCESS=true", "USER_PASSWORD=password", "USER_NAME=user"], hostname="Dell-T140", name="openssh-server" + ID, ports={"2222/tcp": port}, detach=True)


time.sleep(15)

c = client.containers.get("openssh-server" + ID)


def test(input: float) -> int:
    """[summary]

    :param input: [description]
    :type input: float
    :return: [description]
    :rtype:
    """

    return 0
