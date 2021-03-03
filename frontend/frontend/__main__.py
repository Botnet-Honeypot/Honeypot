"""Entrypoint for the honeypot frontend"""
import paramiko

import frontend.protocols.ssh as ssh

if __name__ == '__main__':
    key = paramiko.RSAKey(filename="./host.key")
    s = ssh.ConnectionManager(host_key=key, port=2222)
    s.listen()
