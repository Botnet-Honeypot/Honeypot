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

    # Run HTTP server
    http_server = server.start_http_server(
        container_handler, bind_address=config.HTTP_API_BIND_ADDRESS)
    http_server.wait_for_termination()


if __name__ == '__main__':
    main()
