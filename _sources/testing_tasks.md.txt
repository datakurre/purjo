---
layout: default
title: Testing Tasks
---

# Testing tasks

You can test `purjo` Robot Framework tasks without running Operaton (or any BPM engine) using two complementary approaches:

- **Integration testing**: Use `robotframework-robotlibrary` to run a task/test from another `.robot` file and verify variable behavior in-process.
- **Functional testing**: Use the `purjo` Robot Framework library to execute a configured topic and get output variables back as a dictionary.

Both approaches are fast and local. Pick integration tests for “does this Robot suite behave as expected when called with variables?”, and functional tests for “does my `pyproject.toml` topic config + `purjo` execution produce the right BPMN-style outputs?”

## Integration testing (RobotLibrary)

`RobotLibrary` is a Robot Framework library for meta-testing: it lets you write Robot Framework tests that execute tests/tasks from another `.robot` file.

This style is especially useful with `purjo` packages because:

- your task inputs are already expressed as suite variables (e.g. `${name}`), and
- you can override those variables as keyword arguments when calling `Run Robot Test` / `Run Robot Task`.

### Installing

Add `robotframework-robotlibrary` as a development dependency in your robot package:

```console
uv add --dev robotframework-robotlibrary>=1.0a3
```

If you created your package using `pur init`, this dependency and a ready-made example test (`test_hello.robot`) are already included.

### How input variables are mapped

`RobotLibrary` provides these keywords:

```robotframework
Run Robot Test    suite_path    test_name    **variables
Run Robot Task    suite_path    task_name    **variables
```

The `**variables` part is passed as `NAME=value` pairs. Each pair overrides the corresponding suite variable in the target suite.

In other words, a call like:

```robotframework
Run Robot Test    ${CURDIR}/hello.robot    My Test in Robot
...    name=John Doe
...    answer=42
```

overrides `${name}` and `${answer}` inside `hello.robot` for that run.

If you have inputs as a dictionary, you can expand it into keyword arguments:

```robotframework
&{inputs}=    Create Dictionary    name=John Doe    answer=42
Run Robot Test    ${CURDIR}/hello.robot    My Test in Robot
...    &{inputs}
```

### Making output variables assertable (BPMN:PROCESS=global)

The default `purjo` task fixtures typically set:

```robotframework
${BPMN:PROCESS}     local
```

and then emit output variables using Robot Framework’s built-in `VAR` keyword:

```robotframework
VAR    ${message}    ${message}    scope=${BPMN:PROCESS}
```

When you run the target suite via `RobotLibrary`, output variables written with `VAR ... scope=${BPMN:PROCESS}` are easiest to assert from the calling (meta) test when the scope is set to **global process scope**. In the default fixture, you enable that by overriding `${BPMN:PROCESS}`:

```robotframework
Run Robot Test    ${CURDIR}/hello.robot    My Test in Robot
...    BPMN:PROCESS=global
...    name=${name}
Should Be Equal    ${message}    Hello ${name}!
```

That `BPMN:PROCESS=global` is just another variable override: it sets `${BPMN:PROCESS}` inside the called suite so that `VAR ... scope=${BPMN:PROCESS}` writes variables to a scope that the meta-test can assert afterwards.

### Example (from the init fixture)

The default `pur init` Robot template includes an integration test like this:

```robotframework
*** Settings ***
Library             RobotLibrary

Test Template       Test Hello


*** Test Cases ***    NAME
Hello John      John Doe
Hello Jane      Jane Doe


*** Keywords ***
Test Hello
    [Arguments]    ${name}
    Run Robot Test    ${CURDIR}/hello.robot
    ...    My Test in Robot
    ...    BPMN:PROCESS=global
    ...    name=${name}
    Should Be Equal    ${message}    Hello ${name}!
```

## Functional testing (purjo library)

`purjo` includes a Robot Framework library, also named `purjo`, which executes a configured topic from a robot package and returns the resulting output variables.

Use this when you want to validate:

- topic configuration in `pyproject.toml` (`[tool.purjo.topics."..."]`),
- variable mapping in/out as the engine would do it,
- error handling behavior (`on-fail`), and
- secrets handling.

## The `purjo` Library

The `purjo` library allows you to execute tasks defined in your project as if they were being called by the BPM engine, but locally within a Robot Framework test suite. This is crucial for verifying task logic, variable mapping, and error handling before deployment.

### `Get Output Variables`

The core keyword provided by the library is `Get Output Variables`. It executes a specific task (identified by its topic) from a robot package using a set of input variables and returns the resulting output variables.

#### Syntax

```robotframework
Get Output Variables    path=<path_to_package>    topic=<topic_name>    variables=<input_variables_dict>    secrets=<secrets_dict>
```

*   `path`: Path to the robot package. This can be the current directory (`.`) during development or a path to a packaged `robot.zip` file.
*   `topic`: The BPMN topic name as configured in your `pyproject.toml` file (under `[tool.purjo.topics."<Topic Name>"]`).
*   `variables`: A dictionary containing the input variables that the task expects.
*   `secrets`: (Optional) A dictionary containing the secrets that the task expects.

#### Example

Suppose you have a task configured for the topic "My Topic in BPMN" that expects a `name` variable and returns a `message` variable. You can test it as follows:

```robotframework
*** Settings ***
Library    purjo
Library    Collections

*** Tasks ***
Test My Task
    # Define input variables
    &{inputs}=    Create Dictionary    name=Alice

    # Execute the task locally
    &{outputs}=   Get Output Variables    path=.    topic=My Topic in BPMN    variables=${inputs}

    # Verify the output
    Should Be Equal    ${outputs}[message]    Hello, Alice!
```

In this example:
1.  We import the `purjo` library.
2.  We create a dictionary `&{inputs}` with the test data.
3.  We call `Get Output Variables`, pointing to the current directory (`.`) and the specific topic.
4.  We assert that the returned `message` in `&{outputs}` matches our expectation.

This approach allows you to build a comprehensive regression test suite for your BPMN tasks, ensuring they behave correctly with various inputs and edge cases.

### Testing with Secrets

If your task requires secrets, you can pass them as a dictionary using the `secrets` argument.

For example, consider a task defined in `hello/hello.robot` that uses a secret variable:

```robotframework
*** Variables ***
${BPMN:PROCESS}     local
${name}             n/a
${birthday}

*** Test Cases ***
My Test in Robot
    VAR    ${message}    John's birthday is ${birthday.value}    scope=${BPMN:PROCESS}
```

And its configuration in `hello/pyproject.toml`:

```toml
[tool.purjo.topics."My Topic in BPMN"]
name = "My Test in Robot"
on-fail = "ERROR"
process-variables = true
```

You can test this task as follows:

```robotframework
*** Settings ***
Library     purjo
Library     Collections


*** Variables ***
&{Input Variables}              name=John
&{Expected Output Variables}    message=John's birthday is tomorrow
&{Secret Variables}             birthday=tomorrow


*** Test Cases ***
Test Hello World
    ${Output Variables}=    Get Output Variables    ${CURDIR}${/}hello    My Topic in BPMN    ${Input Variables}   ${Secret Variables}
    Dictionaries Should Be Equal    ${Output Variables}    ${Expected Output Variables}
```

