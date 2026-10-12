# `pur`(jo)

`pur`(jo) (*/ˈpurjo/*)  is an experimental command line tool for orchestrating [Robot Framework](https://robotframework.org/) test or task suites with the [Operaton](https://operaton.org/) BPM engine. It long-polls external service tasks from the Operaton engine, executes mapped Robot Framework test and task suites with the [uv](https://docs.astral.sh/uv/) Python environment manager, and finally reports the results or errors back to the engine.

## CLI

```
 Usage: pur [OPTIONS] COMMAND [ARGS]...

 pur(jo) is a tool for managing and serving robot packages.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ serve     Serve robot.zip packages (or directories) as BPMN service tasks.   │
│ init      Initialize a new robot package into the current directory.         │
│ wrap      Wrap the current directory into a robot.zip package.               │
│ run       Deploy process resources to BPM engine and start a new instance.   │
│ operaton  BPM engine operations as distinct sub commands (also as "bpm").    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

```
 Usage: pur serve [OPTIONS] {robots}...

 Serve robot.zip packages (or directories) as BPMN service tasks.

╭─ Arguments ──────────────────────────────────────────────────────────────────────╮
│ *    robots      <path>  [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────╮
│ --base-url             <str>                  [env var: ENGINE_REST_BASE_URL]    │
│                                               [default:                          │
│                                               http://localhost:8080/engine-rest] │
│ --authorization        <str>                  [env var:                          │
│                                               ENGINE_REST_AUTHORIZATION]         │
│ --secrets              <str>                  [env var: TASKS_SECRETS_PROFILE]   │
│ --timeout              <int>                  [env var:                          │
│                                               ENGINE_REST_TIMEOUT_SECONDS]       │
│                                               [default: 20]                      │
│ --poll-ttl             <int>                  [env var:                          │
│                                               ENGINE_REST_POLL_TTL_SECONDS]      │
│                                               [default: 10]                      │
│ --lock-ttl             <int>                  [env var:                          │
│                                               ENGINE_REST_LOCK_TTL_SECONDS]      │
│                                               [default: 30]                      │
│ --max-jobs             <int>                  [default: 1]                       │
│ --worker-id            <str>                  [env var: TASKS_WORKER_ID]         │
│                                               [default: operaton-robot-runner]   │
│ --log-level            <str>                  [env var: LOG_LEVEL]               │
│                                               [default: DEBUG]                   │
│ --on-fail              <FAIL|COMPLETE|ERROR>  [default: FAIL]                    │
│ --help                                        Show this message and exit.        │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

## Usage

Start Operaton:

```console
$ podman run --rm -ti -p 8080:8080 operaton/operaton:latest
```

Create workspace:

```console
$ mkdir hello-world
$ cd hello-world
```

Init project:

```console
$ uv run --with=purjo -- pur init
Adding pyproject.toml
Adding README.md
Adding Hello.py
Adding hello.robot
Adding uv.lock
Adding Makefile
Adding hello.bpmn
Adding test_hello.robot
Adding src/hello_world/__init__.py
```

The generated `Makefile` wraps the common commands; run `make help` to list them.

Or init with Robot Framework task template (uses `*** Tasks ***` instead of `*** Test Cases ***`):

```console
$ uv run --with=purjo -- pur init --task
```

Or add an `AGENTS.md` guide for LLM coding agents working on the package (not supported with `--python`):

```console
$ uv run --with=purjo -- pur init --agents
...
Adding AGENTS.md
```

Deploy and start an example process:

```console
$ uv run --with=purjo -- pur run hello.bpmn
Started: http://localhost:8080/operaton/app/cockpit/default/#/process-instance/36228e79-e97e-11ef-a0ec-52f4bfd829ae/runtime
```

Serve the project as external task worker:

```console
$ uv run --with=purjo -- pur serve .
... | INFO | ... | Scheduling My Topic in BPMN:3622b58f-e97e-11ef-a0ec-52f4bfd829ae.
==============================================================================
Tmpdlb85Jrp
==============================================================================
Tmpdlb85Jrp.Hello
==============================================================================
My Test in Robot                                                      | PASS |
------------------------------------------------------------------------------
Tmpdlb85Jrp.Hello                                                     | PASS |
1 test, 1 passed, 0 failed
==============================================================================
Tmpdlb85Jrp                                                           | PASS |
1 test, 1 passed, 0 failed
==============================================================================
Output:  /tmp/tmp2721mpez/output.xml
Log:     /tmp/tmp2721mpez/log.html
Report:  /tmp/tmp2721mpez/report.html
... | INFO | ... | Completing My Topic in BPMN:3622b58f-e97e-11ef-a0ec-52f4bfd829ae.
```

The example rolls a die and fails with `Bad luck` on a roll below 3, to demonstrate BPMN error handling: about one run in three prints `FAIL` and the process continues through its error boundary event instead.

## More information

* Documentation: https://datakurre.github.io/purjo/
* Playground: https://datakurre.github.io/operaton-robot-playground
