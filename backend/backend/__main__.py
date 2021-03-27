"""Main entrypoint for backend."""

import logging
import urllib.request
import backend.container as container
import backend.http_server as server
import backend.config as config


def main():
    """Main entrypoint for backend."""

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Find public server IP
    # TODO: Is there any better way to get the public facing ip?
    public_address = urllib.request.urlopen('https://ident.me').read().decode('utf8')

    # Setup container management
    container_handler = container.Containers()

    # Run HTTP server
    http_server = server.start_http_server(
        container_handler,
        public_address,
        bind_address=config.HTTP_API_BIND_ADDRESS)
    http_server.wait_for_termination()


if __name__ == '__main__':
    main()
