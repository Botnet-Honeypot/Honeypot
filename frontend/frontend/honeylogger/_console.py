import hashlib
import logging
import sys
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union

from ._types import IPAddress
from frontend.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Enable more logging to file
if config.SSH_ENABLE_DEBUG_LOGGING:
    fh = logging.FileHandler(config.SSH_LOG_FILE, encoding="UTF-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)


class ConsoleLogSSHSession():
    """Implementation of honeylogger.SSHSession that merely logs actions to console"""

    source: str
    src_address: str
    src_port: int
    dst_address: str
    dst_port: int

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        self.source = f'{src_address}:{src_port}'
        self.src_address = str(src_address)
        self.src_port = src_port
        self.dst_address = str(dst_address)
        self.dst_port = dst_port

    def begin_ssh_session(self) -> None:
        logger.info(
            "SSH session from %s:%i to %s:%i began",
            self.src_address, self.src_port,
            self.dst_address, self.dst_port)

    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        logger.info("[%s] SSH PTY request: %s (%ix%i cols/rows, %ix%i pixels)",
                    self.source, term,
                    term_width_cols, term_height_rows,
                    term_width_pixels, term_height_pixels)

    def log_login_attempt(self, username: str, password: str) -> None:
        logger.info("[%s] Login attempt: %s/%s",
                    self.source, username, password)

    def log_command(self, input: str) -> None:
        logger.info("[%s] Command: %s",
                    self.source, input)

    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        return
        logger.info("[%s] Output recieved on channel %d",
                    self.source, channel)

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        logger.info("[%s] Download from %s (%s) of type %s: %s",
                    self.source, source_address,
                    source_url, file_type,
                    hashlib.sha256(data).hexdigest())

    def end(self) -> None:
        logger.info("SSH session from %s ended", self.source)
