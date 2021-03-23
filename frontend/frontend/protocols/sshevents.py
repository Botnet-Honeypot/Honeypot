

class ServerEvent:
    """Superclass representing events that an SSH server can trigger
    """


class ShellRequest(ServerEvent):
    """A class representing a shell request event
    """


class ExecRequest(ServerEvent):
    """A class representing an exec request event
    """

    def __init__(self, command: bytes) -> None:
        self._command = command

    def get_command(self) -> bytes:
        """Returns the command associated with the exec request

        :return: The command
        """
        return self._command
