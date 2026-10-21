# DataHub GraphQL — ingestion (lab notes)

These notes cite the public DataHub GraphQL schema. This repo talks to a bundled
mock at `POST /api/graphql`, not a hosted DataHub cloud.

## listIngestionSources

Query `listIngestionSources(input: ListIngestionSourcesInput!)` returns `urn`,
`name`, `type`, `schedule`, and nested `executions`.

## createIngestionSource

Mutation `createIngestionSource(input: UpdateIngestionSourceInput!)`.
Required input fields used by this lab:

- `name` — display / pipeline name
- `type` — must match the recipe, e.g. `postgres` or `oracle`
- `config.recipe` — **JSON-encoded** recipe (the YAML you edit is converted)
- `config.executorId` — `default` in this lab (datahub-actions executor)
- `config.version` — optional ingestion-framework version

Returns the new source urn, typically `urn:li:dataHubIngestionSource:<id>`.

## createIngestionExecutionRequest

Mutation `createIngestionExecutionRequest(input: CreateIngestionExecutionRequestInput!)`.
The required field is `ingestionSourceUrn`. Returns an execution-request urn
used as the run id. datahub-actions picks the request up.

## listExecutionRequests / poll

Query `listExecutionRequests` (or fetch by urn) for `result.status`
(`PENDING`, `RUNNING`, `SUCCESS`, `FAILURE`), `startTimeMs`, `durationMs`.
