import logging
from typing import Optional, Union
from ipaddress import IPv4Address, IPv6Address
import hashlib
from ._types import IPAddress


class PostgresLogSSHSession:
    """Implementation of logging.SSHSession that logs session and actions to a Postgres database"""

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        pass

    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        pass

    def log_login_attempt(self, username: str, password: str) -> None:
        pass

    def log_command(self, input: str) -> None:
        pass

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: Union[IPv4Address, IPv6Address],
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        pass

    def end(self) -> None:
        pass
