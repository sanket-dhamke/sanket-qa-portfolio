# DataHub recipes — postgres and oracle

Public docs:

- https://datahubproject.io/docs/generated/ingestion/sources/postgres/
- Oracle source uses `host_port` plus **either** `database` **or** `service_name`.

## Postgres (`type: postgres`)

Required-ish coordinates this lab asks for:

- `host_port` (host:port)
- `username`
- `database`
- `schema_pattern.allow` / `table_pattern.allow` (regex lists)
- `include_tables` / `include_views`

Concept mapping: database → Container (DATABASE), schema → Container (SCHEMA),
table → Dataset (TABLE), view → Dataset (VIEW), stored procedure → DataJob.

## Oracle (`type: oracle`)

- `host_port`
- `username`
- `service_name` **or** `database` (not both)
- `schema_pattern.allow`

## Sink

UI ingestion and this lab use `sink.type: datahub-rest` with
`server: http://datahub-gms:8080`. The executor is `datahub-actions`.

CLI equivalent (not used here): `datahub ingest -c recipe.yml`.
