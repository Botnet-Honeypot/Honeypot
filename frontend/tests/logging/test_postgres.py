from frontend.honeylogger import create_ssh_session
from ipaddress import IPv4Address, ip_address


def test_no_runtime_errors():
    session = create_ssh_session(src_address=ip_address('43.56.223.156'),
                                 src_port=3463,
                                 dst_address=ip_address('226.64.12.2'),
                                 dst_port=22)
    session.begin("SSH-2.0-OpenSSH_fake")

    session.log_login_attempt('a_username', 'some_password')
    session.log_command('sudo rm -rf /')
    session.log_pty_request('xterm', 5, 20, 600, 200)
    session.log_download(memoryview(b'HELLO THIS IS SOME FILE DATA'),
                         'text/plain',
                         ip_address('2.43.12.243'),
                         'https://google.com/hello.txt')
    session.log_ssh_channel_output(memoryview(b'ls\noutput of ls....\n'), 1)
    session.log_ssh_channel_output(memoryview(b'more output of ls\n'), 1)
    session.log_ssh_channel_output(memoryview(b'SOME COMMAND ONE SECOND CHANNEL\n'), 2)
    session.log_ssh_channel_output(memoryview(b'output on second channel\n'), 2)
    session.log_env_request(1, "TERM", "screen")
    session.log_env_request(1523, "tnsrieotena", "pfeiabpu")
    session.log_direct_tcpip_request(4, IPv4Address("23.4.42.53"), 80, "google.com", 80)
    session.log_x11_request(4, False, "idk", memoryview(b"43"), 1)
    session.log_x11_request(5, True, "idkatall", memoryview(b"434"), 1)
    session.log_port_forward_request("54.123.64.3", 80)

    session.end()
