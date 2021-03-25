import logging
import backend.container as container
import backend.http_server as server


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Setup container management
    container_handler = container.Containers()

    # Run HTTP server
    http_server = server.start_http_server(container_handler, port=80)
    http_server.wait_for_termination()


if __name__ == '__main__':
    main()
