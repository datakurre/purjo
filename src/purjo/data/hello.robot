*** Settings ***

Library    Hello

*** Variables ***

${BPMN}    local
${name}    n/a

*** Tasks ***

My Task
    ${message}=    Hello    ${name}
    VAR    ${message}    ${message}    scope=${BPMN}
