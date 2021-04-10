"""Main entrypoint for backend."""

import logging
import backend.container as container
import backend.http_server as server
import backend.config as config


def main():
    """Main entrypoint for backend."""

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Setup container management
    container_handler = container.Containers()

    if config.TARGET_SYSTEM_ADDRESS is None:
        raise TypeError('Environment variable TARGET_SYSTEM_ADDRESS must be set')

    # Run HTTP server
    http_server = server.start_http_server(
        container_handler,
        target_system_address=config.TARGET_SYSTEM_ADDRESS,
        bind_address=config.HTTP_API_BIND_ADDRESS)
    http_server.wait_for_termination()

    # Cleanup remaining containers
    container_handler.destroy_target_containers()


if __name__ == '__main__':
    main()
