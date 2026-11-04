# Task Metadata Example

This example shows how a Robot Framework task reads selected Operaton external
task metadata and copies the process `businessKey` into a BPMN process variable.

## Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Robot package metadata and the `Task Metadata` topic, which selects `activityId`, `topicName`, `createTime`, and `businessKey` |
| `metadata.bpmn` | BPMN process with one external service task on topic `Task Metadata` |
| `metadata.robot` | Robot test case that checks the metadata variables and writes them to `BPMN:PROCESS` scope |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (used by `pur serve` to run the package)
- `purjo` installed, so the `pur` command is available
- A running Operaton engine reachable at `http://localhost:8080/engine-rest`
  (the default base URL). Set `ENGINE_REST_BASE_URL` and
  `ENGINE_REST_AUTHORIZATION` if your engine differs.

When using this repository, prefix the commands below with `devenv shell --`
to run the checked-out `pur` version. If using another installation, ensure it
includes the task-metadata feature.

## Running the example

1. In this directory, start the worker and leave it running:

   ```console
   $ devenv shell -- pur serve .
   ```

2. In a second terminal, deploy `metadata.bpmn` and start a process instance
   with the sample business key `invoice-42`:

   ```console
   $ devenv shell -- pur run metadata.bpmn --variables '{"businessKey": "invoice-42"}'
   ```

   `businessKey` must be a top-level key in the JSON passed to `--variables`.
   `pur run` uses it as the process instance business key (rather than a
   process variable) and prints a link to the started instance in Operaton
   Cockpit. If omitted, `pur run` generates a UUID.

## Expected behavior

- The external task on topic `Task Metadata` is picked up by `pur serve` and
  runs the `Read task metadata` test case.
- The test case checks that:
  - `${TASK_METADATA_ACTIVITY_ID}` is `MetadataTask`
  - `${TASK_METADATA_TOPIC_NAME}` is `Task Metadata`
  - `${TASK_METADATA_CREATE_TIME}` is not `None`
  - `${TASK_METADATA_BUSINESS_KEY}` is `invoice-42`
- The test case writes these values to process variables `metadata_activity_id`,
  `metadata_topic_name`, `metadata_create_time`, and `metadata_business_key`.
- The process then reaches its end event.

To confirm the round-trip, open the instance in Cockpit and check the process
variables, or query the engine:

```console
$ curl -s "http://localhost:8080/engine-rest/process-instance?businessKey=invoice-42"
$ curl -s "http://localhost:8080/engine-rest/process-instance/<instance-id>/variables"
```

`metadata_business_key` should be `invoice-42`.

If a check fails, the `pur serve` output shows the Robot failure.

## Notes

- The Robot assertions expect the business key `invoice-42`. If you start the
  process with a different `businessKey`, update `metadata.robot` to match.
- The `TASK_METADATA_` prefix is reserved for metadata variables. Do not use it
  for BPMN input variables.

## Cleanup

- Stop `pur serve` with `Ctrl+C`.
- Delete the test process instances from Cockpit, or with the engine REST API,
  if you do not need them. This example creates no local files.
