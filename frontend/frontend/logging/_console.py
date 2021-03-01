import logging
from typing import Optional, Union
from ipaddress import IPv4Address, IPv6Address
import hashlib
from ._types import IPAddress

logger = logging.getLogger(__name__)


class SSHSession:
    """Implementation of logging.Session that merely logs actions to console"""

    source: str

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int,
                 term: str) -> None:
        self.source = f'{src_address}:{src_port}'
        logger.info(
            "SSH session from %s:%i to %s:%i begun (term: %s)",
            src_address, src_port,
            dst_address, dst_port,
            term)

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
