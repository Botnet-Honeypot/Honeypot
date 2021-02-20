"""Entrypoint for the honeypot frontend"""
import paramiko

from protocols.ssh import ConnectionManager

key = paramiko.RSAKey(filename="./host.key")
s = ConnectionManager(host_key=key, port=2222)
s.listen()
