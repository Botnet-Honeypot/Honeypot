"""Module wrapping environment variables for configuration."""

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# The interface and port the HTTP API should listen on
HTTP_API_BIND_ADDRESS = os.getenv('HTTP_API_BIND_ADDRESS', '0.0.0.0:80')

# The address to use when connecting to acquired target systems
TARGET_SYSTEM_ADDRESS = os.getenv('TARGET_SYSTEM_ADDRESS')

# If enabled, uses creates a unique Docker network per target container
# to isolate containers from eachother and reduce amount of redundant
# captured network traffic.
ENABLE_ISOLATED_TARGET_CONTAINER_NETWORKS = os.getenv(
    'ENABLE_ISOLATED_TARGET_CONTAINER_NETWORKS', 'False') == 'True'

# If enabled, volumes belonging to a target system are not
# removed after the target system is shut down
KEEP_TARGET_SYSTEM_VOLUMES = os.getenv(
    'KEEP_TARGET_SYSTEM_VOLUMES', 'False') == 'True'
