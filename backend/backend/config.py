"""Module wrapping environment variables for configuration."""

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


HTTP_API_BIND_ADDRESS = os.getenv('HTTP_API_BIND_ADDRESS', '0.0.0.0:80')
