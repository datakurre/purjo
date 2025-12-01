---
layout: default
title: Testing Tasks
---

# Testing tasks

`purjo` includes a Robot Framework library, also named `purjo`, which facilitates testing your tasks in isolation without needing a running BPM engine.

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

