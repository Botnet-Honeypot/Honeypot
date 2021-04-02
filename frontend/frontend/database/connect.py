import logging
import psycopg2
from frontend.database.config import config

logger = logging.getLogger(__name__)


def connect():
    """ Connects to the PostgreSQL database server """
    try:
        # read connection parameters
        params = config()

        # connect to the PostgreSQL server
        logger.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)

        return conn
    except (Exception, psycopg2.DatabaseError):
        logger.exception('Failed to connect to Postgres database')
