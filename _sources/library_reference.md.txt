---
layout: default
title: Library Reference
---

# Library reference

`purjo` includes a Robot Framework library named `purjo` to assist with testing and development.

## Importing

```robotframework
*** Settings ***
Library    purjo
```

## Keywords

### `Get Output Variables`

Executes a specific task (topic) from a robot package using a set of input variables and returns the resulting output variables. This keyword simulates the execution of an external task by the BPM engine, allowing you to test your task logic in isolation.

**Arguments:**

*   `path`: The path to the robot package. This can be a directory containing `pyproject.toml` or a packaged `robot.zip` file.
*   `topic`: The name of the BPMN topic to execute, as defined in the `[tool.purjo.topics]` section of `pyproject.toml`.
*   `variables`: A dictionary containing the input variables to pass to the task. These simulate the process variables that would be sent by the BPM engine.
*   `log_level`: (Optional) The logging level to use during execution. Default is `DEBUG`.

**Returns:**

*   A dictionary containing the output variables returned by the task. If the task fails, the dictionary will include `errorCode` and `errorMessage` keys.

**Example:**

```robotframework
*** Settings ***
Library    purjo
Library    Collections

*** Tasks ***
Test Hello Task
    # Define input variables
    &{inputs}=    Create Dictionary    name=World

    # Execute the task defined for topic "My Topic in BPMN" in the current directory
    &{outputs}=   Get Output Variables    path=.    topic=My Topic in BPMN    variables=${inputs}

    # Verify the output
    Dictionary Should Contain Key    ${outputs}    message
    Should Be Equal    ${outputs}[message]    Hello, World!
```
