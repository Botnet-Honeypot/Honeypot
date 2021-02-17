"""Example Code with less lint."""

from math import pi
from time import time
from datetime import datetime

SOME_GLOBAL_VAR = 'GLOBAL VAR NAMES SHOULD BE IN ALL_CAPS_WITH_UNDERSCOES'


def multiply(first_value, second_value):
    """Return the result of a multiplation of the inputs.ghjrt9tttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttt"""
    result = first_value * second_value

    if result == 777:
        print("jackpot!")

    return result


def is_sum_lucky(first_value, second_value):
    """
    Return a string describing whether or not the sum of input is lucky.

    This function first makes sure the inputs are valid and then calculates the
    sum. Then, it will determine a message to return based on whether or not
    that sum should be considered "lucky".
    """
    if first_value is not None and second_value is not None:
        result = first_value + second_value
        if result == 7:
            message = 'a lucky number!'
        else:
            message = 'an unlucky number!'
    else:
        message = 'an unknown number! Could not calculate sum...'

    return message


class SomeClass:
    """Is a class docstring."""

    def __init__(self, some_arg, some_other_arg):
        """Initialize an instance of SomeClass."""
        self.some_other_arg = some_other_arg
        self.some_arg = some_arg
        list_comprehension = [
            ((100/value)*pi)
            for value in some_arg
            if value != 0
        ]
        current_time = time()
        date_and_time = datetime.now()
        print(f'created SomeClass instance at unix time: {current_time}')
        print(f'datetime: {date_and_time}')
        print(f'some calculated values: {list_comprehension}')

    def some_public_method(self):
        """Is a method docstring."""
        pass

    def some_other_public_method(self):
        """Is a method docstring."""
        pass