"""Safe, idempotent write-back for research Analysis Run records.

This adapter targets a Notion data source (collection:// ID), not a database
container ID. Call only from a trusted server-side process.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import requests

NOTION_API_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2025-09-03"


class ResearchRunWriteError(RuntimeError):
    """A run could not be safely persisted to Notion."""


class AmbiguousWriteError(ResearchRunWriteError):
    """A write may have reached Notion; reconcile by stable ID before retry."""


class ResearchRunAdapter:
    """Create or retrieve an Analysis Run using a stable external run ID."""

    def __init__(
        self, token: str, data_source_id: str, *,
        external_id_property: str = "External Run ID",
        notion_version: str = DEFAULT_NOTION_VERSION,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("A Notion integration token is required.")
        if not data_source_id or not data_source_id.strip():
            raise ValueError("A target Analysis Runs data source ID is required.")
        if not external_id_property or not external_id_property.strip():
            raise ValueError("An external run ID property name is required.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        self.data_source_id = data_source_id.removeprefix("collection://")
        self.external_id_property = external_id_property
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty stable string.")
        return run_id.strip()

    def _find_by_external_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        response = self.session.post(
            f"{NOTION_API_URL}/data_sources/{self.data_source_id}/query",
            json={"page_size": 2, "filter": {
                "property": self.external_id_property,
                "rich_text": {"equals": run_id},
            }},
            headers=self.headers, timeout=self.timeout,
        )
        if response.status_code != 200:
            raise ResearchRunWriteError(
                f"Could not verify run identity (HTTP {response.status_code})."
            )
        results = response.json().get("results", [])
        if len(results) > 1:
            raise ResearchRunWriteError(
                f"Duplicate External Run ID exists for {run_id!r}; "
                "manual reconciliation is required."
            )
        return results[0] if results else None

    def _read_page(self, page_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=self.headers, timeout=self.timeout,
        )
        if response.status_code != 200:
            raise ResearchRunWriteError(
                f"Run write-back read verification failed (HTTP {response.status_code}); "
                f"page ID: {page_id}."
            )
        return response.json()

    def recover_run(self, run_id: str) -> Dict[str, Any]:
        """Reconcile an ambiguous run without creating anything new.

        This path is intentionally read-only: absence from a query is not
        proof that an earlier uncertain create failed to commit.
        """
        stable_id = self._validate_run_id(run_id)
        existing = self._find_by_external_id(stable_id)
        if not existing:
            raise AmbiguousWriteError(
                "This run_id has an ambiguous prior write and no matching record is "
                "currently visible. No new record was created; reconcile in Notion "
                "before clearing the idempotency reservation."
            )
        page_id = existing.get("id")
        if not page_id:
            raise AmbiguousWriteError(
                "A matching record was found without a page ID; manual reconciliation is required."
            )
        return {"created": False, "page": self._read_page(page_id)}

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Fetch a page by ID for idempotent completed-run read-back."""
        if not isinstance(page_id, str) or not page_id.strip():
            raise ValueError("page_id must be a non-empty string.")
        return self._read_page(page_id.strip())

    def validate_page_parent(
        self, page_id: str, expected_data_source_id: str, label: str
    ) -> Dict[str, Any]:
        """Confirm a relation page belongs to the expected Notion data source."""
        if not isinstance(page_id, str) or not page_id.strip():
            raise ValueError(f"{label} page ID must be a non-empty string.")
        expected = expected_data_source_id.removeprefix("collection://").strip()
        if not expected:
            raise ValueError(f"Expected data source for {label} is not configured.")
        page = self._read_page(page_id.strip())
        parent = page.get("parent") or {}
        actual = parent.get("data_source_id")
        if parent.get("type") != "data_source_id" or actual != expected:
            raise ResearchRunWriteError(
                f"{label} page does not belong to the configured private data source."
            )
        return page

    def create_or_get_run(
        self, run_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist a run once; retries return the existing record."""
        stable_id = self._validate_run_id(run_id)
        if not isinstance(properties, dict):
            raise ValueError("properties must be a dictionary of Notion properties.")
        props = dict(properties)
        expected = {"rich_text": [{"text": {"content": stable_id}}]}
        supplied = props.get(self.external_id_property)
        if supplied is not None and supplied != expected:
            raise ValueError(
                f"{self.external_id_property!r} must match the stable run_id."
            )
        props[self.external_id_property] = expected

        existing = self._find_by_external_id(stable_id)
        if existing:
            page_id = existing.get("id")
            if not page_id:
                raise ResearchRunWriteError("Existing run record has no page ID.")
            return {"created": False, "page": self._read_page(page_id)}

        try:
            response = self.session.post(
                f"{NOTION_API_URL}/pages",
                json={"parent": {
                    "type": "data_source_id",
                    "data_source_id": self.data_source_id,
                }, "properties": props},
                headers=self.headers, timeout=self.timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            try:
                recovered = self._find_by_external_id(stable_id)
            except Exception as lookup_error:
                raise AmbiguousWriteError(
                    "Write outcome is unknown and run identity could not be verified. "
                    "Do not blindly retry; reconcile by External Run ID."
                ) from lookup_error
            if recovered:
                page_id = recovered.get("id")
                if not page_id:
                    raise AmbiguousWriteError(
                        "A matching record was found without a page ID."
                    ) from exc
                return {"created": False, "page": self._read_page(page_id)}
            raise AmbiguousWriteError(
                "Write outcome is unknown and no matching record is visible. "
                "Retry only with this same run_id after checking Notion; do not "
                "mint a new run ID."
            ) from exc

        if response.status_code not in (200, 201):
            raise ResearchRunWriteError(
                f"Notion rejected the run write (HTTP {response.status_code})."
            )
        page_id = response.json().get("id")
        if not page_id:
            raise ResearchRunWriteError(
                "Notion accepted the write but returned no page ID."
            )
        return {"created": True, "page": self._read_page(page_id)}


def build_analysis_run_properties(
    *,
    run_name: str,
    project_page_id: str,
    protocol_page_id: str,
    input_sample_page_ids: Optional[list[str]] = None,
    input_data_record_page_ids: Optional[list[str]] = None,
    source_evidence_page_ids: Optional[list[str]] = None,
    input_dataset_version: str = "",
    analysis_method: str = "",
    code_revision: str = "",
    environment: str = "staging",
    manifest_hash: str = "",
    parameters_json: str = "",
) -> Dict[str, Any]:
    """Build a schema-aligned Analysis Run payload with conservative gates.

    Starts at Draft / Intake / Pending QC / Not Checked / Synthetic-Test.
    It never marks a run complete or approved. The caller must validate all
    related page IDs against the intended private data sources.
    """
    def required_text(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string.")
        return value.strip()

    def relation_ids(values: Optional[list[str]], field: str) -> list[dict[str, str]]:
        ids = values or []
        if not isinstance(ids, list):
            raise ValueError(f"{field} must be a list of page IDs.")
        cleaned = []
        for value in ids:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} contains an empty page ID.")
            cleaned.append({"id": value.strip()})
        return cleaned

    props: Dict[str, Any] = {
        "Run Name": {"title": [{"text": {"content": required_text(run_name, "run_name")}}]},
        "Project": {"relation": [{"id": required_text(project_page_id, "project_page_id")}]},
        "Protocol": {"relation": [{"id": required_text(protocol_page_id, "protocol_page_id")}]},
        "Input Samples": {"relation": relation_ids(input_sample_page_ids, "input_sample_page_ids")},
        "Input Data Records": {"relation": relation_ids(input_data_record_page_ids, "input_data_record_page_ids")},
        "Source Evidence": {"relation": relation_ids(source_evidence_page_ids, "source_evidence_page_ids")},
        "Run Status": {"select": {"name": "Draft"}},
        "Workflow Gate": {"select": {"name": "Intake"}},
        "QC Outcome": {"select": {"name": "Pending"}},
        "Reproducibility Check": {"select": {"name": "Not Checked"}},
        "Record Classification": {"select": {"name": "Synthetic/Test"}},
    }
    optional_text = {
        "Input Dataset Version": input_dataset_version,
        "Analysis Method": analysis_method,
        "Code Revision": code_revision,
        "Environment": environment,
        "Run Manifest Hash": manifest_hash,
        "Parameters": parameters_json,
    }
    for name, value in optional_text.items():
        if value:
            props[name] = {"rich_text": [{"text": {"content": str(value)}}]}
    return props
