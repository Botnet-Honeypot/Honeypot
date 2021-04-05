"""Entrypoint for the honeypot frontend"""
import logging
import coloredlogs
import paramiko
from frontend.protocols.ssh import ConnectionManager as SSHConnectionManager
from frontend.config import config
import frontend.protocols.ssh
from frontend.target_systems import create_grpc_target_system_provider

logger = logging.getLogger(__name__)


def setup_logging():
    root_logger = logging.getLogger()

    # Console handler
    coloredlogs.install(
        logging.NOTSET, logger=root_logger,
        fmt='%(asctime)s %(levelname)-8s %(message)s (%(threadName)s, %(name)s)',
        datefmt='%Y-%m-%d %H:%M:%S')

    # File handler
    file_formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(message)s (%(threadName)s, %(name)s)',
        datefmt='%Y-%m-%d %H:%M:%S')
    file_handler = logging.FileHandler(config.SSH_LOG_FILE, encoding='UTF-8')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Log levels
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if config.SSH_ENABLE_DEBUG_LOGGING:
        ssh_logger = logging.getLogger(frontend.protocols.ssh.__name__)
        ssh_logger.setLevel(logging.DEBUG)


def main() -> None:
    """Entrypoint for the honeypot frontend"""

    # Set up logging
    setup_logging()

    # Create the target system provider to use for all attacker connections
    if config.BACKEND_ADDRESS is None:
        raise TypeError('Environment variable BACKEND_ADDRESS must be set')
    logger.info('Using backend with address: %s', config.BACKEND_ADDRESS)
    target_system_provider = create_grpc_target_system_provider(config.BACKEND_ADDRESS)

    # Start SSH server
    logger.info('Starting SSH server...')
    key = paramiko.RSAKey(filename='./host.key')
    server = SSHConnectionManager(target_system_provider=target_system_provider,
                                  host_key=key,
                                  port=config.SSH_SERVER_PORT,
                                  socket_timeout=config.SSH_SOCKET_TIMEOUT,
                                  max_unaccepted_connetions=config.SSH_MAX_UNACCEPTED_CONNECTIONS,
                                  usernames=config.SSH_ALLOWED_USERNAMES,
                                  passwords=config.SSH_ALLOWED_PASSWORDS)
    server.start()
    logger.info('SSH server started')

    # Wait for SSH server thread to exit
    server.join()
    logger.info('Shutdown complete')


if __name__ == '__main__':
    main()
