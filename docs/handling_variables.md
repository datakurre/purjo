---
layout: default
title: Handling Variables
---

# Handling variables

`purjo` provides flexible mechanisms for passing data (variables) between your BPMN processes and your Robot Framework or Python tasks. This guide details how to manage these variables.

## Passing variables from BPMN to tasks

Variables defined in your BPMN process can be directly accessed within your `purjo` tasks.

### Different data types

`purjo` automatically converts common BPMN variable types to their corresponding Python/Robot Framework types.

Consider the following Robot Framework task file:

```robotframework
*** Settings ***
Library     DateTime
Library     String


*** Variables ***
${BPMN:TASK}        local

${String Input}     ${None}
${Number Input}     ${None}
${Boolean Input}    ${None}
${Date Input}       ${None}
@{List Input}       ${None}
&{Dict Input}       &{EMPTY}


*** Tasks ***
Test Variable Tpyes
    ${Date Input}=    Convert Date    ${Date Input}
    Log Variables
    VAR    ${String Output}    ${String Input}    scope=${BPMN:TASK}
    VAR    ${Number Output}    ${Number Input}    scope=${BPMN:TASK}
    VAR    ${Boolean Output}    ${Boolean Input}    scope=${BPMN:TASK}
    VAR    ${Date Output}    ${Date Input}    scope=${BPMN:TASK}
    VAR    ${List Output}    ${List Input}    scope=${BPMN:TASK}
    VAR    ${Dict Output}    ${Dict Input}    scope=${BPMN:TASK}
```

In this example, variables like `${String Input}`, `${Number Input}`, `${Boolean Input}`, `${Date Input}`, `@{List Input}`, and `&{Dict Input}` are expected to be set by the BPMN process. `purjo` ensures these are available to the Robot Framework task in the appropriate format.

## Reading external task metadata

Topic configuration can select fields from Operaton's locked external task
DTO for use in a Robot task:

```toml
[tool.purjo.topics."My Topic in BPMN"]
task-metadata = ["activityId", "createTime", "extensionProperties"]
```

These are available selections, not enabled by default: only fields listed in
`task-metadata` are exposed, and an omitted or empty list exposes none. The
field names below come from the project's locked
`operaton-tasks==1.0rc1` `LockedExternalTaskDto`; the DTO's `variables` map is
not selectable.

| `task-metadata` field | Robot variable |
|---|---|
| `activityId` | `${TASK_METADATA_ACTIVITY_ID}` |
| `activityInstanceId` | `${TASK_METADATA_ACTIVITY_INSTANCE_ID}` |
| `errorMessage` | `${TASK_METADATA_ERROR_MESSAGE}` |
| `errorDetails` | `${TASK_METADATA_ERROR_DETAILS}` |
| `executionId` | `${TASK_METADATA_EXECUTION_ID}` |
| `id` | `${TASK_METADATA_ID}` |
| `lockExpirationTime` | `${TASK_METADATA_LOCK_EXPIRATION_TIME}` |
| `processDefinitionId` | `${TASK_METADATA_PROCESS_DEFINITION_ID}` |
| `processDefinitionKey` | `${TASK_METADATA_PROCESS_DEFINITION_KEY}` |
| `processDefinitionVersionTag` | `${TASK_METADATA_PROCESS_DEFINITION_VERSION_TAG}` |
| `processInstanceId` | `${TASK_METADATA_PROCESS_INSTANCE_ID}` |
| `tenantId` | `${TASK_METADATA_TENANT_ID}` |
| `retries` | `${TASK_METADATA_RETRIES}` |
| `suspended` | `${TASK_METADATA_SUSPENDED}` |
| `workerId` | `${TASK_METADATA_WORKER_ID}` |
| `priority` | `${TASK_METADATA_PRIORITY}` |
| `topicName` | `${TASK_METADATA_TOPIC_NAME}` |
| `businessKey` | `${TASK_METADATA_BUSINESS_KEY}` |
| `extensionProperties` | `${TASK_METADATA_EXTENSION_PROPERTIES}` |
| `createTime` | `${TASK_METADATA_CREATE_TIME}` |

