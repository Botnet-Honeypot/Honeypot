from typing import Optional
from ._types import IPAddress
import frontend.database as db
import hashlib


def insert_network_source(cur, ip_address: IPAddress):
    cur.execute("""
                INSERT INTO NetworkSource (ip_address)
                    VALUES (%s)
                    ON CONFLICT (ip_address) DO NOTHING
                """, (str(ip_address),))


def insert_new_event(cur, session_id: int, type: str) -> int:
    cur.execute("""
                INSERT INTO Event (session_id, session_protocol, type)
                    VALUES (%s, 'ssh', %s)
                    RETURNING id
                """, (session_id, type))
    return cur.fetchone()[0]


def insert_file(cur, data: memoryview, type: str, save_data: bool) -> memoryview:
    data_value = '%(data)s' if save_data else 'NULL'
    conflict_action = 'UPDATE SET data = %(data)s' if save_data else 'DO NOTHING'
    cur.execute("""
                INSERT INTO File (hash, data, type)
                    VALUES (sha256(%(data)s), """ + data_value + """, %(type)s)
                    ON CONFLICT (hash) DO """ + conflict_action,
                {'data': data, 'type': type})
    return memoryview(hashlib.sha256(data).digest())


class PostgresLogSSHSession:
    """Implementation of logging.SSHSession that logs session and actions to a Postgres database"""

    session_id: int

    source: str
    src_address: IPAddress
    src_port: int
    dst_address: IPAddress
    dst_port: int

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        self.source = f'{src_address}:{src_port}'
        self.src_address = src_address
        self.src_port = src_port
        self.dst_address = dst_address
        self.dst_port = dst_port

    def begin_ssh_session(self) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    insert_network_source(cur, self.src_address)
                    cur.execute("""
                        INSERT INTO Session (attack_src, protocol, src_port, dst_ip, dst_port)
                            VALUES (%s, 'ssh', %s, %s, %s)
                            RETURNING id
                        """, (str(self.src_address), self.src_port, str(self.dst_address), self.dst_port))

                    self.session_id = cur.fetchone()[0]
        finally:
            conn.close()

    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    event_id = insert_new_event(
                        cur, self.session_id, 'pty_request')
                    cur.execute("""
                        INSERT INTO PTYRequest (event_id, event_type, session_protocol, term, term_width_cols,
                            term_height_rows, term_width_pixels, term_height_pixels)
                            VALUES (%s, 'pty_request', 'ssh', %s, %s, %s, %s, %s)
                        """, (event_id, term, term_width_cols,
                              term_height_rows, term_width_pixels, term_height_pixels))
        finally:
            conn.close()

    def log_login_attempt(self, username: str, password: str) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    event_id = insert_new_event(
                        cur, self.session_id, 'login_attempt')
                    cur.execute("""
                        INSERT INTO LoginAttempt (event_id, username, password)
                            VALUES (%s, %s, %s)
                        """, (event_id, username, password))
        finally:
            conn.close()

    def log_command(self, input: str) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    event_id = insert_new_event(
                        cur, self.session_id, 'command')
                    cur.execute("""
                        INSERT INTO Command (event_id, input)
                            VALUES (%s, %s)
                        """, (event_id, input))
        finally:
            conn.close()

    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    event_id = insert_new_event(
                        cur, self.session_id, 'ssh_channel_output')
                    cur.execute("""
                        INSERT INTO SSHChannelOutput (event_id, data, channel)
                            VALUES (%s, %s, %s)
                        """, (event_id, data, channel))
        finally:
            conn.close()

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    event_id = insert_new_event(
                        cur, self.session_id, 'download')
                    file_hash = insert_file(cur, data, file_type, save_data)
                    insert_network_source(cur, source_address)
                    cur.execute("""
                        INSERT INTO Download (event_id, hash, src, url)
                            VALUES (%s, %s, %s, %s)
                        """, (event_id, file_hash, str(source_address), source_url))
        finally:
            conn.close()

    def end(self) -> None:
        conn = db.connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE Session
                            SET end_timestamp = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (self.session_id,))
        finally:
            conn.close()
