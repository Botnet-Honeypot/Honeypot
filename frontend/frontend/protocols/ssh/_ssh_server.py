from ipaddress import AddressValueError, IPv4Address
import logging
import datetime
from typing import List, Optional, Set, Tuple

from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL, OPEN_SUCCEEDED)
import paramiko
from paramiko.channel import Channel

from frontend.honeylogger import SSHSession
from ._proxy_handler import ProxyHandler


logger = logging.getLogger(__name__)


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    """

    # The set of channels that have successfully issued a shell or exec request
    _channels_done: Set[int]

    def __init__(
            self, session: SSHSession,
            proxy_handler: ProxyHandler,
            usernames: Optional[List[str]],
            passwords: Optional[List[str]]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords
        self._session = session
        self._proxy_handler = proxy_handler

        self._channels_done = set()

        self._last_activity = datetime.datetime.now()
        self._logging_session_started = False

    def get_last_activity(self) -> datetime.datetime:
        """Get the datetime of the last activity

        :return: datetime of the last activity
        """
        return self._last_activity

    def _update_last_activity(self) -> None:
        """Updates the last activity seen
        """
        # Make sure to start the logging session if it isn't started
        if not self._logging_session_started:
            try:
                self._session.begin()
                self._logging_session_started = True
            except Exception:
                logger.exception("Failed to start the SSH logging session")
        self._last_activity = datetime.datetime.now()

    def check_auth_password(self, username: str, password: str) -> int:
        self._update_last_activity()
        self._session.log_login_attempt(username, password)
        if self._usernames is not None and not username in self._usernames:
            return AUTH_FAILED
        if self._passwords is None or password in self._passwords:
            return AUTH_SUCCESSFUL
        return AUTH_FAILED

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        self._update_last_activity()
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        self._update_last_activity()
        return 'password'

    def check_channel_request(self, kind: str, chanid: int) -> int:
        self._update_last_activity()
        logger.info("Attacker requested a channel with the id %s and kind %s", chanid, kind)
        if kind == "session":
            return self._proxy_handler.create_backend_connection(
                "", "") and self._proxy_handler.open_channel(
                kind, chanid)

        return OPEN_SUCCEEDED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        self._update_last_activity()
        logger.info("Got a shell request on channel %s", channel.chanid)
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_shell_request(
                channel):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        self._update_last_activity()
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_exec_request(
                channel, command):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_pty_request(self, channel: paramiko.Channel, term: bytes,
                                  width: int, height: int, pixelwidth: int,
                                  pixelheight: int, _: bytes) -> bool:
        self._update_last_activity()
        try:
            term_string = term.decode("utf-8")
            self._session.log_pty_request(term_string, width, height, pixelwidth, pixelheight)
        except UnicodeError:
            logger.exception("Failed to decode the term to utf8")
            return False

        return self._proxy_handler.handle_pty_request(
            channel, term_string, width, height, pixelwidth, pixelheight)

    def check_channel_window_change_request(self, channel: Channel, width: int, height: int,
                                            pixelwidth: int, pixelheight: int) -> bool:
        self._update_last_activity()
        return self._proxy_handler.handle_window_change_request(
            channel, width, height, pixelwidth, pixelheight)

    def check_channel_env_request(self, channel: Channel, name: str, value: str) -> bool:
        self._update_last_activity()
        self._session.log_env_request(channel.chanid, name, value)
        return False

    def check_channel_direct_tcpip_request(
            self, chanid: int, origin: Tuple[str, int],
            destination: Tuple[str, int]) -> int:
        self._update_last_activity()
        try:
            ip = IPv4Address(origin[0])
            self._session.log_direct_tcpip_request(
                chanid, ip, origin[1],
                destination[0],
                destination[1])
        except AddressValueError:
            pass
        return OPEN_SUCCEEDED

    def check_channel_x11_request(
            self, channel: Channel, single_connection: bool, auth_protocol: str, auth_cookie: bytes,
            screen_number: int) -> bool:
        self._update_last_activity()
        self._session.log_x11_request(channel.chanid, single_connection,
                                      auth_protocol, memoryview(auth_cookie), screen_number)
        return False

    def check_channel_forward_agent_request(self, channel: Channel) -> bool:
        self._update_last_activity()
        logger.info("Got forward agent request on channel %s", channel.chanid)
        return False

    def check_port_forward_request(self, address: str, port: int) -> int:
        self._update_last_activity()
        self._session.log_port_forward_request(address, port)
        return False
