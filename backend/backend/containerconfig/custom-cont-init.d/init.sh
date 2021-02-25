#!/bin/bash
# This is the init script for the container. Commands
# written here will be executed on startup, which
# we might use for configuration and installing applications.

# Username for the user to be logged in
# python may change this dynamically.
# Remember to set the same in docker-compose.yaml 
# too, otherwise it does not create login for ssh.
USERNAME=user

# Install some applications as decoy
apk add htop
#apk add lighttpd

# Start lighttpd as decoy process
#lighttpd -D -f /etc/lighttpd/lighttpd.conf &

# Creating user directory
mkdir /home/$USERNAME/
chmod 777 /home/$USERNAME/

# Change entry directory for user 
sed -i "s/\/config/\/home\/$USERNAME/" "/etc/passwd"

