from __future__ import annotations
from datetime import timezone, datetime
from typing import Any, Callable, Optional
import hashlib
import threading
import logging
import frontend.database as db
from ._types import IPAddress


logger = logging.getLogger(__name__)


def insert_network_source(cur, ip_address: IPAddress):
    cur.execute("""
                INSERT INTO NetworkSource (ip_address)
                    VALUES (%s)
                    ON CONFLICT (ip_address) DO NOTHING
                """, (str(ip_address),))


def insert_new_event(cur, session_id: int, event_type: str, timestamp: datetime) -> int:
    cur.execute("""
                INSERT INTO Event (session_id, session_protocol, type, timestamp)
                    VALUES (%s, 'ssh', %s, %s)
                    RETURNING id
                """, (session_id, event_type, timestamp))
    return cur.fetchone()[0]


def insert_file(cur, data: memoryview, file_type: str, save_data: bool) -> memoryview:
    data_value = '%(data)s' if save_data else 'NULL'
    conflict_action = 'UPDATE SET data = %(data)s' if save_data else 'DO NOTHING'
    cur.execute("""
                INSERT INTO File (hash, data, type)
                    VALUES (sha256(%(data)s), """ + data_value + """, %(type)s)
                    ON CONFLICT (hash) DO """ + conflict_action,
                {'data': data, 'type': file_type})
    return memoryview(hashlib.sha256(data).digest())


class PostgresLogSSHSession:
    """Implementation of honeylogger.SSHSession that
    logs session and actions to a Postgres database"""

    begin_called: bool

    _lock: threading.Lock
    _scheduled_inserts: list[InsertFunc]

    session_id: Optional[int]
    src_address: IPAddress
    src_port: int
    dst_address: IPAddress
    dst_port: int

    def __init__(self,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        self.begin_called = False
        self._lock = threading.Lock()
        self._scheduled_inserts = []
        self.session_id = None
        self.src_address = src_address
        self.src_port = src_port
        self.dst_address = dst_address
        self.dst_port = dst_port

    def _schedule_insert(self, function: InsertFunc) -> None:
        with self._lock:
            self._scheduled_inserts.append(function)

    def _get_timestamp(self) -> datetime:
        return datetime.now(timezone.utc)

    def begin(self, ssh_version: str) -> None:
        if self.begin_called:
            raise ValueError('Logging session was already started')
        self.begin_called = True

        timestamp = self._get_timestamp()

        def insert(cur, session):
            insert_network_source(cur, session.src_address)
            cur.execute("""
                INSERT INTO Session (ssh_version, attack_src, protocol, src_port, dst_ip, dst_port, start_timestamp)
                    VALUES (%s, %s, 'ssh', %s, %s, %s, %s)
                    RETURNING id
                """, (ssh_version, str(session.src_address), session.src_port,
                      str(session.dst_address), session.dst_port, timestamp))
            session.session_id = cur.fetchone()[0]

        self._schedule_insert(insert)

    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'pty_request', timestamp)
            cur.execute("""
                INSERT INTO PTYRequest (event_id, event_type, session_protocol, term, term_width_cols,
                    term_height_rows, term_width_pixels, term_height_pixels)
                    VALUES (%s, 'pty_request', 'ssh', %s, %s, %s, %s, %s)
                """, (event_id, term, term_width_cols,
                      term_height_rows, term_width_pixels, term_height_pixels))

        self._schedule_insert(insert)

    def log_env_request(self, chan_id: int, name: str, value: str) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'env_request', timestamp)
            cur.execute("""
                INSERT INTO EnvRequest (event_id, event_type, session_protocol, channel_id,
                    name, value)
                    VALUES (%s, 'env_request', 'ssh', %s, %s, %s)
                """, (event_id, chan_id, name, value))

        self._schedule_insert(insert)

    def log_direct_tcpip_request(self, chan_id: int, origin_ip: IPAddress, origin_port: int,
                                 destination: str, destination_port: int) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'direct_tcpip_request', timestamp)
            cur.execute("""
                INSERT INTO DirectTCPIPRequest (event_id, event_type, session_protocol, channel_id,
                    origin_ip, origin_port, destination, destination_port)
                    VALUES (%s, 'direct_tcpip_request', 'ssh', %s, %s, %s, %s, %s)
                """, (event_id, chan_id, str(origin_ip), origin_port, destination, destination_port))

        self._schedule_insert(insert)

    def log_x11_request(
            self, chan_id: int, single_connection: bool, auth_protocol: str,
            auth_cookie: memoryview, screen_number: int) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'x_eleven_request', timestamp)
            cur.execute("""
                INSERT INTO XElevenRequest (event_id, event_type, session_protocol, channel_id,
                    single_connection, auth_protocol, auth_cookie, screen_number)
                    VALUES (%s, 'x_eleven_request', 'ssh', %s, %s, %s, %s, %s)
                """, (event_id, chan_id, single_connection, auth_protocol, auth_cookie, screen_number))

        self._schedule_insert(insert)

    def log_port_forward_request(self, address: str, port: int) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'port_forward_request', timestamp)
            cur.execute("""
                INSERT INTO PortForwardRequest (event_id, event_type, session_protocol,
                    address, port)
                    VALUES (%s, 'port_forward_request', 'ssh', %s, %s)
                """, (event_id, address, port))

        self._schedule_insert(insert)

    def log_login_attempt(self, username: str, password: str) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'login_attempt', timestamp)
            cur.execute("""
                INSERT INTO LoginAttempt (event_id, username, password)
                    VALUES (%s, %s, %s)
                """, (event_id, username, password))

        self._schedule_insert(insert)

    def log_command(self, input: str) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'command', timestamp)
            cur.execute("""
                INSERT INTO Command (event_id, input)
                    VALUES (%s, %s)
                """, (event_id, input))

        self._schedule_insert(insert)

    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'ssh_channel_output', timestamp)
            cur.execute("""
                INSERT INTO SSHChannelOutput (event_id, data, channel)
                    VALUES (%s, %s, %s)
                """, (event_id, data, channel))

        self._schedule_insert(insert)

    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'download', timestamp)
            file_hash = insert_file(cur, data, file_type, save_data)
            insert_network_source(cur, source_address)
            cur.execute("""
                INSERT INTO Download (event_id, hash, src, url)
                    VALUES (%s, %s, %s, %s)
                """, (event_id, file_hash, str(source_address), source_url))

        self._schedule_insert(insert)

    def end(self) -> None:
        if not self.begin_called:
            raise ValueError('Logging session was not started')

        timestamp = self._get_timestamp()

        def insert(cur, session):
            cur.execute("""
                UPDATE Session
                    SET end_timestamp = %s
                    WHERE id = %s
                """, (timestamp, session.session_id))

        self._schedule_insert(insert)

        logger.debug('Inserting logging session %s into database...', self.session_id)
        with self._lock:
            conn = db.connect()
            with conn:  # Start transaction
                with conn.cursor() as cur:
                    for func in self._scheduled_inserts:
                        func(cur, self)
        logger.debug('Logging session %s inserted', self.session_id)


InsertFunc = Callable[[Any, PostgresLogSSHSession], None]
