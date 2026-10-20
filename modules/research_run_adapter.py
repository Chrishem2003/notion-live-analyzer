"""Safe, idempotent write-back for research Analysis Run records.

This adapter is separate from the UI and generic sync engine. Call it only
from a trusted server-side process; never expose the Notion token to a browser.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

NOTION_API_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2022-06-28"


class ResearchRunWriteError(RuntimeError):
    """A run could not be safely persisted to Notion."""


class AmbiguousWriteError(ResearchRunWriteError):
    """A write may have reached Notion; reconcile by stable ID before retry."""


class ResearchRunAdapter:
    """Create or retrieve a Notion Analysis Run using a stable external run ID.

    The target database must have a rich-text property named by
    external_id_property. Supplied properties use Notion's native payload
    format, including relation values like {"relation": [{"id": "page-id"}]}.
    This adapter does not infer schema names or approve QC.
    """

    def __init__(
        self,
        token: str,
        database_id: str,
        *,
        external_id_property: str = "External Run ID",
        notion_version: str = DEFAULT_NOTION_VERSION,
        timeout: float = 15.0,
        session: Optional[requests.Session] = None,
        sleep=time.sleep,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("A Notion integration token is required.")
        if not database_id or not database_id.strip():
            raise ValueError("A target Analysis Runs database ID is required.")
        if not external_id_property or not external_id_property.strip():
            raise ValueError("An external run ID property name is required.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        self.database_id = database_id
        self.external_id_property = external_id_property
        self.timeout = timeout
        self.session = session or requests.Session()
        self.sleep = sleep
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
        url = f"{NOTION_API_URL}/databases/{self.database_id}/query"
        payload = {
            "page_size": 2,
            "filter": {
                "property": self.external_id_property,
                "rich_text": {"equals": run_id},
            },
        }
        response = self.session.post(
            url, json=payload, headers=self.headers, timeout=self.timeout
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
            headers=self.headers,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise ResearchRunWriteError(
                f"Run write-back read verification failed (HTTP {response.status_code}); "
                f"page ID: {page_id}."
            )
        return response.json()

    def create_or_get_run(
        self, run_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist a run once; retries return the existing record.

        properties must contain Notion-native values for the target schema.
        The stable External Run ID is injected automatically.
        """
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

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": props,
        }
        try:
            response = self.session.post(
                f"{NOTION_API_URL}/pages",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            # The write might have succeeded server-side. Check before retry.
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
        created = response.json()
        page_id = created.get("id")
        if not page_id:
            raise ResearchRunWriteError(
                "Notion accepted the write but returned no page ID."
            )
        verified = self._read_page(page_id)
        return {"created": True, "page": verified}
