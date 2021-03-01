from frontend.database import connect


def test_isConnecting():
    conn = connect()
    cur = conn.cursor()
    cur.execute('SELECT 1')
    assert 1 == cur.fetchone()[0]
