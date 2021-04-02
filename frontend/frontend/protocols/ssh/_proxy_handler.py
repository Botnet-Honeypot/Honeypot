"""This file contains the ProxyHandler class which can be used to
proxy data between the backend and log commands recieved from the attacker and
all the data recieved from the backend during the sesison.
"""
import logging
import socket
import threading
from time import sleep, time
from typing import Optional
import itertools

import paramiko
from paramiko import SSHException
from paramiko.ssh_exception import AuthenticationException, BadHostKeyException
from paramiko.transport import Transport
from paramiko.channel import Channel
from paramiko.common import (OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED, OPEN_SUCCEEDED)

from frontend.honeylogger import SSHSession
from ._command_parser import CommandParser
from frontend.target_systems import TargetSystemProvider

logger = logging.getLogger(__name__)


class ProxyHandler:
    """This class is responsible for proxying information from recieved attacker SSH channels
    to corresponding backend channels
    """

    # SSH transport to the backend, None if not open
    _backend_transport: Optional[Transport]
    # Dict mapping the attacker channel IDs to a proxy channel to the backend
    _backend_chan_proxies: dict[int, Channel]

    # A session log we can log events to
    _session_log: SSHSession

    # The provider used to acquire a target system for this attacker connection
    _target_system_provider: TargetSystemProvider

    def __init__(self,
                 session_log: SSHSession,
                 target_system_provider: TargetSystemProvider) -> None:
        self._backend_transport = None
        self._backend_chan_proxies = dict()
        self._session_log = session_log
        self._target_system_provider = target_system_provider

    @staticmethod
    def _open_proxy_transport(ip_address: str, port: int,
                              username: str, password: str,
                              max_retries: int = 10,
                              backoff_time_ms=10) -> Optional[Transport]:
        """Opens another SSH session to proxy data over

        :param ip_address: The IP adress of the SSH proxy
        :param port: The port of the SSH proxy
        :param username: The usernames of the SSH proxy
        :param password: The password of the SSH proxy
        :return: If successful, the SSH transport for the connection, otherwise None
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            for num_retries in itertools.count():
                try:
                    client.connect(ip_address, port=port, username=username, password=password)
                    transport = client.get_transport()

                    if transport is None:
                        raise SSHException(
                            f"Failed to obtain SSH transport for {ip_address}:{port}")
                    return transport

                except (SSHException, socket.error):
                    if num_retries == max_retries:
                        raise  # If we ran out of retries, propagate exception

                    logger.debug('Connection to target system failed, retrying (#%d)...',
                                 num_retries+1)

                    # Exponential backoff
                    backoff = (2 ** num_retries * backoff_time_ms) / 1000
                    sleep(backoff)
                    continue

        except AuthenticationException:
            logger.error("Authentication failed on SSH proxy %s:%i with %s/%s",
                         ip_address, port, username, password)
            return None
        except SSHException:
            logger.exception("Failed to establish a SSH session to SSH proxy %s:%i with %s/%s",
                             ip_address, port, username, password)
            return None
        except socket.error:
            logger.exception(
                "Got socket excepting while connecting to SSH proxy %s:%i with %s/%s", ip_address,
                port, username, password)
            return None
        except Exception:
            logger.exception(
                "Got unknown excepting while connecting to SSH proxy %s:%i with %s/%s", ip_address,
                port, username, password)
            return None

    def _get_corresponding_backend_channel(self, attacker_chan_id: int) -> paramiko.Channel:
        """Retrieves the corresponding backend channel that is related to the attacker channel

        :param attacker_chan_id: The attacker channel id
        :raises KeyError: If the corresponding backend channel does not exist
        :return: The corresponding backend channel
        """
        chan = self._backend_chan_proxies.get(attacker_chan_id)
        if chan is None:
            raise KeyError(
                ("Failed to obtain a backend channel correspoding"
                 f"to the attacker channel {attacker_chan_id}\n"
                 "This should never happen since a attacker channel id should always"
                 "be related to a backend channel"))

        return chan

    def close_connection(self) -> None:
        """This closes the backend connection and ends the session
        """
        self._session_log.end()
        if self._backend_transport is None:
            return
        # Close the backend connection
        try:
            self._backend_transport.close()
        except Exception:
            logger.exception("Failed to close backend transport")
        finally:
            self._backend_transport = None

    def create_backend_connection(self) -> bool:
        """Sets up the a SSH connection to the backend

        :return: True if the connection was successful
        """

        username = 'aaa'
        password = 'bbb'

        if self._backend_transport is not None:
            # Connction already opened
            return True

        t0 = time()
        # Acquire target system
        logger.debug('Acquiring target system from provider...')
        target_system = self._target_system_provider.acquire_target_system(username, password)
        if target_system is None:
            logger.warning('No target system was available to be acquired')
            return False
        t1 = time()
        try:
            # Open the backend transport
            logger.debug('Connecting to target system %s:%d...',
                         target_system.address, target_system.port)
            self._backend_transport = self._open_proxy_transport(target_system.address,
                                                                 target_system.port,
                                                                 username, password)
            t2 = time()
            print(f'Acquire: {t1-t0}')
            print(f'Connect: {t2-t1}')
            print(f'Total: {t2-t0}')
        finally:
            if self._backend_transport is None:
                # If connection to target system failed, yield it back to provider
                logger.debug('Failed to connect to %s:%d, yielding target system...',
                             target_system.address, target_system.port)
                self._target_system_provider.yield_target_system(target_system)

        return self._backend_transport is not None

    def open_channel(self, kind: str, chanid: int) -> int:
        """Tries to open a channel to the backend

        :param kind: The channel kind
        :param chanid: The channel id of the channel that the attacker requested
        :return: An int given by paramiko
        """
        try:
            chan = self._backend_transport.open_channel(kind)
        except SSHException:
            logger.error("Failed to open a new channel with kind %s on the backend", kind)
            return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        logger.info("Attacker opening channel %s", chanid)
        # Save the opened channel in our dict
        self._backend_chan_proxies[chanid] = chan
        return OPEN_SUCCEEDED

    def handle_shell_request(self, attacker_channel: paramiko.Channel):
        """Tries to send a shell request to the corresponding backend channel.
        If the shell request succeeds data will be proxied between the two channels

        :param attacker_channel: The attacker channel
        :return: True if we managed to send a shell request to the backend channel
        """
        try:
            backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
            backend_channel.invoke_shell()
        except KeyError:
            return False
        except SSHException:
            logger.error("Failed to invoke shell on the backend channel with id %s",
                         attacker_channel.chanid)
            return False

        logger.info("Attacker opening a shell on the backend")
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
        try:
            backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
            cmd = command.decode("utf-8")
        except KeyError:
            return False
        except UnicodeDecodeError:
            logger.error("Failed to decode the command to utf8")
            return False

        try:
            backend_channel.exec_command(cmd)
        except SSHException:
            logger.error("Failed to execute the command %s on the backend", cmd)
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
        try:
            backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
            backend_channel.get_pty(term_string, width, height, pixelwidth, pixelheight)
        except KeyError:
            return False
        except SSHException:
            logger.error("Failed to get pty on the backend")
            return False

        logger.info("Attacker sent pty request on channel %s", attacker_channel.chanid)
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
        try:
            backend_channel = self._get_corresponding_backend_channel(attacker_channel.chanid)
            backend_channel.resize_pty(width, height, pixelwidth, pixelheight)
        except KeyError:
            return False
        except SSHException:
            logger.error("Failed to resize pty on the backend")
            return False
        return True


def try_send_data(data, send_method) -> bool:
    """Tries to send data and catch exceptions

    :param data: The data to send
    :param send_method: The send method
    :return: True if suceeded to send data
    """
    try:
        send_method(data)
    except socket.timeout:
        logger.warning("Timed out while trying to send data")
        return False
    except socket.error:
        logger.warning("Failed data")
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

    command_parser = CommandParser()
    # While the attacker channel is not closed and has not send eof
    while not (attacker_channel.eof_received or attacker_channel.closed):
        # If the backend channel is shut down
        if backend_channel.eof_received or backend_channel.closed:
            # If we don't have data buffered from the backend we will break from the loop
            if not (backend_channel.recv_ready() or backend_channel.recv_stderr_ready()):
                # Send a final exit code if there is one
                if backend_channel.exit_status_ready():
                    exit_code = backend_channel.recv_exit_status()
                    if try_send_data(exit_code, attacker_channel.send_exit_status):
                        pass  # logger.error("Failled to send exit code to the attacker")
                logger.debug("Backend channel is closed and no more data is available to read")
                break

        if attacker_channel.recv_ready():
            data = attacker_channel.recv(1024)
            if not try_send_data(data, backend_channel.sendall):
                logger.error("Failed to send attacker data to the backend")

            try:
                cmd = data.decode("utf-8")
                command_parser.add_to_cmd_buffer(cmd)
            except UnicodeDecodeError:
                logger.debug("Failed to decode attacker command data %s", data)

            if command_parser.can_read_command():
                session_log.log_command(command_parser.read_command())

        if backend_channel.recv_ready():
            data = backend_channel.recv(1024)
            session_log.log_ssh_channel_output(memoryview(data), attacker_channel.chanid)
            if not try_send_data(data, attacker_channel.sendall):
                logger.error("Failed to send backend stdout data to attacker")
        if backend_channel.recv_stderr_ready():
            data = backend_channel.recv_stderr(1024)
            session_log.log_ssh_channel_output(memoryview(data), attacker_channel.chanid)
            if not try_send_data(data, attacker_channel.sendall_stderr):
                logger.error("Failed to send backend stderr data to attacker")

        sleep(0.1)

    # If one is channel has recieeved eof make sure to send it to the other
    if attacker_channel.eof_received:
        logger.debug("Closing the backend channel since the attacker channel has sent eof")
        backend_channel.close()
    if backend_channel.eof_received:
        logger.debug("Closing the attacker channel since the backend channel has sent eof")
        attacker_channel.close()
