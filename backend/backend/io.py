"""Module for IO-related utilties"""

import io
from typing import IO, Iterable, Optional


def byte_stream_from_iterable(
        iterable: Iterable[bytes],
        buffer_size=io.DEFAULT_BUFFER_SIZE) -> IO[bytes]:
    """
    Source: https://gist.github.com/mechanical-snail/7688353

    Lets you use an iterable (e.g. a generator) that yields bytestrings as a read-only input stream.

    The stream implements Python 3's newer I/O API (available in Python 2's io module).
    For efficiency, the stream is buffered.
    """
    iterator = iter(iterable)

    class IterStream(io.RawIOBase):
        leftover: Optional[bytes]

        def __init__(self):
            self.leftover = None

        def readable(self):
            return True

        def readinto(self, b):
            try:
                length = len(b)  # We're supposed to return at most this much
                chunk = self.leftover or next(iterator)
                output, self.leftover = chunk[:length], chunk[length:]
                b[:len(output)] = output
                return len(output)
            except StopIteration:
                return 0  # indicate EOF

    return io.BufferedReader(IterStream(), buffer_size=buffer_size)
