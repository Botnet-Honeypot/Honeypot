import logging
import psycopg2
from psycopg2 import pool
from frontend.config import config

logger = logging.getLogger(__name__)


def connect():
    """Connects to the PostgreSQL database server

    :return: The psycopg2 ``connection`` object for the connection. 
    """
    try:
        # Connect to the PostgreSQL server
        logger.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            host=config.DB_HOSTNAME,
            database=config.DB_DATABASE,
            user=config.DB_USERNAME,
            password=config.DB_PASSWORD
        )

        return conn
    except Exception:
        logger.exception('Failed to connect to Postgres database')
        raise


def create_pool(**kwargs) -> pool.ThreadedConnectionPool:
    """Creates a new pool of database connections.

    :return: The connection pool.
    """

    return pool.ThreadedConnectionPool(
        minconn=config.DB_MIN_CONNECTIONS,
        maxconn=config.DB_MAX_CONNECTIONS,
        host=config.DB_HOSTNAME,
        database=config.DB_DATABASE,
        user=config.DB_USERNAME,
        password=config.DB_PASSWORD,
        **kwargs
    )
