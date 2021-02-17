import socket
import threading

import paramiko


class SSHServer(paramiko.ServerInterface):
    MAX_UNACCEPTED_CONNECTIONS = 100

    def __init__(self, host_key: paramiko.PKey, port: int = 22) -> None:
        self.host_key = host_key
        self.port = port
        self.event = threading.Event()

    # todo move method out of SSHServer class
    def listen(self) -> None:
        try:
            # SOCK_STREAM is TCP
            # AF_INET is IPv4
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Permit reuse of local addresses for this socket.
            # More information on options can be found here
            # https://www.gnu.org/software/libc/manual/html_node/Socket_002dLevel-Options.html
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.port))
        except Exception as exc:
            print(f"Failed to bind port.\nError:{exc}")
            raise

        try:
            sock.listen(self.MAX_UNACCEPTED_CONNECTIONS)
            # todo Only accept one client for now
            client, addr = sock.accept()
            t = paramiko.Transport(client)
        except Exception as exc:
            print(f"Failed to accept connection\nError{exc}")
            raise

        t.set_gss_host(socket.getfqdn(""))

        if not t.load_server_moduli():
            print("No moduli")

        t.add_server_key(self.host_key)
        # Negotiate a new SSH session
        t.start_server(server=self)
        self.event.wait(30)
        t.close()
