import backend.container as container
import time

print("Hello World")

# Starting ID and port
ID = 0
Port = 2222

containerHandler = container.Containers()

# Example code for showing multiple containers started and stopped

for i in range(2):
    containerHandler.create_container(ID, Port, "user"+str(ID), "password")
    ID += 1
    Port += 1

time.sleep(10)

ID = 0
for i in range(5):
    try:
        containerHandler.stop_container(ID)
        containerHandler.destroy_container(ID)
    except:
        print("Could not find or stop the specified container, continuing anyways")
    ID += 1

print("Goodbye World")
