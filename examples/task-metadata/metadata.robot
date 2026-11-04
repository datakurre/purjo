*** Variables ***
${BPMN:PROCESS}    BPMN:PROCESS


*** Test Cases ***
Read task metadata
    Should Be Equal    ${TASK_METADATA_ACTIVITY_ID}    MetadataTask
    Should Be Equal    ${TASK_METADATA_TOPIC_NAME}    Task Metadata
    Should Not Be Equal    ${TASK_METADATA_CREATE_TIME}    ${None}
    Should Be Equal    ${TASK_METADATA_BUSINESS_KEY}    invoice-42
    Log    ${TASK_METADATA_ACTIVITY_ID}    console=${True}
    Log    ${TASK_METADATA_TOPIC_NAME}    console=${True}
    Log    ${TASK_METADATA_CREATE_TIME}    console=${True}
    Log    ${TASK_METADATA_BUSINESS_KEY}    console=${True}
    VAR    ${metadata_activity_id}    ${TASK_METADATA_ACTIVITY_ID}    scope=${BPMN:PROCESS}
    VAR    ${metadata_topic_name}    ${TASK_METADATA_TOPIC_NAME}    scope=${BPMN:PROCESS}
    VAR    ${metadata_create_time}    ${TASK_METADATA_CREATE_TIME}    scope=${BPMN:PROCESS}
    VAR    ${metadata_business_key}    ${TASK_METADATA_BUSINESS_KEY}    scope=${BPMN:PROCESS}
