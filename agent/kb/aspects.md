# Aspects, datasets, lineage (lab notes)

DataHub stores metadata as **aspects** on entities identified by URNs.

Example dataset urn produced by postgres ingestion:

`urn:li:dataset:(urn:li:dataPlatform:postgres,analytics.public.orders,PROD)`

Aspects commonly emitted by SQL sources:

- `datasetProperties`
- `schemaMetadata` (columns / SchemaField)
- `status`
- `container` (schema and database)
- `upstreamLineage` (views / query lineage)
- `datasetProfile` (optional profiling)
- `ownership`, `globalTags`, `glossaryTerms` when configured

REST alternative to GraphQL entity fetch: `POST /aspects?action=ingestProposal`
(Metadata Change Proposal). This lab’s mock accepts that path for API tests
and still does not talk to a real GMS.
