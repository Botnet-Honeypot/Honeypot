import logging
import datetime
from typing import List, Optional, Set, Tuple


from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, OPEN_SUCCEEDED, )
import paramiko
from paramiko.channel import Channel

import frontend.honeylogger as logger
from frontend.config import config
from ._proxy_handler import ProxyHandler


debug_log = logging.getLogger(config.SSH_DEBUG_LOG)


class Server(paramiko.ServerInterface):
    """Server implements the ServerInterface from paramiko

    :param paramiko: The SSH server interface
    """

    def __init__(
            self, session: logger.SSHSession,
            proxy_handler: ProxyHandler,
            usernames: Optional[List[str]],
            passwords: Optional[List[str]]) -> None:
        super().__init__()
        self._usernames = usernames
        self._passwords = passwords
        self._session = session
        self._proxy_handler = proxy_handler

        # The set of channels that have successfully issued a shell or exec request
        self._channels_done: Set[int]
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
                self._session.begin_ssh_session()
                self._logging_session_started = True
            except Exception as exc:
                debug_log.exception("Failed to start the SSH logging session", exc_info=exc)
        self._last_activity = datetime.datetime.now()

    def check_auth_password(self, username: str, password: str) -> int:
        self._update_last_activity()
        self._session.log_login_attempt(username, password)
        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        self._update_last_activity()
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        self._update_last_activity()
        return 'password'

    def check_channel_request(self, kind: str, chanid: int) -> int:
        self._update_last_activity()
        debug_log.info("Attacker requested a channel with the id %s and kind %s", chanid, kind)
        if kind == "session":
            return self._proxy_handler.create_backend_connection(
                "", "") and self._proxy_handler.open_channel(
                kind, chanid)

        return OPEN_SUCCEEDED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        self._update_last_activity()
        debug_log.info("Got a shell request on channel %s", channel.chanid)
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
            debug_log.error("Failed to decode the term to utf8")
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
        debug_log.info(
            "Got env request for channel %s. name: %s value:%s", channel.chanid,
            name, value)
        return False

    def check_channel_direct_tcpip_request(
            self, chanid: int, origin: Tuple[str, int],
            destination: Tuple[str, int]) -> int:
        self._update_last_activity()
        debug_log.info(
            "Got direct tcpip request for channel %s. origin: %s destination:%s", chanid,
            origin, destination)
        return OPEN_SUCCEEDED

    def check_channel_x11_request(
            self, channel: Channel, single_connection: bool, auth_protocol: str, auth_cookie: bytes,
            screen_number: int) -> bool:
        self._update_last_activity()
        debug_log.info(
            "Got x11 request on channel %s. single_connection: %s auth_protocol: %s auth_cookie: %s screen_number: %s",
            channel.chanid, single_connection, auth_protocol, auth_cookie, screen_number)
        return False

    def check_channel_forward_agent_request(self, channel: Channel) -> bool:
        self._update_last_activity()
        debug_log.info("Got forward agent request on channel %s", channel.chanid)
        return False

    def check_port_forward_request(self, address: str, port: int) -> int:
        self._update_last_activity()
        debug_log.info("Got port forward request. Address: %s, Port: %s", address, port)
        return False
