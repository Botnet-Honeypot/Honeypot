*** Settings ***
Documentation     Some documentation.

*** Test Cases ***
Connect to frontend and send some commands
    Push button    1
    Result should be    1