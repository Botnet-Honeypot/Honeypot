import logging
import random
import datetime
import time
from typing import List, Optional, Set


from paramiko.common import (AUTH_FAILED, AUTH_SUCCESSFUL,
                             OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, )
import paramiko
from paramiko.channel import Channel

import frontend.honeylogger as logger
from frontend.protocols.proxy_handler import ProxyHandler


debug_log = logging.getLogger("debuglogger")


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
        self._count = 0  # todo remove

        self._last_activity = datetime.datetime.now()

    def get_last_activity(self) -> datetime.datetime:
        """Get the datetime of the last activity

        :return: datetime of the last activity
        """
        return self._last_activity

    def _update_last_activity(self) -> None:
        """Updates the last activity seen
        """
        self._last_activity = datetime.datetime.now()

    def check_auth_password(self, username: str, password: str) -> int:
        self._update_last_activity()
        self._session.log_login_attempt(username, password)
        self._count += 1
        r = random.randint(2, 8)
        if self._count < 3:
            # debug_log.info(
            #     "[AUTH] Sleeping %s seconds and denying, hopefully we see another login", r)
            debug_log.info("[AUTH] Denying, hopefully we see another login")
            # time.sleep(r)
            return AUTH_FAILED
        else:
            debug_log.info(
                "[AUTH] Sleeping %s seconds and accepting, hopefully we see a shell/exec attempt",
                r)
            time.sleep(r)
            return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username: str, key: paramiko.PKey) -> int:
        self._update_last_activity()
        return AUTH_FAILED

    def get_allowed_auths(self, username: str) -> str:
        self._update_last_activity()
        return 'password'

    def check_channel_request(self, kind: str, chanid: int) -> int:
        self._update_last_activity()
        if kind == "session":
            return self._proxy_handler.open_channel(kind, chanid)

        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel: paramiko.Channel) -> bool:
        self._update_last_activity()
        debug_log.info("Wow this is rare, we got a shell request")
        if channel.chanid in self._channels_done or not self._proxy_handler.handle_shell_request(
                channel):
            return False
        self._channels_done.add(channel.chanid)
        return True

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        self._update_last_activity()
        r = random.randint(2, 8)
        debug_log.info(
            "[CHANNEL] Sleeping %s seconds and then running, hopefully we see another shell/exec attempt",
            r)
        time.sleep(r)
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
