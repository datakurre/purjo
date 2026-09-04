*** Settings ***
Library     Hello.py
Library     random


*** Variables ***
${BPMN:PROCESS}     local
${name}             n/a


*** Test Cases ***
My Test in Robot
    ${dice}=    Randint    ${1}    ${6}
    IF    ${dice} < 3
        ${errorCodeAndMessage}=    Catenate    SEPARATOR=\n
        ...    Bad luck
        ...    You rolled ${dice}, which is less than 3.
        Fail    ${errorCodeAndMessage}
    END
    ${message}=    Hello    ${name}
    Should Be Equal    ${message}    Hello ${name}!
    VAR    ${message}    ${message}    scope=${BPMN:PROCESS}
