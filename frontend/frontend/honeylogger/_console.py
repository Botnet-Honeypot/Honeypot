import hashlib
import logging
import sys
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union
from frontend.honeylogger import SSHSession

from ._types import IPAddress

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ConsoleLogSSHSession(SSHSession):
    """Implementation of honeylogger.SSHSession that merely logs actions to console"""

    source: str

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        self.source = f'{src_address}:{src_port}'
        logger.info(
            "SSH session from %s:%i to %s:%i began",
            src_address, src_port,
            dst_address, dst_port)

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

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: Union[IPv4Address, IPv6Address],
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        logger.info("[%s] Download from %s (%s) of type %s: %s",
                    self.source, source_address,
                    source_url, file_type,
                    hashlib.sha256(data).hexdigest())

    def end(self) -> None:
        logger.info("SSH session from %s ended", self.source)
