# DataHub components in this lab

Fictional `datahub` namespace. Component names match the public Helm chart.

| Component | Role in this lab |
| --- | --- |
| `datahub-gms` | Generalized Metadata Service. GraphQL `/api/graphql`, REST, MCP apply. |
| `datahub-frontend` | React UI (port 9002 in the public k8s docs). |
| `datahub-mae-consumer` | Metadata Audit Event consumer (optional standalone). |
| `datahub-mce-consumer` | Metadata Change Event consumer (optional standalone). |
| `datahub-actions` | Actions + **executor** for UI / scheduled ingestion. |

Typical dependencies (not all simulated here): Kafka, a local DB, Elasticsearch,
optional Neo4j. This console only ticks CPU/memory for the five DataHub
components above.
