"""The CommandParser class
"""
import queue
import logging

from frontend.config import config

debug_log = logging.getLogger(config.SSH_DEBUG_LOG)


class CommandParser:
    """A class to parse recieved data from the attacker.
    It is not thread safe, so don't share an instance of this across threads
    """
    CR = "\r"
    DEL = "\x7f"

    TERM_UP = "\x1b[A"
    TERM_DOWN = "\x1b[B"
    TERM_RIGHT = "\x1b[C"
    TERM_LEFT = "\x1b[D"

    VISUAL_UP = "\x1bOA"
    VISUAL_DOWN = "\x1bOB"
    VISUAL_RIGHT = "\x1bOC"
    VISUAL_LEFT = "\x1bOD"

    def __init__(self) -> None:
        self._buffer = []
        self._buffer_index = 0

        self._cmd_queue = queue.Queue()
        self._cmd_queue_size = 0

        self._is_in_escape_mode = False
        self._escape_sequence_buffer = []

    def _reset_buffer(self) -> None:
        self._buffer = []
        self._buffer_index = 0

    def _add_to_buffer(self, char: str) -> None:
        """Add a character to the buffer

        :param string: The character to add
        """
        if len(self._buffer) == self._buffer_index:
            self._buffer.append(char)
        else:
            self._buffer = self._buffer[:self._buffer_index] + \
                [char] + self._buffer[self._buffer_index:]
        self._buffer_index += 1

    def _handle_escape_sequence(self, sequence: str) -> None:
        if sequence == self.TERM_LEFT and self._buffer_index > 0:
            self._buffer_index -= 1  # Move the "cursor" to the left
        elif sequence == self.TERM_RIGHT and self._buffer_index+1 <= len(self._buffer):
            self._buffer_index += 1  # Mothe "cursor" to the right
        elif sequence in (self.TERM_UP, self.TERM_DOWN):
            self._buffer = []  # If you press up or down in a terminal, what
            self._buffer_index = 0  # you typed previously is lost
            # We could try to parse the history of previously parsed command
            # but this is not dealt at the moment with due to time constraints
        elif sequence in (self.VISUAL_UP, self.VISUAL_DOWN, self.VISUAL_RIGHT, self.VISUAL_LEFT):
            self._buffer = []  # If you press up or down in (seemingly) something visual
            self._buffer_index = 0  # we just reset the buffer and try to parse it
            # We could try and parse this if we wanted to
        else:
            debug_log.debug("Unsupported escape sequence recieved from attacker %s",
                            sequence.encode("utf-8"))

    def _add_to_cmd_queue(self, string: str) -> None:
        """Adds a command to the comand queue

        :param string: The command to add
        """
        self._cmd_queue.put(string)
        self._cmd_queue_size += 1

    def can_read_command(self) -> bool:
        """Returns true if there is a command to read from the command buffer

        :return: True if there is a command available to read
        """
        return self._cmd_queue_size > 0

    def read_command(self) -> str:
        """Reads the first previous unread command

        :return: The first previous unread command
        """
        self._cmd_queue_size -= 1
        return self._cmd_queue.get_nowait()

    def add_to_cmd_buffer(self, cmd: str) -> None:
        """Adds string data to the command buffer

        :param cmd: The string data to add
        """
        for char in cmd:
            # ANSI escape sequence always starts with \x1b, followed by zero or more numbers
            # seperated by ";" and ends with a letter
            # There are other weird escape sequences aswell

            # Examples here (not all are ANSI it seems)
            # http://www.manmrk.net/tutorials/ISPF/XE/xehelp/html/HID00000594.htm
            if self._is_in_escape_mode:
                sequence = ''.join(self._escape_sequence_buffer)

                # Here they've sent some weird invalid escape sequence
                if ((sequence == "\x1b" and char not in ("[", "O"))
                    or (sequence == "\x1b[" and not (char == "[" or char.isalpha() or char.isdigit()))
                        or not (char.isdigit() or char.isalpha() or char != ";")):
                    debug_log.debug("The attacker sent a weird escape sequence %s",
                                    (sequence + char).encode("utf-8"))
                    self._escape_sequence_buffer = []
                    self._is_in_escape_mode = False

                # Found the end of escape sequence
                elif len(sequence) >= 2 and char.isalpha():
                    self._handle_escape_sequence(sequence+char)
                    self._escape_sequence_buffer = []
                    self._is_in_escape_mode = False

                # Append expected escape sequence character
                else:
                    self._escape_sequence_buffer.append(char)
                continue

            # Found start of escape sequence
            if char == "\x1b":
                self._escape_sequence_buffer.append(char)
                self._is_in_escape_mode = True
            # Treat everything before \r as a command
            elif char == self.CR and len(self._buffer) > 0:
                self._add_to_cmd_queue(''.join(self._buffer))
                self._reset_buffer()
            # Pop from the cmd_buffer if we recieved delete
            elif char == self.DEL:
                if len(self._buffer) > 0:
                    self._buffer.pop()
            # Append normal character
            elif char != self.CR:
                self._add_to_buffer(char)
