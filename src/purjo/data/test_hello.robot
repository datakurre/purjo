*** Settings ***
Library             RobotLibrary

Test Template       Test Hello


*** Variables ***
${message}      Hello World


*** Test Cases ***    NAME
Hello John      John Doe
Hello Jane      Jane Doe
Hello Zoe       Zoe Doe


*** Keywords ***
Test Hello
    [Arguments]    ${name}
    Run Robot Test    ${CURDIR}/hello.robot
    ...    My Test in Robot
    ...    BPMN:PROCESS=global
    ...    name=${name}
    Should be equal    ${message}    Hello ${name}!
