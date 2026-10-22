"""GraphQL operations posted to mock GMS `POST /api/graphql`."""

from __future__ import annotations

from typing import Any

LIST_SOURCES = """
query {
  listIngestionSources(input: { start: 0, count: 20 }) {
    total
    ingestionSources {
      urn
      name
      type
      assets
    }
  }
}
"""

ASSET_COUNTS = """
query {
  assetCounts
}
"""

LIST_INCIDENTS = """
query {
  listIncidents { open total incidents { title severity entity } }
}
"""

CREATE_EXEC = """
mutation($input: CreateIngestionExecutionRequestInput!) {
  createIngestionExecutionRequest(input: $input)
}
"""

POLL_EXEC = """
query($urn: String!) {
  listExecutionRequests(urn: $urn) {
    executionRequests {
      urn
      result { status durationMs }
    }
  }
}
"""


def gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    return payload
