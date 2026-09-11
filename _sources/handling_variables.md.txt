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
