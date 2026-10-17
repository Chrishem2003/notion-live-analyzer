"""Unit tests for explicit Notion workflow handoff with mocked HTTP."""
import unittest
from concurrent.futures import ThreadPoolExecutor

import requests

from modules.notion_workflow_handoff import NotionHandoffError, _rich_text, sync_run_to_notion


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def schema_payload():
    properties = {
        "Run Name": {"type": "title"},
        "Run Status": {"type": "select", "select": {"options": [{"name": "Complete"}]}},
        "Workflow Gate": {"type": "select", "select": {"options": [{"name": "Execution Recorded"}]}},
        "QC Outcome": {"type": "select", "select": {"options": [{"name": "Pending"}]}},
        "Reproducibility Check": {"type": "select", "select": {"options": [{"name": "Not Checked"}]}},
        "Record Classification": {"type": "select", "select": {"options": [{"name": "Synthetic/Test"}]}},
        "Analysis Method": {"type": "rich_text"},
        "Code Revision": {"type": "rich_text"},
        "Input Dataset Version": {"type": "rich_text"},
        "Run Manifest Hash": {"type": "rich_text"},
        "Execution Evidence / Handoff": {"type": "rich_text"},
        "Environment": {"type": "rich_text"},
        "Parameters": {"type": "rich_text"},
        "Started At": {"type": "date"},
        "Completed At": {"type": "date"},
        "Blocker / Recovery Action": {"type": "rich_text"},
    }
    return {"properties": properties}


