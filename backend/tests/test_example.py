import backend.example

# https://docs.pytest.org/en/stable/contents.html


def test_iscorrect():
    assert backend.example.plus(1, 2) == 3