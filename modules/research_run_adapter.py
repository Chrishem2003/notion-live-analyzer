"""Safe, idempotent write-back for research Analysis Run records.

This adapter targets a Notion data source (collection:// ID), not a database
container ID. Call only from a trusted server-side process.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import requests

from modules.research_run_idempotency import IdempotencyConflictError

NOTION_API_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2025-09-03"


class ResearchRunWriteError(RuntimeError):
    """A run could not be safely persisted to Notion."""


class AmbiguousWriteError(ResearchRunWriteError):
    """A write may have reached Notion; reconcile by stable ID before retry."""


class RelationValidationError(ValueError):
    """A submitted page is not a valid, linked input for this run."""


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

    def recover_run(
        self, run_id: str, submitted_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Reconcile an ambiguous run without creating anything new.

        When submitted properties are supplied, verify the stored manifest too.
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
        if submitted_properties is not None:
            page = self._read_and_verify_existing(page_id, stable_id, submitted_properties)
        else:
            page = self._read_page(page_id)
        return {"created": False, "page": page}

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Fetch a page by ID for idempotent completed-run read-back."""
        if not isinstance(page_id, str) or not page_id.strip():
            raise ValueError("page_id must be a non-empty string.")
        return self._read_page(page_id.strip())

    def get_and_verify_existing_run(
        self, page_id: str, run_id: str, submitted_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read a completed run and verify its stored manifest matches the request."""
        stable_id = self._validate_run_id(run_id)
        if not isinstance(submitted_properties, dict):
            raise ValueError("submitted_properties must be a dictionary.")
        return self._read_and_verify_existing(page_id, stable_id, submitted_properties)

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
            raise RelationValidationError(
                f"{label} page does not belong to the configured private data source."
            )
        return page

    @staticmethod
    def validate_relation_membership(
        page: Dict[str, Any],
        property_name: str,
        expected_page_ids: list[str],
        label: str,
        *,
        require_all: bool = True,
    ) -> None:
        """Ensure a linked input's existing relation agrees with the submitted run."""
        if not expected_page_ids:
            raise RelationValidationError(f"{label}: at least one expected related page is required.")
        properties = page.get("properties") or {}
        prop = properties.get(property_name)
        if not isinstance(prop, dict) or prop.get("type") != "relation":
            raise RelationValidationError(
                f"{label}: required relation property {property_name!r} is missing or has the wrong type."
            )
        actual = {
            str(item.get("id", "")).replace("-", "").lower()
            for item in (prop.get("relation") or [])
            if isinstance(item, dict) and item.get("id")
        }
        expected = {
            str(page_id).strip().replace("-", "").lower()
            for page_id in expected_page_ids
            if isinstance(page_id, str) and page_id.strip()
        }
        if require_all:
            valid = expected.issubset(actual)
        else:
            valid = bool(expected.intersection(actual))
        if not valid:
            raise RelationValidationError(
                f"{label}: relation {property_name!r} does not match the project, protocol, or samples selected for this run."
            )

    @staticmethod
    def validate_record_classification(
        page: Dict[str, Any],
        label: str,
        allowed: tuple[str, ...] = ("Demo", "Synthetic/Test"),
    ) -> None:
        """Prevent a synthetic endpoint from being used with real/unclassified records."""
        properties = page.get("properties") or {}
        prop = properties.get("Record Classification")
        selected = prop.get("select") if isinstance(prop, dict) and prop.get("type") == "select" else None
        name = selected.get("name") if isinstance(selected, dict) else None
        if name not in allowed:
            raise RelationValidationError(
                f"{label} must be classified Demo or Synthetic/Test for this staging endpoint."
            )

    @staticmethod
    def _manifest_hash(properties: Dict[str, Any]) -> str:
        """Read a manifest hash from a Notion properties mapping."""
        prop = properties.get("Run Manifest Hash") or {}
        rich_text = prop.get("rich_text") if isinstance(prop, dict) else None
        if not isinstance(rich_text, list):
            return ""
        return "".join(
            item.get("plain_text") or (item.get("text") or {}).get("content", "")
            for item in rich_text
            if isinstance(item, dict)
        )

    def _read_and_verify_existing(
        self, page_id: str, run_id: str, submitted_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read back an existing run and reject stable-ID reuse for changed inputs."""
        page = self._read_page(page_id)
        expected_hash = self._manifest_hash(submitted_properties)
        if expected_hash:
            actual_hash = self._manifest_hash(page.get("properties") or {})
            if not actual_hash or actual_hash != expected_hash:
                raise IdempotencyConflictError(
                    f"External Run ID {run_id!r} already exists with a missing or different "
                    "Run Manifest Hash. The local ledger may have been reset; manual "
                    "reconciliation is required and no new record was created."
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
            return {
                "created": False,
                "page": self._read_and_verify_existing(page_id, stable_id, props),
            }

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
                return {
                    "created": False,
                    "page": self._read_and_verify_existing(page_id, stable_id, props),
                }
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
