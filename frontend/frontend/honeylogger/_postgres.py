from __future__ import annotations
from datetime import timezone, datetime
import functools
from time import sleep, time
from typing import Any, Callable, Iterator, Optional
import hashlib
import threading
import logging
import itertools
from contextlib import contextmanager
from psycopg2.pool import PoolError, ThreadedConnectionPool
from psycopg2 import OperationalError
import random
import frontend.config
from ._types import IPAddress


logger = logging.getLogger(__name__)


def debug(func):
    """Wrapper to log method calls to PostgresLogSSHSession"""
    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        # Instance
        instance = args[0]
        # Args and kwargs
        args_repr = [repr(a) for a in args[1:]]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2

        # Join them
        signature = ", ".join(args_repr + kwargs_repr)

        start_time = time()
        try:
            value = func(*args, **kwargs)
        except Exception as exc:
            logger.exception("%s %s(%s) Threw an exception!",
                             instance, func.__name__, signature, exc_info=exc)
            raise
        finally:
            logger.debug("%s %s(%s) (took %fs)",
                         instance, func.__name__, signature, time()-start_time)

        return value
    return wrapper_debug


def get_timestamp() -> datetime:
    return datetime.now(timezone.utc)


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

    _begin_successful: bool
    _session_aborted: bool
    _end_successful: bool

    _lock: threading.Lock
    _conn_pool: ThreadedConnectionPool
    _conn: Optional[Any]

    session_id: Optional[int]
    ssh_version: Optional[str]
    src_address: IPAddress
    src_port: int
    dst_address: IPAddress
    dst_port: int

    def __init__(self,
                 conn_pool: ThreadedConnectionPool,
                 src_address: IPAddress, src_port: int,
                 dst_address: IPAddress, dst_port: int) -> None:
        self._begin_successful = False
        self._session_aborted = False
        self._end_successful = False
        self._lock = threading.Lock()
        self._conn_pool = conn_pool
        self._conn = None
        self._scheduled_inserts = []
        self.session_id = None
        self.ssh_version = None
        self.src_address = src_address
        self.src_port = src_port
        self.dst_address = dst_address
        self.dst_port = dst_port

    def __str__(self) -> str:
        session_id = self.session_id if self.session_id is not None else -1
        return f"[Session: {session_id}]"

    def __del__(self):
        if self._conn is not None:
            logger.critical(
                '%s DATA LOST AND DB CONN LEAKED! Logging session was started but never ended.',
                self)

    @contextmanager
    def _get_connection(self) -> Iterator[Any]:
        with self._lock:
            if self._session_aborted:
                raise Exception('This session failed and was aborted, cannot be used anymore!')

            if self._conn is None:
                try:
                    # Connect and begin transaction
                    self._conn = PostgresLogSSHSession._connect(self, self._conn_pool)
                except Exception as exc:
                    self._session_aborted = True
                    logger.exception("%s ABC Failed to get connection from pool",
                                     self, exc_info=exc)
                    raise

            try:
                yield self._conn
            except:
                logger.critical(
                    '%s DATA LOST! Error while using DB connection, returning connection to pool...',
                    self)
                self._session_aborted = True
                if self._conn is not None:
                    self._conn_pool.putconn(self._conn, close=True)
                    self._conn = None
                raise

    @staticmethod
    def _connect(session, pool: ThreadedConnectionPool,
                 max_retries=10, backoff_ms=10, max_timeout=30) -> Any:
        """Gets a database connection for this session from connection pool.
        If no connection is currently available, reattempts are made to connect.

        :raises RuntimeError: If no connection can be made, even after retrying.
        """
        start_time = time()
        for num_retries in itertools.count():
            try:
                if frontend.config.SIMULATE_UNSTABLE_DB_CONNECTION and random.random() < 0.1:
                    raise OperationalError('NOPE')

                conn = pool.getconn()

                logger.debug(
                    '%s [%s:%d] Acquired database connection for logging session, took %fs (retry #%d)',
                    session, session.src_address, session.src_port,
                    time() - start_time, num_retries)
                return conn
            except (PoolError, OperationalError) as exc:
                if num_retries == max_retries or time() - start_time >= max_timeout:
                    raise RuntimeError(
                        f'Failed to get database connection for logging session {session} after '
                        f'{time() - start_time}s (retry #{num_retries})'
                    ) from exc

                logger.debug('%s No database connection available after %fs, retrying (#%d)...',
                             session, time() - start_time, num_retries + 1)
                # Exponential backoff
                backoff = (2 ** num_retries * backoff_ms) / 1000
                sleep(backoff)

    def _queue_insert(self, conn, function: InsertFunc) -> None:
        """Queues an insert function to run in session's
        current transaction.

        :param function: Function performing database inserts.
        """
        with conn.cursor() as cur:
            if frontend.config.SIMULATE_UNSTABLE_DB_CONNECTION and random.random() < 0.1:
                raise Exception('NOPE')

            function(cur, self)

    def _commit_and_disconnect(self) -> None:
        """Commits the session's database transaction
        and hands connection back to connection pool.
        """

        if frontend.config.SIMULATE_UNSTABLE_DB_CONNECTION and random.random() < 0.1:
            raise Exception('NOPE')

        t0 = time()
        try:
            self._conn.commit()
        except Exception as exc:
            logger.exception('%s ABC Failed to commit changes',
                             self, exc_info=exc)
        finally:
            self._conn_pool.putconn(self._conn, close=True)
            self._conn = None

        logger.debug('%s Logging session committed (took %fs)',
                     self, time()-t0)

    def set_remote_version(self, ssh_version: str) -> None:
        """Sets the SSH remote version of the session.

        : param ssh_version: The SSH remote version string.
        : raises ValueError: If the version string is None.
        : raises ValueError: If called more than once.
        : raises ValueError: If called after calling ``begin``.
        """

        if ssh_version is None:
            raise ValueError('ssh_version may not be None')
        if self.ssh_version is not None:
            raise ValueError('ssh_version may only be set once')
        if self._begin_successful:
            raise ValueError('ssh_version may not be set after session has started')
        self.ssh_version = ssh_version

    @debug
    def begin(self) -> None:
        if self._begin_successful:
            raise ValueError('Logging session was already started')
        if self.ssh_version is None:
            raise ValueError('SSH version must be set before beginning session')

        timestamp = get_timestamp()

        def insert(cur, session):
            insert_network_source(cur, session.src_address)
            cur.execute("""
                INSERT INTO Session (attack_src, protocol, src_port, dst_ip, dst_port, start_timestamp)
                    VALUES (%s, 'ssh', %s, %s, %s, %s)
                    RETURNING id
                """,  (str(session.src_address), session.src_port,
                        str(session.dst_address), session.dst_port, timestamp))
            session.session_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO SSHSession (session_id, ssh_version)
                    VALUES (%s, %s)
                """,  (session.session_id, session.ssh_version))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

        self._begin_successful = True

    @debug
    def log_pty_request(self, term: str,
                        term_width_cols: int, term_height_rows: int,
                        term_width_pixels: int, term_height_pixels: int) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'pty_request', timestamp)
            cur.execute("""
                INSERT INTO PTYRequest (event_id, term, term_width_cols,
                    term_height_rows, term_width_pixels, term_height_pixels)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (event_id, term, term_width_cols,
                      term_height_rows, term_width_pixels, term_height_pixels))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_env_request(self, chan_id: int, name: str, value: str) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'env_request', timestamp)
            cur.execute("""
                INSERT INTO EnvRequest (event_id, channel_id, name, value)
                    VALUES (%s, %s, %s, %s)
                """, (event_id, chan_id, name, value))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_direct_tcpip_request(self, chan_id: int, origin_ip: IPAddress, origin_port: int,
                                 destination: str, destination_port: int) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'direct_tcpip_request', timestamp)
            cur.execute("""
                INSERT INTO DirectTCPIPRequest (event_id, channel_id,
                    origin_ip, origin_port, destination, destination_port)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (event_id, chan_id, str(origin_ip), origin_port, destination, destination_port))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_x11_request(
            self, chan_id: int, single_connection: bool, auth_protocol: str,
            auth_cookie: memoryview, screen_number: int) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'x_eleven_request', timestamp)
            cur.execute("""
                INSERT INTO XElevenRequest (event_id, channel_id,
                    single_connection, auth_protocol, auth_cookie, screen_number)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (event_id, chan_id, single_connection, auth_protocol, auth_cookie, screen_number))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_port_forward_request(self, address: str, port: int) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'port_forward_request', timestamp)
            cur.execute("""
                INSERT INTO PortForwardRequest (event_id, address, port)
                    VALUES (%s, %s, %s)
                """, (event_id, address, port))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_login_attempt(self, username: str, password: str) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'login_attempt', timestamp)
            cur.execute("""
                INSERT INTO LoginAttempt (event_id, username, password)
                    VALUES (%s, %s, %s)
                """, (event_id, username, password))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_command(self, input: str) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'command', timestamp)
            cur.execute("""
                INSERT INTO Command (event_id, input)
                    VALUES (%s, %s)
                """, (event_id, input))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_ssh_channel_output(self, data: memoryview, channel: int) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'ssh_channel_output', timestamp)
            cur.execute("""
                INSERT INTO SSHChannelOutput (event_id, data, channel)
                    VALUES (%s, %s, %s)
                """, (event_id, data, channel))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def log_download(self,
                     data: memoryview,
                     file_type: str,
                     source_address: IPAddress,
                     source_url: Optional[str] = None,
                     save_data: bool = True) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')

        timestamp = get_timestamp()

        def insert(cur, session):
            event_id = insert_new_event(
                cur, session.session_id, 'download', timestamp)
            file_hash = insert_file(cur, data, file_type, save_data)
            insert_network_source(cur, source_address)
            cur.execute("""
                INSERT INTO Download (event_id, hash, src, url)
                    VALUES (%s, %s, %s, %s)
                """, (event_id, file_hash, str(source_address), source_url))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)

    @debug
    def end(self) -> None:
        if not self._begin_successful:
            raise ValueError('Logging session was not started')
        if self._end_successful:
            raise ValueError('Logging session was ended already')

        timestamp = get_timestamp()

        def insert(cur, session):
            cur.execute("""
                UPDATE Session
                    SET end_timestamp = %s
                    WHERE id = %s
                """, (timestamp, session.session_id))

        with self._get_connection() as conn:
            self._queue_insert(conn, insert)
            self._commit_and_disconnect()

        self._end_successful = True


InsertFunc = Callable[[Any, PostgresLogSSHSession], None]
