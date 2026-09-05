# Glossary

This glossary defines canonical terminology used throughout the `purjo` project. Agents and contributors should use these terms consistently to reduce semantic drift.

---

## Core Domain Terms

### Robot Package
A zip file containing a Robot Framework suite, its dependencies, and configuration. Created using `pur wrap` and deployed to execute as external service tasks.

### External Task
A BPMN service task that is executed by an external worker (like `purjo`) rather than by the BPM engine itself. The engine publishes tasks to a queue, and workers poll for and execute them.

### Topic
The identifier used to route external tasks to specific workers. Each robot package is associated with a topic that matches the service task's topic in the BPMN process.

### Process Instance
A running instance of a BPMN process definition. Created when a process is started and represents the execution state of a workflow.

### Process Definition Key
The unique identifier for a BPMN process definition. Used to start new process instances or query existing definitions.

### Lock TTL (Time To Live)
The duration (in milliseconds) that an external task is reserved for a worker. If the worker doesn't complete or extend the lock within this time, the task becomes available to other workers.

### BPMN Error
A catchable error that can be handled within the BPMN process flow. Unlike technical failures, BPMN errors can trigger error boundary events for graceful error handling.

---

## Technical Terms

### Operaton
The BPM engine used by `purjo`. An open-source fork of Camunda Platform 7.

### uv
The Python package manager and environment tool used by `purjo` to manage dependencies and execute Robot Framework in isolated environments.

### Worker ID
A unique identifier for a task worker instance. Used for logging, debugging, and tracking which worker processed a specific task.

---

## CLI Commands

### serve
Start the external task worker to poll and execute tasks from the BPM engine.

### init
Initialize a new robot package or Python project with `purjo` configuration.

### wrap
Package the current directory into a `robot.zip` file for deployment.

### run
Deploy resources to the BPM engine and start a process instance in one command.

### operaton (bpm)
Direct access to BPM engine operations: create resources, deploy, and start processes.

---

## Failure Handling Terms

### FAIL
A failure mode where task execution failure is reported as a task failure to the engine, potentially triggering retries.

### ERROR
A failure mode where task execution failure is reported as a BPMN error, allowing error boundary events to handle it.

### COMPLETE
A failure mode where task execution failure is still reported as task completion, with failure details included in output variables.

---

## Deprecated Terms

| Deprecated Term | Use Instead |
|-----------------|-------------|
| Camunda | Operaton |
| robot.zip | Robot Package |
| bpm (command) | operaton |
