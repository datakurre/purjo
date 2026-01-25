# 2. Use External Task Pattern

Date: 2024-12-28

## Status

Accepted

## Context

We needed a way to integrate Robot Framework execution with the Operaton BPM engine. The integration needed to be decoupled, allowing the Robot Framework tasks to run independently of the BPM engine's process.

## Decision

We decided to use the [External Task Pattern](https://docs.camunda.org/manual/latest/user-guide/process-engine/external-tasks/) (supported by Operaton).

## Consequences

### Positive

- **Decoupling**: The BPM engine and the Robot Framework runner are loosely coupled. They communicate via the REST API.
- **Scalability**: External task workers can be scaled independently of the engine.
- **Language Agnostic**: The worker can be implemented in any language (Python in this case), while the engine runs in Java.

### Negative

- **Latency**: There is a polling interval involved, which might introduce slight latency compared to internal Java delegates.
- **Complexity**: Requires managing a separate worker process (`purjo serve`).
