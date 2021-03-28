
import pytest

import pytest


from frontend.protocols.command_parser import CommandParser


@pytest.fixture()
def command_parser() -> CommandParser:
    return CommandParser()


CR = "\r"
TERM_UP = "\x1b[A"
TERM_DOWN = "\x1b[B"
TERM_RIGHT = "\x1b[C"
TERM_LEFT = "\x1b[D"

VISUAL_UP = "\x1bOA"
VISUAL_DOWN = "\x1bOB"


def test_no_arrows(command_parser: CommandParser):
    cmd = "Hi"
    command_parser.add_to_cmd_buffer(cmd+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd


def test_no_arrows_several_commands(command_parser: CommandParser):
    cmd1 = "Hi "
    cmd2 = "how "
    cmd3 = "are "
    cmd4 = "you "
    cmd5 = "doing"
    command_parser.add_to_cmd_buffer(cmd1+CR)
    command_parser.add_to_cmd_buffer(cmd2+CR)
    command_parser.add_to_cmd_buffer(cmd3+CR)
    command_parser.add_to_cmd_buffer(cmd4+CR)
    command_parser.add_to_cmd_buffer(cmd5+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd1
    assert command_parser.read_command() == cmd2
    assert command_parser.read_command() == cmd3
    assert command_parser.read_command() == cmd4
    assert command_parser.read_command() == cmd5
    assert command_parser.can_read_command() == False


def test_no_arrows_one_big_command(command_parser: CommandParser):
    cmd1 = "Hi "
    cmd2 = "how "
    cmd3 = "are "
    cmd4 = "you "
    cmd5 = "doing"
    command_parser.add_to_cmd_buffer(cmd1)
    command_parser.add_to_cmd_buffer(cmd2)
    command_parser.add_to_cmd_buffer(cmd3)
    command_parser.add_to_cmd_buffer(cmd4)
    command_parser.add_to_cmd_buffer(cmd5+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd1+cmd2+cmd3+cmd4+cmd5
    assert command_parser.can_read_command() == False


def test_single_arrow(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer(TERM_LEFT+CR)
    assert command_parser.can_read_command() == False


def test_multiple_arrows(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer(TERM_RIGHT+TERM_RIGHT+TERM_RIGHT+CR)
    assert command_parser._buffer_index == 0
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_at_end(command_parser: CommandParser):
    cmd = "AB"
    command_parser.add_to_cmd_buffer(TERM_LEFT+TERM_LEFT+cmd+TERM_RIGHT+TERM_RIGHT+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_one(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_LEFT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ACB"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_two(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_LEFT+TERM_LEFT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "CAB"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_three(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_RIGHT+TERM_LEFT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ACB"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_four(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_RIGHT+TERM_LEFT+TERM_LEFT+TERM_RIGHT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ACB"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_five(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_LEFT+TERM_RIGHT+TERM_RIGHT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ABC"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_six(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    command_parser.add_to_cmd_buffer(TERM_LEFT+TERM_LEFT+TERM_RIGHT+TERM_RIGHT)
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ABC"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_seven(command_parser: CommandParser):
    command_parser.add_to_cmd_buffer("AB")
    # Send left arrow in chunks
    command_parser.add_to_cmd_buffer(TERM_LEFT[0])
    command_parser.add_to_cmd_buffer(TERM_LEFT[1])
    command_parser.add_to_cmd_buffer(TERM_LEFT[2])
    command_parser.add_to_cmd_buffer("C"+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "ACB"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_eight(command_parser: CommandParser):
    cmd1 = "\x54\x68\x69\x73 is a \n"
    cmd2 = " very weird \n\n\n test"
    cmd3 = "But it should work"
    command_parser.add_to_cmd_buffer(cmd1+cmd2+CR)
    command_parser.add_to_cmd_buffer(cmd3+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd1+cmd2
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == cmd3
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_nine(command_parser: CommandParser):
    cmd = "\n"+TERM_LEFT+"hi" + TERM_RIGHT+TERM_RIGHT+TERM_RIGHT+"there"
    command_parser.add_to_cmd_buffer(cmd+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "hi\nthere"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_ten(command_parser: CommandParser):
    cmd = "E" + TERM_LEFT + "H" + TERM_RIGHT + "O" + TERM_LEFT + "LL"
    command_parser.add_to_cmd_buffer(cmd+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "HELLO"
    assert command_parser.can_read_command() == False


def test_cmd_and_arrows_eleven(command_parser: CommandParser):
    cmd1 = "This is " + TERM_UP
    cmd2 = "the " + VISUAL_UP
    cmd3 = "final " + VISUAL_DOWN
    cmd4 = "test"
    command_parser.add_to_cmd_buffer(cmd1)
    command_parser.add_to_cmd_buffer(cmd2)
    command_parser.add_to_cmd_buffer(cmd3)
    command_parser.add_to_cmd_buffer(cmd4+CR)
    assert command_parser.can_read_command() == True
    assert command_parser.read_command() == "test"
    assert command_parser.can_read_command() == False