Each selected field is provided as a Robot variable in the variable-file
scope, using a reserved `TASK_METADATA_` prefix and a screaming-snake-case
field suffix. For example, `activityId` is `${TASK_METADATA_ACTIVITY_ID}`.
The metadata variables are separate from BPMN process/task variables; they
are not automatically written back to Operaton.

Field names must match fields on the installed `LockedExternalTaskDto`;
unknown names, duplicates, and `variables` are configuration errors. Selected
null fields remain Robot `None` values. Nested values, including
`extensionProperties`, remain dictionaries, while date/time fields are
serialized as JSON strings.

Reserve the `TASK_METADATA_` prefix for metadata; do not use it for BPMN
inputs or secret names. If a secret is nevertheless configured with a
metadata variable name, the existing secret-over-variable precedence remains
in effect, so the secret value wins. If a BPMN input collides with a metadata
variable after Robot's case/space/underscore normalization, the task fails
before Robot runs. Collision handling follows `on-fail`: `FAIL` and
`COMPLETE` produce a technical task failure (`COMPLETE` does not suppress the
collision), while `ERROR` produces a BPMN error.

## Setting variables from tasks to BPMN

You can also set variables within your tasks to be passed back to the BPMN process. `purjo` supports setting variables with specific scopes: task-local or process-global.

### Using the `VAR` keyword (Robot Framework)

In Robot Framework tasks, you can use the built-in `VAR` keyword to set variables and specify their scope.

```robotframework
    VAR    ${VariableName}    ${Value}    scope=${BPMN:TASK}
    VAR    ${AnotherVariable}    ${AnotherValue}    scope=${BPMN:PROCESS}
```

*   `scope=${BPMN:TASK}`: Sets a variable that is local to the current external task instance.
*   `scope=${BPMN:PROCESS}`: Sets a variable that is available throughout the entire BPMN process instance.

### Variables of a failed task

When a task ends in a BPMN error (`on-fail = "ERROR"`, or `on-fail = "FAIL"` with an explicit `Fail`), the `scope=${BPMN:TASK}` variables it had already set are still stored as local variables of the task, together with `log.html` and `output.xml`.

This matters for output mappings: the engine evaluates them before the error reaches its boundary event, and a mapping that refers to a variable the failed task never set breaks the error handling. Set such outputs first, to an empty value if necessary, before the step that may fail:

```robotframework
    VAR    ${result}    ${None}    scope=${BPMN:TASK}
    Step That May Fail
    VAR    ${result}    ${value}    scope=${BPMN:TASK}
```

A technical failure (`on-fail = "FAIL"` without an explicit `Fail`) stores only `log.html` and `output.xml`, so a retry does not see the outputs of the failed attempt.

### Getting and setting variables from Python

For Python-based tasks, `purjo` provides utilities to interact with BPMN variables.

```python
from pydantic import BaseModel
from robot.api import logger
from robot.libraries import BuiltIn
from typing import Literal
import json


VariableScope = Literal["BPMN:TASK", "BPMN:PROCESS"]


class InputVariables(BaseModel):
    name: str = "John Doe"


class OutputVariables(BaseModel):
    message: str


def get_variables() -> InputVariables:
    library = BuiltIn.BuiltIn()
    return InputVariables(**library.get_variables(no_decoration=True))


def set_variables(
    variables: OutputVariables, scope: VariableScope = "BPMN:PROCESS"
) -> None:
    library = BuiltIn.BuiltIn()
    try:
        if scope == "BPMN:TASK":
            for name, value in variables.model_dump().items():
{% raw %}
                library._variables.set_bpmn_task(f"${{{name}}}", value)
        else:
            for name, value in variables.model_dump().items():
                library._variables.set_bpmn_process(f"${{{name}}}", value)
{% endraw %}
    except AssertionError:
        logger.info(json.dumps(variables.model_dump(), indent=2))
```

*   **`get_variables()`**: This function retrieves all variables passed from the BPMN process and validates them against an `InputVariables` Pydantic model.
*   **`set_variables()`**: This function allows you to set output variables, which will be passed back to the BPMN engine. You can specify the `scope` (`"BPMN:TASK"` or `"BPMN:PROCESS"`) to control the visibility of these variables.

Using Pydantic models (like `InputVariables` and `OutputVariables`) is highly recommended for Python tasks as it provides strong typing and validation for your variable payloads, ensuring data integrity.
