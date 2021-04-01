"""Module for logging attacker sessions and actions.

Example Usage (SSH):
    session = begin_ssh_session(src_address=ip_address('43.56.223.156'),
                        src_port=3463,
                        dst_address=ip_address('226.64.12.2'),
                        dst_port=22)

    session.log_login_attempt('a_username', 'some_password')
    session.log_command('sudo rm -rf /')
    session.log_pty_request('xterm', 5, 20, 600, 200)
    session.end()
"""

from typing import Optional, Protocol
from abc import abstractmethod
from ._types import IPAddress
from ._postgres import PostgresLogSSHSession


__all__ = ['Session', 'SSHSession', 'create_ssh_session']


class Session(Protocol):
    """Representation of an attacker's session while being connected to the honeypot."""

    @abstractmethod
    def begin(self) -> None:
        """Begins the logging session"""
        raise NotImplementedError

    @abstractmethod
    def log_login_attempt(self, username: str, password: str) -> None:
        """Logs a new login attempt associated with the current session.

        :param username: The username used in the login attempt.
        :param password: The password used in the login attempt.
        """
        raise NotImplementedError

    @abstractmethod
    def log_command(self, input: str) -> None:
        """Logs a new command associated with the current session.

        :param input: The raw string that was input to run the command.
        """
        raise NotImplementedError

    @abstractmethod
    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        """Logs a new downloaded file associated with the current session.

        :param data: The binary contents of the downloaded file.
        :param file_type: The file type of the downloaded file. Should be a valid MIME type.
            If unknown, `application/octet-stream` should be used.
        :param source_address: The IP address of the downloaded file's source.
        :param source_url: If known, the URL where the downloaded file originated from.
        :param save_data: If true, the binary contents of the downloaded file will be saved,
            if not, only metadata is saved.
        """
        raise NotImplementedError

    @abstractmethod
    def end(self) -> None:
        """Marks the session as having ended."""
        raise NotImplementedError


class SSHSession(Session, Protocol):
    """Representation of an attacker's SSH session while being connected to the honeypot."""

    @abstractmethod
    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        """Logs an SSH pty request associated with the current session.

        :param term: ``TERM`` environment variable value (e.g. vt100).
        :param term_width_cols: Terminal width, characters (e.g. 80)
        :param term_height_rows: Terminal height, rows (e.g. 24)
        :param term_width_pixels: Terminal width, pixels (e.g. 640)
        :param term_height_pixels: Terminal height, pixels (e.g. 480)
        """
        raise NotImplementedError

    @abstractmethod
    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        """Logs a new block of output associated with the current session and SSH channel.

        :param data: The raw bytes that were output.
        :param channel: The SSH channel the data was output on.
        """
        raise NotImplementedError


def create_ssh_session(src_address: IPAddress, src_port: int,
                       dst_address: IPAddress, dst_port: int) -> SSHSession:
    """Create a new SSH logging session.

    :param src_address: The IP address of the instigating origin of the session.
    :param src_port: The port number at the instigating origin.
    :param dst_address: The public IP address of the honeypot.
    :param dst_port: The port at the honeypot.
    :return: An established SSH session.
    """

    session = PostgresLogSSHSession(src_address=src_address,
                                    src_port=src_port,
                                    dst_address=dst_address,
                                    dst_port=dst_port)
    return session
