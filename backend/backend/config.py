"""Module wrapping environment variables for configuration."""

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# The interface and port the HTTP API should listen on
HTTP_API_BIND_ADDRESS = os.getenv('HTTP_API_BIND_ADDRESS', '0.0.0.0:80')

# The address to use when connecting to acquired target systems
TARGET_SYSTEM_ADDRESS = os.getenv('TARGET_SYSTEM_ADDRESS')
