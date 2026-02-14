# `pur`(jo)

`pur`(jo) (*/ˈpurjo/*)  is an experimental command line tool for orchestrating [Robot Framework](https://robotframework.org/) test or task suites with the [Operaton](https://operaton.org/) BPM engine. It long-polls external service tasks from the Operaton engine, executes mapped Robot Framework test and task suites with the [uv](https://docs.astral.sh/uv/) Python environment manager, and finally reports the results or errors back to the engine.

## CLI

```
 Usage: pur [OPTIONS] COMMAND [ARGS]...

 pur(jo) is a tool for managing and serving robot packages.

╭─ Commands ───────────────────────────────────────────────────────────────╮
│ serve   Serve robot.zip packages (or directories) as BPMN service tasks. │
│ init    Initialize a new robot package into the current directory.       │
│ wrap    Wrap the current directory into a robot.zip package.             │
│ run     Deploy process resources to BPM engine and start a new instance. │
│ bpm     BPM engine operations as distinct sub commands.                  │
╰──────────────────────────────────────────────────────────────────────────╯
```

```
Usage: pur serve [OPTIONS] ROBOTS...

 Serve robot.zip packages (or directories) as BPMN service tasks.

╭─ Arguments ────────────────────────────────────────────────────────────────────╮
│ *    robots      ROBOTS...  [default: None] [required]                         │
╰────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────╮
│ --base-url             TEXT        default: http://localhost:8080/engine-rest] │
│ --authorization        TEXT                   [default: None]                  │
│ --timeout              INTEGER                [default: 20]                    │
│ --poll-ttl             INTEGER                [default: 10]                    │
│ --lock-ttl             INTEGER                [default: 30]                    │
│ --max-jobs             INTEGER                [default: 1]                     │
│ --worker-id            TEXT                   [default: operaton-robot-runner] │
│ --log-level            TEXT                   [default: DEBUG]                 │
│ --on-fail              [FAIL|COMPLETE|ERROR]  [default: FAIL]                  │
│ --help                                        Show this message and exit.      │
╰────────────────────────────────────────────────────────────────────────────────╯
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
Adding .python-version
Adding pyproject.toml
Adding README.md
Adding Hello.py
Adding hello.robot
Adding uv.lock
Adding hello.bpmn
```

Or init with Robot Framework task template (uses `*** Tasks ***` instead of `*** Test Cases ***`):

```console
$ uv run --with=purjo -- pur init --task
```

Deploy and start an example process:

```console
$ uv run --with=purjo -- run hello.bpmn
Started: http://localhost:8080/operaton/app/cockpit/default/#/process-instance/36228e79-e97e-11ef-a0ec-52f4bfd829ae/runtime
```

Serve the project as external task worker:

```console
$ uv run --with=purjo -- serve .
... | DEBUG | ... | Waiting for 1 pending asyncio task: ['My Topic in BPMN:3622b58f-e97e-11ef-a0ec-52f4bfd829ae'].
==============================================================================
Tmpdlb85Jrp
==============================================================================
Tmpdlb85Jrp.Hello
==============================================================================
My Task in Robot                                                      | PASS |
------------------------------------------------------------------------------
Tmpdlb85Jrp.Hello                                                     | PASS |
1 task, 1 passed, 0 failed
==============================================================================
Tmpdlb85Jrp                                                           | PASS |
1 task, 1 passed, 0 failed
==============================================================================
Output:  /tmp/nix-shell-49641-0/tmp2721mpez/output.xml
Log:     /tmp/nix-shell-49641-0/tmp2721mpez/log.html
Report:  /tmp/nix-shell-49641-0/tmp2721mpez/report.html
... | INFO | ... | Completing My Topic in BPMN:3622b58f-e97e-11ef-a0ec-52f4bfd829ae.
```

## More information

https://datakurre.github.io/operaton-robot-playground