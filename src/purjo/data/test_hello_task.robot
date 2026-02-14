*** Settings ***
Library             RobotLibrary

Task Template       Test Hello


*** Variables ***
${message}      Hello World


*** Tasks ***    NAME
Hello John    John Doe
Hello Jane    Jane Doe
Hello Zoe    Zoe Doe


*** Keywords ***
Test Hello
    [Arguments]    ${name}
    Run Robot Task    ${CURDIR}/hello.robot
    ...    My Task in Robot
    ...    BPMN:PROCESS=global
    ...    name=${name}
    Should be equal    ${message}    Hello ${name}!
