from frontend.database import connect


def test_isConnecting():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert 1 == cur.fetchone()[0]


def test_isInserting():
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO NetworkSource (ip_address) VALUES ('192.168.1.0')")
    cur.execute(
        "SELECT ip_address FROM NetworkSource WHERE ip_address = '192.168.1.0'")
    assert None != cur.fetchone()
