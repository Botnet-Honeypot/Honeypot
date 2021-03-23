import logging
import backend.http_server as server


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Run HTTP server
    server.start_http_server()


if __name__ == '__main__':
    main()
