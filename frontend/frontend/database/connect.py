import logging
import psycopg2
from psycopg2 import pool
from frontend.database.config import config

logger = logging.getLogger(__name__)

db_config = config()


def connect():
    """Connects to the PostgreSQL database server

    :return: The psycopg2 ``connection`` object for the connection. 
    """
    try:
        # Connect to the PostgreSQL server
        logger.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            host=db_config['host'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
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
        minconn=db_config['min_connections'],
        maxconn=db_config['max_connections'],
        host=db_config['host'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password'],
        **kwargs
    )
