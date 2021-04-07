FROM ghcr.io/linuxserver/openssh-server 

RUN apk add htop perl

# Copy runtime initialization script
COPY custom-cont-init.d /config/custom-cont-init.d