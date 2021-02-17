#from protocols import *

import paramiko

from protocols.ssh import SSHServer

key = paramiko.RSAKey(filename="../host.key")
s = SSHServer(host_key=key, port=2222)
s.listen()
