"""Module wrapping environment variables for configuration."""

import logging
import os
import sys
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

SSH_DEBUG_LOG = "ssh_debug_log"


# To provide multiple usernames or passwords, seperate them with a ":"
# If theses are left empty, then every user and password combination is allowed
SSH_ALLOWED_USERNAMES = os.getenv('SSH_ALLOWED_USERNAMES', '').split(":")
SSH_ALLOWED_PASSWORDS = os.getenv('SSH_ALLOWED_PASSWORDS', '').split(":")

# The port to lisen on
SSH_SERVER_PORT = int(os.getenv('SSH_SERVER_PORT', '22'))

# The local version of the SSH server
SSH_LOCAL_VERSION = os.getenv('SSH_LOCAL_VERSION ', 'SSH-2.0-dropbear_2019.78')

# The timeout in seconds for which to drop an SSH session if no interaction is observed
SSH_SESSION_TIMEOUT = int(os.getenv('SSH_SERVER_PORT', '600'))

# The timeout to wait for a connectiion before throwing a timeout error
# This will cause the ConnectionManager to do another loop to make sure nobody
# wants to shut the instance down
SSH_SOCKET_TIMEOUT = float(os.getenv('SSH_SOCKET_TIMEOUT', '5'))

# Max number of qqueued connections (not that important)
SSH_MAX_UNACCEPTED_CONNECTIONS = int(os.getenv('SSH_MAX_UNACCEPTED_CONNECTIONS', '100'))

# Debug logging
SSH_ENABLE_DEBUG_LOGGING = bool(os.getenv('ENABLE_DEBUG_LOGGING', 'False'))

# Log file for SSH if debug logging is enabled
SSH_LOG_FILE = os.getenv('SSH_LOG_FILE', './honeypot.log')

BACKEND_IP = os.getenv('BACKEND_IP')

# Set up logging
if SSH_ENABLE_DEBUG_LOGGING:
    debug_log = logging.getLogger(SSH_DEBUG_LOG)
    debug_log.setLevel(logging.DEBUG)
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh = logging.FileHandler(SSH_LOG_FILE, encoding="UTF-8")
    log_handler.setFormatter(formatter)
    fh.setFormatter(formatter)
    debug_log.addHandler(log_handler)
    debug_log.addHandler(fh)
