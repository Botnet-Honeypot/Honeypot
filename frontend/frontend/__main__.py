"""Entrypoint for the honeypot frontend"""
import paramiko

from frontend.protocols.ssh import ConnectionManager as SSHConnectionManager
from frontend.config import config

if __name__ == '__main__':
    key = paramiko.RSAKey(filename="./host.key")
    s = SSHConnectionManager(host_key=key, port=config.SSH_SERVER_PORT,
                             socket_timeout=config.SSH_SOCKET_TIMEOUT,
                             max_unaccepted_connetions=config.SSH_MAX_UNACCEPTED_CONNECTIONS,
                             usernames=config.SSH_ALLOWED_USERNAMES,
                             passwords=config.SSH_ALLOWED_PASSWORDS)
    s.start()
    s.join()
