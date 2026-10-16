"""Unit tests for explicit Notion workflow handoff with mocked HTTP."""
import unittest

from modules.notion_workflow_handoff import NotionHandoffError, sync_run_to_notion


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, query_payload=None, create_payload=None):
        self.query_payload = query_payload or {"results": []}
        self.create_payload = create_payload or {"id": "page-1", "url": "https://notion.example/page-1"}
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/query"):
            return FakeResponse(self.query_payload)
        return FakeResponse(self.create_payload)


def sample_run(**overrides):
    run = {
        "run_id": "run-123",
        "workflow_id": "project-1",
        "task_type": "numeric_summary",
        "status": "succeeded",
        "input": {"values": [1, 2, 3]},
        "result": {"mean": 2.0, "n": 3},
        "created_at": "2026-10-16T10:00:00+00:00",
        "updated_at": "2026-10-16T10:01:00+00:00",
        "error_message": None,
    }
    run.update(overrides)
    return run


class NotionWorkflowHandoffTests(unittest.TestCase):
    def test_only_successful_runs_can_be_handed_off(self):
        session = FakeSession()
        with self.assertRaisesRegex(NotionHandoffError, "only successful"):
            sync_run_to_notion(sample_run(status="failed"), token="secret", database_id="db", session=session)
        self.assertEqual(session.calls, [])

    def test_missing_configuration_fails_closed(self):
        with self.assertRaisesRegex(NotionHandoffError, "NOTION_API_KEY"):
            sync_run_to_notion(sample_run(), token="", database_id="db", session=FakeSession())

    def test_creates_review_pending_record_and_uses_idempotency_hash(self):
        session = FakeSession()
        result = sync_run_to_notion(sample_run(), token="secret", database_id="db-1", session=session)
        self.assertTrue(result["created"])
        self.assertEqual(result["url"], "https://notion.example/page-1")
        self.assertEqual(len(session.calls), 2)
        query_call, create_call = session.calls
        self.assertTrue(query_call[0].endswith("/databases/db-1/query"))
        query_filter = query_call[1]["json"]["filter"]
        self.assertEqual(query_filter["property"], "Run Manifest Hash")
        properties = create_call[1]["json"]["properties"]
        self.assertEqual(properties["QC Outcome"]["select"]["name"], "Pending")
        self.assertEqual(properties["Reproducibility Check"]["select"]["name"], "Not Checked")
        self.assertEqual(properties["Record Classification"]["select"]["name"], "Synthetic/Test")
        self.assertEqual(properties["Run Manifest Hash"]["rich_text"][0]["text"]["content"], result["manifest_hash"])

    def test_existing_matching_record_is_returned_without_duplicate_create(self):
        session = FakeSession(query_payload={"results": [{"id": "existing", "url": "https://notion.example/existing"}]})
        result = sync_run_to_notion(sample_run(), token="secret", database_id="db-1", session=session)
        self.assertFalse(result["created"])
        self.assertEqual(result["page_id"], "existing")
        self.assertEqual(len(session.calls), 1)

    def test_http_error_is_reported_without_claiming_delivery(self):
        class FailedSession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return FakeResponse({"message": "unauthorized"}, status_code=401)
        with self.assertRaisesRegex(NotionHandoffError, "401"):
            sync_run_to_notion(sample_run(), token="secret", database_id="db-1", session=FailedSession())


if __name__ == "__main__":
    unittest.main()
