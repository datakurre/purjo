# AGENTS.md

## Purpose

Guidance for LLM coding agents working on this **robot package**: how to read it,
extend it, and verify the result without guessing.

This package is a [Robot Framework](https://robotframework.org/) suite plus its
dependencies and configuration, executed as an **external service task** of an
[Operaton](https://operaton.org/) BPMN process. The `pur serve` worker long-polls
the engine for tasks on a *topic*, runs the mapped Robot task, and reports the
output variables (or the error) back to the engine.

Vocabulary: say *Operaton* (not Camunda), *robot package* (not robot.zip),
*external task* (not job).

---

## Repository map

| Path | Role |
|------|------|
| `pyproject.toml` | Dependencies (managed by `uv`) and the `[tool.purjo.topics]` mapping |
| `hello.robot` | The Robot suite executed by the BPMN service task |
| `Hello.py` | Robot keyword library imported by `hello.robot` |
| `test_hello.robot` | Integration test that runs `hello.robot` in-process |
| `hello.bpmn` | The BPMN process containing the external service task |
| `Makefile` | `make help` lists every target |
| `uv.lock` | Resolved dependency graph — generated, never hand-edited |
| `.wrapignore` | Gitignore-style excludes for `pur wrap` |
| `AGENTS.md` | This file |

---

## The central contract: topic to test mapping

Three names must agree. Renaming one means renaming all three.

```toml
# pyproject.toml
[tool.purjo.topics."My Topic in BPMN"]
name = "My Task in Robot"
on-fail = "ERROR"
process-variables = true
```

1. The table key `"My Topic in BPMN"` must equal `camunda:topic` on the
   `bpmn:serviceTask` in `hello.bpmn`.
2. `name` must equal the task name under `*** Tasks ***` in `hello.robot`,
   character for character.
3. `pur serve .` reads this table to decide what to run for an incoming task.

Fields:

- `name` — the Robot task name to execute.
- `on-fail` — `ERROR`, `FAIL` or `COMPLETE` (see *Failure semantics*).
- `process-variables` — `true` passes all process variables to the test;
  `false` passes only task-scope variables.
- `pythonpath` — optional list of extra directories added to Robot's
  `--pythonpath`, e.g. `pythonpath = ["./libs", "./modules"]`.

---

## Variables

### Inputs

Every variable the engine may send must be declared with a default under
`*** Variables ***`. Undeclared variables are not available to the test.

```robotframework
*** Variables ***
${BPMN:PROCESS}     local
${name}             n/a
```

Types are converted for you: strings, numbers, booleans, dates, lists (`@{...}`)
and dictionaries (`&{...}`). Declare list and dict inputs with matching sigils,
e.g. `@{List Input}` and `&{Dict Input}    &{EMPTY}`.

### Outputs

Emit results with Robot's built-in `VAR` keyword and a BPMN scope:

```robotframework
VAR    ${message}    Hello ${name}!    scope=${BPMN:PROCESS}
```

- `scope=${BPMN:PROCESS}` — visible for the rest of the process instance.
- `scope=${BPMN:TASK}` — local to this external task only.

Keep `${BPMN:PROCESS}    local` declared as a suite variable. That default is
what lets tests override the scope (see *Testing*); do not delete it.

---

## Failure semantics

`on-fail` decides what a failing task does to the process:

| Value | Effect |
|-------|--------|
| `ERROR` | Raises a BPMN error, catchable by an error boundary event (default here) |
| `FAIL` | Reports an engine task failure, consuming a retry |
| `COMPLETE` | Completes the task anyway, with `errorCode` / `errorMessage` as output variables |

When failing deliberately, use the convention from `hello.robot`: the first line
of the failure message is the **error code**, the remaining lines are the
**error message**.

```robotframework
${errorCodeAndMessage}=    Catenate    SEPARATOR=\n
...    Bad luck
...    You rolled ${dice}, which is less than ${threshold}.
Fail    ${errorCodeAndMessage}
```

---

## Secrets

Secrets are configured per profile and injected as variables:

```toml
[tool.purjo.secrets.default]
provider = "file"
path = "secrets.json"

[tool.purjo.secrets.prod]
provider = "vault"
path = "secret/my-app"
mount-point = "secret"
```

Select one with `pur serve --secrets prod .`, or point at a file directly with
`pur serve --secrets ./my-secrets.json .`. The `vault` provider needs
`VAULT_ADDR` and `VAULT_TOKEN` in the environment.

Rules:

- **Never** commit `secrets.json` or any other secrets file. Add it to
  `.gitignore`.
- **Never** log a secret value, and never write one into an output variable.
- With `robotframework >= 7.4b2` secrets arrive as `Secret` objects that mask
  themselves in logs; read the value with `${api_key.value}`.

---

## Commands

```console
$ make help                                  # list all targets
$ make test                                  # uv run --group dev robot test_hello.robot
$ make dist                                  # test, then pur wrap
$ make run                                   # deploy, start a process instance, serve

$ uv add requests                            # add a runtime dependency
$ uv add --dev robotframework-robotlibrary   # add a development dependency

$ pur wrap                                   # build robot.zip
$ pur wrap --offline                         # ... with dependencies cached inside
$ pur operaton create my-process.bpmn        # new .bpmn, .dmn or .form with fresh IDs
$ pur operaton deploy hello.bpmn             # deploy resources to the engine
$ pur run hello.bpmn --variables '{"name": "Alice"}'
$ pur serve .                                # run the external task worker
```

The engine is addressed through `ENGINE_REST_BASE_URL` (default
`http://localhost:8080/engine-rest`) and `ENGINE_REST_AUTHORIZATION`, or the
equivalent `--base-url` / `--authorization` options.

Dependencies always go through `uv`, which updates `pyproject.toml` and
`uv.lock` together. Never edit `uv.lock` by hand.

---

## Testing

Both styles run locally, with no BPM engine involved. Run them with `make test`.

### Integration tests: does the suite behave with these variables?

`RobotLibrary` runs a task from another `.robot` file. Input variables are passed
as `NAME=value` pairs that override the target suite's variables — including
`BPMN:PROCESS`, which is how outputs become assertable from the calling suite.

```robotframework
*** Settings ***
Library             RobotLibrary

Task Template       Test Hello


*** Tasks ***    NAME
Hello John    John Doe
Hello Jane    Jane Doe


*** Keywords ***
Test Hello
    [Arguments]    ${name}
    Run Robot Task    ${CURDIR}/hello.robot
    ...    My Task in Robot
    ...    BPMN:PROCESS=global
    ...    name=${name}
    Should Be Equal    ${message}    Hello ${name}!
```

`BPMN:PROCESS=global` is an ordinary variable override: it makes
`VAR ... scope=${BPMN:PROCESS}` write to global scope, so the calling suite can
assert `${message}` afterwards.

### Functional tests: does the topic configuration produce the right outputs?

The `purjo` library executes a configured topic the way the engine would, and
returns the output variables as a dictionary. Use it to verify the
`[tool.purjo.topics]` mapping, variable conversion, `on-fail` behaviour and
secrets handling.

```robotframework
*** Settings ***
Library     purjo
Library     Collections


*** Tasks ***
Test My Topic
    &{inputs}=    Create Dictionary    name=Alice
    &{outputs}=    Get Output Variables    path=.    topic=My Topic in BPMN
    ...    variables=${inputs}
    Should Be Equal    ${outputs}[message]    Hello Alice!
```

`Get Output Variables` takes `path` (a directory with `pyproject.toml`, or a
`robot.zip`), `topic`, `variables`, and optionally `secrets`. On failure the
returned dictionary contains `errorCode` and `errorMessage`.

Add `purjo` as a development dependency before using this library:
`uv add --dev purjo`.

---

## Work loop

1. State the goal in one sentence.
2. Read `pyproject.toml` (the topics table), `hello.robot`, and
   `test_hello.robot`. They define the current contract.
3. Extend `test_hello.robot` first, so the expected behaviour is executable.
4. Implement the change in `hello.robot` / `Hello.py`.
5. Run `make test`.
6. Run `make dist` before shipping.

---

## Rules

- Keep the topic key, the `name` field, and `camunda:topic` in `hello.bpmn` in sync.
- Declare every new input variable with a default under `*** Variables ***`.
- Add dependencies with `uv add`; never hand-edit `uv.lock`.
- Edit `.bpmn`, `.dmn` and `.form` files with a bpmn.io-compatible modeler, or
  create them with `pur operaton create`. Hand-editing the XML breaks the
  diagram references.
- Do not commit `secrets.json`, `robot.zip`, `.venv`, `output.xml`, `log.html`
  or `report.html`.
- Keep new files out of the deployed package by listing them in `.wrapignore`.

---

## Escalation

Stop and ask rather than guessing when:

- `hello.bpmn` and `pyproject.toml` disagree about the topic name.
- A change would alter the output variables another BPMN task depends on.
- A required credential, engine URL, or external service is unavailable.
- The intended behaviour is ambiguous and more than one reading is plausible.

---

## Further reading

- Robot Framework: <https://robotframework.org/>
- Operaton: <https://operaton.org/>
- uv: <https://docs.astral.sh/uv/>