class FakeSession:
    def __init__(self, query_payload=None, create_payload=None, database_schema=None):
        self.query_payload = query_payload if query_payload is not None else {"results": []}
        self.create_payload = create_payload or {"id": "page-1", "url": "https://notion.example/page-1"}
        self.database_schema = database_schema or schema_payload()
        self.calls = []
        self.posts = []
        self.created_properties = None

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if "/pages/" in url:
            properties = self.created_properties or {}
            return FakeResponse({
                "id": self.create_payload.get("id"),
                "url": self.create_payload.get("url"),
                "properties": properties,
            })
        return FakeResponse(self.database_schema)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        self.posts.append((url, kwargs))
        if url.endswith("/query"):
            return FakeResponse(self.query_payload)
        if url.endswith("/pages"):
            self.created_properties = kwargs.get("json", {}).get("properties", {})
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
            sync_run_to_notion(
                sample_run(status="failed"),
                token="secret",
                database_id="12345678123456781234567812345678",
                session=session,
            )
        self.assertEqual(session.calls, [])

    def test_missing_configuration_fails_closed(self):
        with self.assertRaisesRegex(NotionHandoffError, "NOTION_API_KEY"):
            sync_run_to_notion(sample_run(), token="", database_id="db", session=FakeSession())

    def test_creates_review_pending_record_and_uses_idempotency_hash(self):
        session = FakeSession()
        result = sync_run_to_notion(sample_run(), token="secret", database_id="12345678-1234-5678-1234-567812345678", session=session)
        self.assertTrue(result["created"])
        self.assertTrue(result["read_back_verified"])
        self.assertEqual(result["url"], "https://notion.example/page-1")
        self.assertEqual(len(session.posts), 2)
        query_call, create_call = session.posts
        self.assertTrue(query_call[0].endswith("/databases/12345678-1234-5678-1234-567812345678/query"))
        query_filter = query_call[1]["json"]["filter"]
        self.assertEqual(query_filter["property"], "Run Manifest Hash")
        properties = create_call[1]["json"]["properties"]
        self.assertEqual(properties["QC Outcome"]["select"]["name"], "Pending")
        self.assertEqual(properties["Reproducibility Check"]["select"]["name"], "Not Checked")
        self.assertEqual(properties["Record Classification"]["select"]["name"], "Synthetic/Test")
        self.assertEqual(properties["Run Manifest Hash"]["rich_text"][0]["text"]["content"], result["manifest_hash"])
        self.assertEqual(properties["Code Revision"]["rich_text"][0]["text"]["content"], "Not supplied by runtime")
        self.assertEqual(properties["Input Dataset Version"]["rich_text"][0]["text"]["content"], "Not supplied by runtime")
        evidence = properties["Execution Evidence / Handoff"]["rich_text"][0]["text"]["content"]
        self.assertIn('"mean": 2.0', evidence)
        self.assertIn("QC and reproducibility are still pending", evidence)

    def test_manifest_mismatch_on_independent_readback_is_not_claimed_as_delivery(self):
        class MismatchedReadBackSession(FakeSession):
            def get(self, url, **kwargs):
                self.calls.append(("GET", url, kwargs))
                if "/pages/" in url:
                    return FakeResponse({
                        "id": "page-1",
                        "url": "https://notion.example/page-1",
                        "properties": {
                            "Run Manifest Hash": {
                                "type": "rich_text",
                                "rich_text": [{"plain_text": "wrong-manifest"}],
                            }
                        },
                    })
                return FakeResponse(self.database_schema)

        with self.assertRaisesRegex(NotionHandoffError, "manifest hash did not match"):
            sync_run_to_notion(
                sample_run(),
                token="secret",
                database_id="12345678123456781234567812345678",
                session=MismatchedReadBackSession(),
            )

    def test_existing_matching_record_is_returned_without_duplicate_create(self):
        session = FakeSession(query_payload={"results": [{"id": "existing", "url": "https://notion.example/existing"}]})
        result = sync_run_to_notion(sample_run(), token="secret", database_id="12345678-1234-5678-1234-567812345678", session=session)
        self.assertFalse(result["created"])
        self.assertEqual(result["page_id"], "existing")
        self.assertEqual(len(session.posts), 1)

    def test_multiple_matching_manifest_records_pause_handoff_for_reconciliation(self):
        session = FakeSession(query_payload={
            "results": [
                {"id": "existing-1", "url": "https://notion.example/existing-1"},
                {"id": "existing-2", "url": "https://notion.example/existing-2"},
            ]
        })
        with self.assertRaisesRegex(NotionHandoffError, "multiple Notion records match"):
            sync_run_to_notion(
                sample_run(), token="secret",
                database_id="12345678-1234-5678-1234-567812345678",
                session=session,
            )
        self.assertFalse(any(url.endswith("/pages") for url, _ in session.posts))
        query = next(kwargs for url, kwargs in session.posts if url.endswith("/query"))
        self.assertEqual(query["json"]["page_size"], 100)

    def test_http_error_is_reported_without_claiming_delivery(self):
        class FailedSession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return FakeResponse({"message": "unauthorized"}, status_code=401)
        with self.assertRaisesRegex(NotionHandoffError, "401"):
            sync_run_to_notion(sample_run(), token="secret", database_id="12345678-1234-5678-1234-567812345678", session=FailedSession())

    def test_timezone_naive_timestamp_is_rejected_before_network_calls(self):
        session = FakeSession()
        with self.assertRaisesRegex(NotionHandoffError, "must include a timezone"):
            sync_run_to_notion(
                sample_run(created_at="2026-10-16T10:00:00"),
                token="secret",
                database_id="12345678123456781234567812345678",
                session=session,
            )
        self.assertEqual(session.calls, [])

    def test_long_rich_text_is_explicitly_marked_as_truncated(self):
        value = "x" * 2500
        content_value = _rich_text(value)["rich_text"][0]["text"]["content"]
        self.assertLessEqual(len(content_value), 1900)
        self.assertIn("[truncated; see manifest hash and local run store]", content_value)

    def test_input_dataset_version_is_preserved_when_provided(self):
        session = FakeSession()
        run = sample_run(input={"values": [1, 2, 3], "dataset_version": "dataset-v7"})
        sync_run_to_notion(run, token="secret", database_id="12345678123456781234567812345678", session=session)
        create_call = [call for call in session.posts if call[0].endswith("/pages")][0]
        properties = create_call[1]["json"]["properties"]
        self.assertEqual(
            properties["Input Dataset Version"]["rich_text"][0]["text"]["content"],
            "dataset-v7",
        )

    def test_invalid_database_id_is_rejected_before_network_calls(self):
        session = FakeSession()
        with self.assertRaisesRegex(NotionHandoffError, "database ID must be"):
            sync_run_to_notion(sample_run(), token="secret", database_id="db-1/../../pages", session=session)
        self.assertEqual(session.calls, [])

    def test_transient_schema_failure_is_retried(self):
        class FlakySchemaSession(FakeSession):
            def __init__(self):
                super().__init__()
                self.get_count = 0

            def get(self, url, **kwargs):
                self.get_count += 1
                self.calls.append(("GET", url, kwargs))
                if self.get_count == 1:
                    return FakeResponse({"message": "temporarily unavailable"}, status_code=503)
                return FakeResponse(self.database_schema)

        session = FlakySchemaSession()
        result = sync_run_to_notion(sample_run(), token="secret", database_id="12345678123456781234567812345678", session=session)
        self.assertTrue(result["created"])
        self.assertEqual(session.get_count, 2)

    def test_ambiguous_create_transport_failure_is_not_blindly_replayed(self):
        class AmbiguousCreateSession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append(("POST", url, kwargs))
                if url.endswith("/query"):
                    return FakeResponse({"results": []})
                raise requests.ConnectionError("connection dropped after request")

        session = AmbiguousCreateSession()
        with self.assertRaisesRegex(NotionHandoffError, "outcome is unknown"):
            sync_run_to_notion(sample_run(), token="secret", database_id="12345678123456781234567812345678", session=session)
        create_calls = [call for call in session.calls if call[0] == "POST" and call[1].endswith("/pages")]
        self.assertEqual(len(create_calls), 1)

    def test_incompatible_database_schema_fails_before_any_write(self):
        schema = schema_payload()
        del schema["properties"]["Run Manifest Hash"]
        session = FakeSession(database_schema=schema)
        with self.assertRaisesRegex(NotionHandoffError, "missing required properties"):
            sync_run_to_notion(sample_run(), token="secret", database_id="12345678-1234-5678-1234-567812345678", session=session)
        self.assertEqual(session.posts, [])

    def test_missing_required_select_option_fails_closed(self):
        schema = schema_payload()
        schema["properties"]["QC Outcome"]["select"]["options"] = [{"name": "Pass"}]
        session = FakeSession(database_schema=schema)
        with self.assertRaisesRegex(NotionHandoffError, "missing required option"):
            sync_run_to_notion(sample_run(), token="secret", database_id="12345678-1234-5678-1234-567812345678", session=session)
        self.assertEqual(session.posts, [])


    def test_shared_sqlite_ledger_serializes_concurrent_same_manifest_handoffs(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        class StatefulSession(FakeSession):
            def post(self, url, **kwargs):
                if url.endswith("/query") and any(
                    posted_url.endswith("/pages") for posted_url, _ in self.posts
                ):
                    self.calls.append(("POST", url, kwargs))
                    return FakeResponse({"results": [self.create_payload]})
                return super().post(url, **kwargs)

        session = StatefulSession()
        with TemporaryDirectory() as temporary_directory:
            ledger = str(Path(temporary_directory) / "handoff-lock.sqlite3")
            def deliver():
                return sync_run_to_notion(
                    sample_run(),
                    token="secret",
                    database_id="12345678123456781234567812345678",
                    session=session,
                    ledger_database=ledger,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(deliver)
                second = executor.submit(deliver)
                results = [first.result(timeout=10), second.result(timeout=10)]

        self.assertEqual(sum(1 for result in results if result["created"]), 1)
        self.assertEqual(sum(1 for result in results if not result["created"]), 1)
        create_calls = [
            posted for posted in session.posts
            if posted[0].endswith("/pages")
        ]
        self.assertEqual(len(create_calls), 1)


    def test_malformed_query_results_fail_closed_before_create(self):
        class MalformedQuerySession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append(("POST", url, kwargs))
                self.posts.append((url, kwargs))
                if url.endswith("/query"):
                    return FakeResponse({"results": {"unexpected": "shape"}})
                return FakeResponse(self.create_payload)

        session = MalformedQuerySession()
        with self.assertRaisesRegex(NotionHandoffError, "invalid results structure"):
            sync_run_to_notion(
                sample_run(), token="secret",
                database_id="12345678-1234-5678-1234-567812345678",
                session=session,
            )
        self.assertFalse(any(url.endswith("/pages") for url, _ in session.posts))

    def test_create_response_without_page_id_is_not_reported_as_delivered(self):
        class IncompleteCreateSession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append(("POST", url, kwargs))
                self.posts.append((url, kwargs))
                if url.endswith("/query"):
                    return FakeResponse({"results": []})
                return FakeResponse({"url": "https://notion.example/missing-id"})

        session = IncompleteCreateSession()
        with self.assertRaisesRegex(NotionHandoffError, "did not confirm a page ID"):
            sync_run_to_notion(
                sample_run(), token="secret",
                database_id="12345678-1234-5678-1234-567812345678",
                session=session,
            )
        self.assertEqual(
            sum(1 for url, _ in session.posts if url.endswith("/pages")), 1
        )


    def test_ambiguous_create_is_reconciled_on_retry_with_shared_ledger(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        class CommitThenDisconnectSession(FakeSession):
            def __init__(self):
                super().__init__()
                self.remote_page = None
                self.create_attempts = 0

            def post(self, url, **kwargs):
                self.calls.append(("POST", url, kwargs))
                self.posts.append((url, kwargs))
                if url.endswith("/query"):
                    return FakeResponse(
                        {"results": [self.remote_page] if self.remote_page else []}
                    )
                self.create_attempts += 1
                self.remote_page = dict(self.create_payload)
                if self.create_attempts == 1:
                    raise requests.ConnectionError("simulated response lost after remote commit")
                return FakeResponse(self.create_payload)

        session = CommitThenDisconnectSession()
        with TemporaryDirectory() as directory:
            ledger = str(Path(directory) / "handoff-recovery.sqlite3")
            with self.assertRaisesRegex(NotionHandoffError, "outcome is unknown"):
                sync_run_to_notion(
                    sample_run(), token="secret",
                    database_id="12345678-1234-5678-1234-567812345678",
                    session=session, ledger_database=ledger,
                )
            recovered = sync_run_to_notion(
                sample_run(), token="secret",
                database_id="12345678-1234-5678-1234-567812345678",
                session=session, ledger_database=ledger,
            )

        self.assertFalse(recovered["created"])
        self.assertEqual(recovered["page_id"], "page-1")
        self.assertEqual(session.create_attempts, 1)
        self.assertEqual(
            sum(1 for url, _ in session.posts if url.endswith("/pages")), 1
        )

    def test_existing_match_with_non_https_url_fails_closed(self):
        session = FakeSession(
            query_payload={"results": [{"id": "existing", "url": "http://notion.example/page"}]}
        )
        with self.assertRaisesRegex(NotionHandoffError, "valid HTTPS page URL"):
            sync_run_to_notion(
                sample_run(), token="secret",
                database_id="12345678-1234-5678-1234-567812345678",
                session=session,
            )
        self.assertFalse(any(url.endswith("/pages") for url, _ in session.posts))

if __name__ == "__main__":
    unittest.main()
