"""Module wrapping environment variables for configuration."""

import os
import re
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# To provide multiple usernames or passwords, seperate them with a ":"
# If theses are left empty, then every user and password combination is allowed
SSH_ALLOWED_USERNAMES = None if os.getenv(
    'SSH_ALLOWED_USERNAMES') is None else os.getenv('SSH_ALLOWED_USERNAMES').split(":")
SSH_ALLOWED_PASSWORDS = None if os.getenv(
    'SSH_ALLOWED_PASSWORDS') is None else os.getenv('SSH_ALLOWED_PASSWORDS').split(":")

# The port to lisen on
SSH_SERVER_PORT = int(os.getenv('SSH_SERVER_PORT', '22'))

# Success chance of login
SSH_LOGIN_SUCCESS_RATE = int(os.getenv('SSH_LOGIN_SUCCESS_RATE', '-1'))

# Regexes to deny usernamse or passwords
SSH_REGEX_USERNAMES_DENY = os.getenv('SSH_REGEX_USERNAMES_DENY')
SSH_REGEX_PASSWORDS_DENY = os.getenv('SSH_REGEX_PASSWORDS_DENY')

if SSH_REGEX_USERNAMES_DENY is not None:
    SSH_REGEX_USERNAMES_DENY = re.compile(SSH_REGEX_USERNAMES_DENY)

if SSH_REGEX_PASSWORDS_DENY is not None:
    SSH_REGEX_PASSWORDS_DENY = re.compile(SSH_REGEX_PASSWORDS_DENY)

# The local version of the SSH server
SSH_LOCAL_VERSION = os.getenv('SSH_LOCAL_VERSION', 'SSH-2.0-dropbear_2019.78')

# The timeout in seconds for which to drop an SSH session if no interaction is observed
SSH_SESSION_TIMEOUT = int(os.getenv('SSH_SESSION_TIMEOUT', '600'))

# The timeout to wait for a connectiion before throwing a timeout error
# This will cause the ConnectionManager to do another loop to make sure nobody
# wants to shut the instance down
SSH_SOCKET_TIMEOUT = float(os.getenv('SSH_SOCKET_TIMEOUT', '5'))

# Max number of qqueued connections (not that important)
SSH_MAX_UNACCEPTED_CONNECTIONS = int(os.getenv('SSH_MAX_UNACCEPTED_CONNECTIONS', '100'))

# Debug logging
ENABLE_DEBUG_LOGGING = os.getenv('ENABLE_DEBUG_LOGGING', 'False') == 'True'

# Log file
LOG_FILE = os.getenv('LOG_FILE', './honeypot.log')

# The address to a host running a server supporting the target_system_provider gRCP protocol
# Example: localhost:80
BACKEND_ADDRESS = os.getenv('BACKEND_ADDRESS')
