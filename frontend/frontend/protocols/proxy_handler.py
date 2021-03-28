"""This file contains the ProxyHandler class which can be used to
proxy data between the backend and log commands recieved from the attacker and
all the data recieved from the backend during the sesison.
"""
import logging
import socket
import threading
from time import sleep
from typing import Callable, List

import paramiko
from paramiko import SSHException
from paramiko.transport import Transport
from paramiko.channel import Channel
from paramiko.common import (OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, OPEN_SUCCEEDED)

from frontend.honeylogger import SSHSession


debug_log = logging.getLogger("debuglogger")


class ProxyHandler:
    """This class is responsible for proxying information from recieved attacker SSH channels
    to corresponding backend channels
    """

    def __init__(self, session_log: SSHSession) -> None:
        # This is the SSH transport to the backend
        self._backend_transport: Transport
        # This is the dict mapping the attacker channel ID's to a proxy channel to the backend
        self._backend_chan_proxies: dict[int, Channel]
        self._backend_chan_proxies = dict()

        # This is the session log we can log things to
        self._session_log: SSHSession
        self._session_log = session_log

        self._backend_connection_active = False

    def _open_proxy_transport(self, ip: str, port: int, username: str, password: str) -> None:
        # Here we need to open a SSH connection to the backend
        # This will be done with our backend API later
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, port=port, username=username, password=password)
        except Exception as exc:
            debug_log.exception("Failed to connect SSH proxy %s:%i with %s/%s",
                                ip, port, username, password, exc_info=exc)
            return

        transport = client.get_transport()
        if transport is not None:
            self._backend_connection_active = True
            self._backend_transport = transport
        else:
            debug_log.error("Failed to obtain transport for dozy")

    def _get_corresponding_backend_channel(self, attacker_chan_id: int) -> paramiko.Channel:
        """Retrieves the corresponding backend channel that is related to the attacker channel

        :param attacker_chan_id: The attacker channel id
        :raises ValueError: If the corresponding backend channel does not exist
        :return: The corresponding backend channel
        """
        chan = self._backend_chan_proxies[attacker_chan_id]
        if chan is None:
            debug_log.error(
                "Failed to obtain a backend channel correspoding to the attacker channel %s",
                attacker_chan_id)
            print("This should not happen since a attacker channel id should ", end="")
            print("always be related to a backend channel")
            raise ValueError
        return chan

    def close_connection(self) -> None:
        """This closes the backend connection and ends the session
        """
        if not self._backend_connection_active:
            return
        # Close the backend connection
        try:
            self._backend_transport.close()
        except Exception as exc:
            debug_log.exception("Failed to backend transport", exc_info=exc)
        self._session_log.end()

    def create_backend_connection(self, username: str, password: str) -> bool:
        """Sets up the a SSH connection to the backend with the given username

        :param username: The username to use in the container
        :return: True if the connection was successful
        """
        # todo we don't use the api currently
        if not self._backend_connection_active:
            # Open the backend transport
            self._open_proxy_transport("40.127.101.181", port=22,
                                       username="john", password="Superman1234")
        return self._backend_connection_active

    def open_channel(self, kind: str, chanid: int) -> int:
        """Tries to open a channel to the backend

        :param kind: The channel kind
        :param chanid: The channel id of the channel that the attacker requested
        :return: An int given by paramiko
        """
        try:
            chan = self._backend_transport.open_channel(kind)
        except SSHException:
            debug_log.error("Failed to open a new channel with kind %s on the backend", kind)
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        debug_log.info("Attacker opening channel %s", chanid)
        # Save the opened channel in our dict
        self._backend_chan_proxies[chanid] = chan
        return OPEN_SUCCEEDED

    def handle_shell_request(self, attacker_channel: paramiko.Channel):
        """Tries to send a shell request to the corresponding backend channel.
        If the shell request succeeds data will be proxied between the two channels

        :param attacker_channel: The attacker channel
        :return: True if we managed to send a shell request to the backend channel
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            backend_channel.invoke_shell()
        except SSHException:
            debug_log.error("Failed to invoke shell on the backend channel with id %s",
                            backend_channel.chanid)
            return False

        debug_log.info("Attacker opening a shell on the backend")
        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, self._session_log))
        handle_thread.start()

        return True

    def handle_exec_request(self, attacker_channel: paramiko.Channel, command: bytes) -> bool:
        """Tries to send an exec request to the corresponding backend channel.
        If the exec request succeeds data will be proxied between the two channels

        :param attacker_channel: The attacker channel
        :param command: The command to execute
        :return: True if we managed to send an exec request to the backend channel
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            cmd = command.decode("utf-8")
        except UnicodeDecodeError:
            debug_log.error("Failed to decode the command to utf8")
            return False

        try:
            backend_channel.exec_command(cmd)
        except SSHException:
            debug_log.error("Failed to execute the command %s on the backend", cmd)
            return False

        self._session_log.log_command(cmd)

        handle_thread = threading.Thread(
            target=proxy_data, args=(attacker_channel, backend_channel, self._session_log))
        handle_thread.start()

        return True

    def handle_pty_request(self, attacker_channel: paramiko.Channel, term_string: str,
                           width: int, height: int, pixelwidth: int,
                           pixelheight: int) -> bool:
        """Tries to send a pty request to the corresponding backend channel.

        :param attacker_channel: The attacker channel
        :param term: The type of terminal requested
        :param width: The width of the screen in characters
        :param height: The height of the screen in characters
        :param pixelwidth: The width of the screen in pixels, if known (may be 0 if unknown)
        :param pixelheight: The height of the screen in pixels, if known (may be 0 if unknown)
        :return: True if the pty request succeeded
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            backend_channel.get_pty(term_string, width, height, pixelwidth, pixelheight)
        except SSHException:
            debug_log.error("Failed to get pty on the backend")
            return False

        debug_log.info("Attacker sent pty request on channel %s", attacker_channel.chanid)
        return True

    def handle_window_change_request(self, attacker_channel: Channel, width: int, height: int,
                                     pixelwidth: int, pixelheight: int) -> bool:
        """Tries to send a window change request to the corresponding backend channel.

        :param attacker_channel: The attacker channel
        :param width: The width of the screen in characters
        :param height: The height of the screen in characters
        :param pixelwidth: The width of the screen in pixels, if known (may be 0 if unknown)
        :param pixelheight: The height of the screen in pixels, if known (may be 0 if unknown)
        :return: True if the window change request succeeded
        """
        backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
        try:
            backend_channel.resize_pty(width, height, pixelwidth, pixelheight)
        except SSHException:
            debug_log.error("Failed to resize pty on the backend")
            return False
        return True


def try_send_data(
        data: bytes,
        send_method: Callable[[bytes], None]) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        debug_log.warning("Timed out while trying to send data")
        return False
    except socket.error:
        debug_log.warning("Failed data")
        return False
    return True


def try_send_int(
        data: int,
        send_method: Callable[[int], None]) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        debug_log.warning("Timed out while trying to send data")
        return False
    except socket.error:
        debug_log.warning("Failed data")
        return False
    return True


def proxy_data(
        attacker_channel: paramiko.Channel,
        backend_channel: paramiko.Channel,
        session_log: SSHSession):
    """This will proxy data between two channels and log the data

    :param attacker_channel: The attacker channel
    :param backend_channel: The backend channeel
    :param session_log: The SSH logging session
    """
    attacker_channel.settimeout(10)
    backend_channel.settimeout(10)

    cmd_buffer: List[str]
    cmd_buffer = []
    carriage_return = "\r"
    delete = "\x7f"
    left_arrow = "\x1b[D"
    right_arrow = "\x1b[C"
    while not (attacker_channel.eof_received or attacker_channel.closed):
        # If the backend channel is shut down
        if backend_channel.eof_received or backend_channel.closed:
            # If we don't have data buffered from the backend
            if not (backend_channel.recv_ready() or backend_channel.recv_stderr_ready()):
                # Send a final exit code if there is one
                if backend_channel.exit_status_ready():
                    exit_code = backend_channel.recv_exit_status()
                    try_send_int(exit_code, attacker_channel.send_exit_status)
                debug_log.debug("Backend channel is closed and no more data is available to read")
                break

        if attacker_channel.recv_ready():
            data = attacker_channel.recv(1024)
            if not try_send_data(data, backend_channel.sendall):
                debug_log.debug("Failed to send data to backend_channel")

            try:
                cmd = data.decode("utf-8")
                for char in cmd:
                    if char == carriage_return:  # Treat everything before \r as a command
                        recieved_cmd = ''.join(cmd_buffer)
                        # Log parsed command
                        session_log.log_command(recieved_cmd)
                        cmd_buffer = []
                    elif char == delete:  # Pop from the cmd_buffer if we recieved delete
                        if len(cmd_buffer) > 0:
                            cmd_buffer.pop()
                    elif char == "D" or char == "C":  # Left or right arrow ending
                        cmd_buffer.append(char)
                        if ''.join(cmd_buffer).endswith(left_arrow):
                            print("Got left arrow")
                            cmd_buffer.pop()
                            cmd_buffer.pop()
                            cmd_buffer.pop()
                        if ''.join(cmd_buffer).endswith(right_arrow):
                            print("Got right arrow")
                            cmd_buffer.pop()
                            cmd_buffer.pop()
                            cmd_buffer.pop()
                    else:
                        cmd_buffer.append(char)
            except UnicodeDecodeError:
                debug_log.debug("Failed to decode command data")

        if backend_channel.recv_ready():
            data = backend_channel.recv(1024)
            session_log.log_ssh_channel_output(memoryview(data), attacker_channel.chanid)
            if not try_send_data(data, attacker_channel.sendall):
                debug_log.debug("Failed to send data to attacker_channel")
        if backend_channel.recv_stderr_ready():
            data = backend_channel.recv_stderr(1024)
            session_log.log_ssh_channel_output(memoryview(data), attacker_channel.chanid)
            if not try_send_data(data, attacker_channel.sendall_stderr):
                debug_log.debug("Failed to send data to attacker_channel stderr")

        sleep(0.1)

    # If one is channel has recieeved eof make sure to send it to the other
    if attacker_channel.eof_received:
        debug_log.info("Closing the backend channel since the attacker channel has sent eof")
        backend_channel.close()
    if backend_channel.eof_received:
        debug_log.info("Closing the attacker channel since the backend channel has sent eof")
        attacker_channel.close()
