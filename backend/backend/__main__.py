import backend.container as container
import time

containerHandler = container.Containers()

# Example code for showing multiple containers started and stopped
# These are the environment variables that needs to be provided to
# the container to start an instance.
# Some of these should be given by the frontend of the honeypot.
id = 0
port = 2222
user = "testuser"
password = "password"
hostname = "Dell-T140"
uid = 1000
gid = 1000
timezone = "Europe/London"
sudo = "true"


for i in range(5):
    containerHandler.create_container(
        id, port, user, password, hostname, uid, gid, timezone, sudo)
    id += 1
    port += 1

time.sleep(60)

# Close and destroy containers after 60 seconds
ID = 0
for i in range(5):
    try:
        containerHandler.stop_container(ID)
        containerHandler.destroy_container(ID)
    except:
        print("Could not find or stop the specified container, continuing anyways")
    ID += 1
