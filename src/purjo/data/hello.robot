*** Settings ***
Library     Hello.py
Library     random


*** Variables ***
${BPMN:PROCESS}     local
${name}             n/a
# Roll below this fails the run, to demonstrate BPMN error handling.
# The bundled test suite overrides it to 0 for a deterministic run.
${threshold}        ${3}


*** Test Cases ***
My Test in Robot
    ${dice}=    Randint    ${1}    ${6}
    IF    ${dice} < ${threshold}
        ${errorCodeAndMessage}=    Catenate    SEPARATOR=\n
        ...    Bad luck
        ...    You rolled ${dice}, which is less than ${threshold}.
        Fail    ${errorCodeAndMessage}
    END
    ${message}=    Hello    ${name}
    Should Be Equal    ${message}    Hello ${name}!
    VAR    ${message}=    ${message}    scope=${BPMN:PROCESS}
