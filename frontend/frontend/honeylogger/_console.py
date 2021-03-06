import logging
from typing import Optional
import hashlib

from ._types import IPAddress

logger = logging.getLogger(__name__)


class ConsoleLogSSHSession():
    """Implementation of honeylogger.SSHSession that merely logs actions to console"""

    session_id = 0
    source: str
    ssh_version: str
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

    def __str__(self) -> str:
        session_id = self.session_id if self.session_id is not None else -1
        return f"[Session: {session_id}]"

    def set_remote_version(self, ssh_version: str) -> None:
        self.ssh_version = ssh_version

    def begin(self) -> None:
        self.session_id = ConsoleLogSSHSession.session_id
        ConsoleLogSSHSession.session_id += 1
        logger.info(
            "%s SSH session (Version: %s) from %s:%i to %s:%i began",
            self, self.ssh_version, self.src_address, self.src_port,
            self.dst_address, self.dst_port)

    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        logger.info("%s [%s] SSH PTY request: %s (%ix%i cols/rows, %ix%i pixels)",
                    self, self.source, term,
                    term_width_cols, term_height_rows,
                    term_width_pixels, term_height_pixels)

    def log_env_request(self, chan_id: int, name: str, value: str) -> None:
        logger.info("%s [%s] SSH ENV request on channel %s: name: %s, value: %s",
                    self, self.source, chan_id, name, value)

    def log_direct_tcpip_request(
            self, chan_id: int, origin_ip: IPAddress, origin_port: int,
            destination: str, destination_port: int) -> None:
        logger.info(
            "%s [%s] SSH Direct TCPIP request on channel %d: origin_ip: %s, origin_port: %d, destination: %s destination_port: %d",
            self, self.source, chan_id, origin_ip, origin_port, destination,
            destination_port)

    def log_x11_request(
            self, chan_id: int, single_connection: bool, auth_protocol: str,
            auth_cookie: memoryview, screen_number: int) -> None:
        logger.info(
            "%s [%s] SSH X11 request on channel %d: single_connection: %s, auth_protocol: %s, auth_cookie: %s screen_number: %d",
            self, self.source, chan_id, single_connection, auth_protocol, auth_cookie,
            screen_number)

    def log_port_forward_request(self, address: str, port: int) -> None:
        logger.info("%s [%s] SSH port forward request: address: %s, port: %d",
                    self, self.source, address, port)

    def log_login_attempt(self, username: str, password: str) -> None:
        logger.info("%s [%s] Login attempt: %s/%s",
                    self, self.source, username, password)

    def log_command(self, input: str) -> None:
        logger.info("%s [%s] Command: %s",
                    self, self.source, input)

    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        logger.info("%s [%s] Output recieved on channel %d",
                    self, self.source, channel)

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        logger.info("%s [%s] Download from %s (%s) of type %s: %s",
                    self, self.source, source_address,
                    source_url, file_type,
                    hashlib.sha256(data).hexdigest())

    def end(self) -> None:
        logger.info("%s SSH session from %s ended", self, self.source)
