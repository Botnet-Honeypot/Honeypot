import frontend.example

# https://docs.pytest.org/en/stable/contents.html


def test_iscorrect():
    assert frontend.example.plus(1, 2) == 3
