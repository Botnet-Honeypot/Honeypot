*** Settings ***
Documentation     Some documentation.

*** Test Cases ***
Start whole system and send some commands
    Push button    1
    Result should be    1