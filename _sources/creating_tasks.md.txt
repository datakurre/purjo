---
layout: default
title: Creating Tasks
---

# Creating tasks

This guide explains how to create tasks that can be orchestrated by `purjo` using either traditional Robot Framework keyword libraries or a more advanced pure Python approach.

## Basic task (Robot Framework)

The most common way to define tasks in `purjo` is by using Robot Framework keyword libraries. This involves creating a Python file with your custom keywords and a `.robot` file to define the task suite.

### Example: The "Hello" task

Here is a basic illustration.

#### `Hello.py` (Keyword library)

```python
from robot.api.deco import keyword
from robot.api.deco import library


@library()
class Hello:
    @keyword()
    def hello(self, name: str) -> str:
        return f"Hello {name}!"
```

This Python file defines a simple Robot Framework library named `Hello` with one keyword: `hello`. This keyword takes a `name` and returns a greeting string.

#### `hello.robot` (Task suite)

```robotframework
*** Settings ***
Library    Hello

*** Tasks ***
My Task in Robot
    ${greeting}=    Hello    World
    Log To Console    ${greeting}
```

The `hello.robot` file imports the `Hello` library and defines a task named "My Task in Robot". This task calls the `hello` keyword, passes "World" as the name, and logs the returned greeting to the console.

#### `hello.bpmn` (BPMN process)

Your BPMN process would then include an external service task that references this Robot Framework task. For instance, a service task with `Topic` "My Topic in BPMN" might be configured to execute "My Task in Robot" from `hello.robot`.

### Configuration

To map the BPMN topic to the Robot Framework task, you need to configure `pyproject.toml`.

```toml
[tool.purjo.topics."My Topic in BPMN"]
name = "My Task in Robot"
on-fail = "ERROR"
process-variables = true
pythonpath = ["./libs", "./modules"]
```

*   `[tool.purjo.topics."<Topic Name>"]`: Defines the configuration for a specific BPMN topic.
*   `name`: The name of the Robot Framework task (or Python function) to execute.
*   `on-fail`: Determines the behavior when the task fails (e.g., "ERROR", "FAIL").
*   `process-variables`: If `true`, process variables are passed to the task. If `false`, only task scope variables are passed to the task.
*   `pythonpath`: (Optional) A list of additional paths to add to Robot Framework's `--pythonpath`. This allows importing custom libraries and modules from specified directories.

## Advanced task (Pure Python)

`purjo` also supports defining tasks directly in Python, allowing for more complex logic and direct integration with Python's type hinting and data validation features like Pydantic. This approach can replace the need for a separate `.robot` file for simple tasks.

### Example: A pure Python task

This approach is demonstrated below.

#### `tasks.py` (Pure Python task)

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


def main():
    variables = get_variables()
    set_variables(OutputVariables(message=f"Hello, {variables.name}!"))


if __name__ == "__main__":
    from purjo import PythonParser
    from robot import run

    run(__file__, parser=PythonParser("tasks.main"))
```

#### Key features:

*   **Pydantic Models (`InputVariables`, `OutputVariables`)**: These models enforce strict typing and validation for variables exchanged with the BPMN engine, making your task more robust.
*   **`get_variables()` and `set_variables()`**: Helper functions to easily retrieve input variables from the BPMN process and set output variables back to it.
*   **`main()` Function**: Encapsulates the core logic of your task. It retrieves variables, performs operations, and sets new variables.
*   **`if __name__ == "__main__":` Block**: This block enables the Python script to be executed directly as a Robot Framework task using `purjo`'s `PythonParser`. This means you can specify `tasks.main` as the Robot Framework task to be executed by your BPMN process, without needing a separate `.robot` file.

This advanced approach is particularly useful for tasks that are primarily Python-based, requiring minimal or no Robot Framework specific syntax beyond what `purjo` provides for variable handling.

### Configuration

To map the BPMN topic to the Pure Python task, you need to configure `pyproject.toml`.

```toml
[tool.purjo.topics."My Topic in BPMN"]
name = "tasks.main"
on-fail = "FAIL"
process-variables = true
```

*   `name`: The name of the Python function to execute, in the format `module.function`. In this example, `tasks.main` refers to the `main` function in `tasks.py`.

## Adding dependencies

When your tasks require external Python libraries (e.g., `requests`, `pandas`, `PyPDF2`), you need to add them to your project's dependencies. `purjo` uses `uv` for dependency management.

To add a dependency, use the `uv add` command:

```console
$ uv add requests
```

This command updates your `pyproject.toml` file and the `uv.lock` file, ensuring that the dependency is available when your tasks are executed.

## Packaging

Once your tasks are ready, you can package them into a `robot.zip` file using the `pur wrap` command.

```console
$ pur wrap
```

This command creates a `robot.zip` file containing your project files, excluding those specified in `.wrapignore` (and default exclusions like `.git`, `__pycache__`, etc.). This zip file can be deployed to an external worker or used for distribution.

## Creating BPMN resources

`purjo` provides a convenient way to create new BPMN, DMN, and Form files using the `pur operaton create` command.

```console
$ pur operaton create my-process.bpmn
$ pur operaton create my-decision.dmn
$ pur operaton create my-form.form
```

This generates template files with unique IDs, ready for editing in any bpmn.io-compatible modeler.
