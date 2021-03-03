import psycopg2
from frontend.database.config import config

# The following connect() function connects to the suppliers database and prints out the PostgreSQL database version.


def connect():
    """ Connect to the PostgreSQL database server """
    # psql_conn = None
    try:
        # read connection parameters
        params = config()

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)

        # create a cursor
        # cur = conn.cursor()

        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
