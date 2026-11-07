"""Fictional regressions for session capture, coverage, review and recovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from harness_core.activities import publish, read_asset, retry_publication
from harness_core.engine import Harness
from harness_core.store import Invalid, stamp
from support import Fixture


class LearningWorkflowTests(Fixture):
    def session(self, **overrides):
        payload = {"client_id": "fictional-exchange-1", "records": [
            {"kind": "observation", "payload": {"role": "assistant", "kind": "conversation", "text": "Fictional question: explain the limit?"}},
            {"kind": "observation", "payload": {"role": "user", "kind": "conversation", "text": "  not shure — 日本語\nkeep my wording  "}},
            {"kind": "checkpoint", "payload": {"summary": "Tutor interpretation only", "next_action": "Ask a fresh case"}}]}
        payload.update(overrides)
        return payload

    def test_one_save_preserves_literals_and_separate_summary_across_rebuild(self):
        before = len(self.h.store.events("fictional"))
        payload = self.session()
        event = self.h.record("fictional", "session", payload)
        self.assertEqual(len(self.h.store.events("fictional")), before + 1)
        fresh = Harness(self.h.store.courses, clock=lambda: self.at)
        fresh._snapshot("fictional")
        resumed = fresh.resume("fictional")
        self.assertEqual(resumed["recent_observations"][-1]["payload"]["text"], payload["records"][1]["payload"]["text"])
        self.assertEqual(resumed["recent_observations"][-1]["id"], event["id"])
        self.assertEqual(resumed["checkpoint"]["summary"], "Tutor interpretation only")
        self.assertEqual(resumed["summary"]["progress"]["independent"], 0)

    def test_session_validates_every_part_before_append_and_retries_idempotently(self):
        before = self.h.store.events("fictional")
        bad = self.session()
        bad["records"].append({"kind": "checkpoint", "payload": {"summary": "Missing next step"}})
        with self.assertRaises(Invalid):
            self.h.record("fictional", "session", bad)
        self.assertEqual(before, self.h.store.events("fictional"))
        event = self.h.record("fictional", "session", self.session())
        self.assertEqual(event, self.h.record("fictional", "session", self.session(), expected_revision="stale-on-retry"))
        changed = self.session(); changed["records"][1]["payload"]["text"] = "Changed answer"
        with self.assertRaisesRegex(Invalid, "different content"):
            self.h.record("fictional", "session", changed)

    def test_session_retry_after_projection_write_fails_does_not_duplicate_evidence(self):
        with patch.object(self.h, "_snapshot", side_effect=PermissionError("fictional denied projection")):
            with self.assertRaises(PermissionError):
                self.h.record("fictional", "session", self.session())
        before = self.h.store.events("fictional")
        self.h.record("fictional", "session", self.session())
        self.assertEqual(before, self.h.store.events("fictional"))

    def test_session_help_remains_effective_even_if_learner_declares_unassisted(self):
        task = publish(self.h, "fictional", self.spec())["activity"]
        self.h.record("fictional", "session", self.session(records=[{"kind": "observation", "payload": {
            "role": "assistant", "kind": "help", "activity": task, "text": "Actually displayed fictional hint"}}]))
        submission = self.submit(task)
        self.assess(submission)
        self.assertTrue(submission["payload"]["observed_help_ids"])
        self.assertFalse(self.h.state("fictional")["learner"]["claims"]["independent"])

    def test_coverage_requires_evidence_and_does_not_grant_capability(self):
        event = self.h.record("fictional", "session", self.session())
        coverage = {"concept_ids": ["claims"], "stage": "introduced", "reason": "Fictional instruction", "evidence_ids": [event["id"]]}
        self.h.record("fictional", "coverage", coverage)
        state = self.h.state("fictional")
        self.assertEqual(state["coverage"]["claims"]["stage"], "introduced")
        self.assertEqual(state["coverage"]["reasoning"]["stage"], "not-recorded")
        self.assertFalse(state["coverage"]["claims"]["checked"])
        self.assertEqual(state["progress"]["practiced"], 0)
        with self.assertRaises(Invalid):
            self.h.record("fictional", "coverage", {**coverage, "evidence_ids": ["made-up"]})
        with self.assertRaises(Invalid):
            self.h.record("fictional", "coverage", {**coverage, "stage": "mastered"})
        task = publish(self.h, "fictional", self.spec())["activity"]
        self.assess(self.submit(task, assistance=["worked example"]))
        self.assertTrue(self.h.state("fictional")["coverage"]["claims"]["checked"])
        self.assertEqual(self.h.state("fictional")["progress"]["independent"], 0)

    def test_review_request_is_a_real_queue_entry_and_keeps_earlier_date(self):
        earlier = stamp(self.at + timedelta(days=1))
        schedule = {"concept_ids": ["claims"], "due_at": earlier, "prompt": "Reconstruct without notes", "reason": "Actual fictional request"}
        self.h.record("fictional", "session", self.session(records=[{"kind": "schedule", "payload": schedule}]))
        self.h.record("fictional", "schedule", {**schedule, "due_at": stamp(self.at + timedelta(days=3))})
        self.assertEqual(self.h.resume("fictional")["reviews"]["claims"]["due_at"], earlier)
        self.assertFalse(self.h.resume("fictional")["summary"]["due_reviews"])
        self.at += timedelta(days=1)
        self.assertEqual(len(self.h.resume("fictional")["summary"]["due_reviews"]), 1)

    def test_budget_and_deferred_lab_survive_fresh_resume_without_progress_credit(self):
        budget = {"remaining_minutes": 90, "deadline": stamp(self.at + timedelta(days=2)),
            "priorities": ["Mixed check"], "deferred": ["Cloud lab blocked; inspect a local fixture instead"], "reason": "Fictional availability report"}
        self.h.record("fictional", "budget", budget)
        self.assertEqual(Harness(self.h.store.courses).resume("fictional")["summary"]["budget"], budget)
        with self.assertRaises(Invalid):
            self.h.record("fictional", "budget", {**budget, "remaining_minutes": True})

    def test_failed_chat_publication_queues_exact_spec_then_recovers_once(self):
        spec = self.spec(private_evaluation="Private fictional solution")
        with patch("harness_core.activities.staging_directory", side_effect=PermissionError("fictional publication denied")):
            with self.assertRaisesRegex(OSError, "Recovery saved"):
                publish(self.h, "fictional", spec, activity_id="recovered")
        repair = self.h.resume("fictional")["summary"]["open_repairs"][0]
        self.assertEqual(self.h.state("fictional")["repairs"][0]["specification"], spec)
        self.assertNotIn("Private fictional solution", json.dumps(self.h.resume("fictional")["summary"]))
        self.assertFalse(self.h.state("fictional")["activities"])
        result = retry_publication(self.h, "fictional", repair["id"])
        self.assertEqual(result["activity"], "recovered@v001")
        question = read_asset(self.h, "fictional", result["activity"], "question.md")
        self.assertNotIn(b"Private fictional solution", question)
        self.assertFalse(self.h.resume("fictional")["summary"]["open_repairs"])
        retry_publication(self.h, "fictional", repair["id"])
        self.assertEqual(len(self.h.state("fictional")["activities"]), 1)
        self.assertFalse(self.h.state("fictional")["submissions"])

    def test_retry_after_repair_save_failure_reuses_committed_activity(self):
        with patch("harness_core.activities.staging_directory", side_effect=PermissionError("fictional denial")):
            with self.assertRaises(OSError):
                publish(self.h, "fictional", self.spec())
        repair = self.h.state("fictional")["repairs"][0]
        with patch.object(self.h, "record", side_effect=PermissionError("fictional repair write failure")):
            with self.assertRaises(PermissionError):
                retry_publication(self.h, "fictional", repair["id"])
        retry_publication(self.h, "fictional", repair["id"])
        self.assertEqual(len(self.h.state("fictional")["activities"]), 1)

    def test_simultaneous_publication_recovery_does_not_create_two_versions(self):
        with patch("harness_core.activities.staging_directory", side_effect=PermissionError("fictional denial")):
            with self.assertRaises(OSError):
                publish(self.h, "fictional", self.spec())
        repair = self.h.state("fictional")["repairs"][0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: retry_publication(self.h, "fictional", repair["id"]), range(2)))
        self.assertEqual(len(results), 2)
        self.assertEqual(len(self.h.state("fictional")["activities"]), 1)

    def test_unwritable_journal_never_claims_a_saved_publication_repair(self):
        with patch("harness_core.activities.staging_directory", side_effect=PermissionError("fictional denied publication")), \
             patch.object(self.h, "record", side_effect=PermissionError("fictional denied journal")):
            with self.assertRaisesRegex(OSError, "could not be saved"):
                publish(self.h, "fictional", self.spec())
        self.assertFalse(self.h.state("fictional")["repairs"])
        self.assertFalse(self.h.state("fictional")["activities"])

    def test_session_retry_remains_valid_after_graph_scope_changes(self):
        evidence = self.h.record("fictional", "observation", {"role": "user", "kind": "conversation", "text": "Fictional attempt"})
        payload = self.session(records=[{"kind": "coverage", "payload": {"concept_ids": ["claims"],
            "stage": "practised", "reason": "Fictional practice", "evidence_ids": [evidence["id"]]}}])
        saved = self.h.record("fictional", "session", payload)
        graph = self.graph(); graph["nodes"] = graph["nodes"][1:]
        self.h.record("fictional", "graph", graph)
        self.assertEqual(self.h.record("fictional", "session", payload), saved)

    def test_publication_committed_before_projection_failure_returns_identity(self):
        with patch.object(self.h, "_snapshot", side_effect=PermissionError("fictional projection denied")):
            result = publish(self.h, "fictional", self.spec())
        self.assertIn(result["activity"], self.h.state("fictional")["activities"])
        self.assertIn("committed", result["warning"])
        self.assertFalse(self.h.state("fictional")["repairs"])

    def test_session_author_qa_and_stale_new_save_are_rejected(self):
        with patch.dict(os.environ, {"COURSE_AUTHOR_QA": "1"}):
            with self.assertRaises(Invalid):
                self.h.record("fictional", "session", self.session())
        with self.assertRaisesRegex(Invalid, "New records arrived"):
            self.h.record("fictional", "session", self.session(), expected_revision="old")

    def test_cli_roundtrips_unicode_even_with_legacy_python_io_encoding(self):
        script = Path(__file__).resolve().parents[1] / "learn.py"
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        literal = self.session()["records"][1]["payload"]["text"]
        saved = subprocess.run([sys.executable, str(script), "--courses", str(self.h.store.courses), "record", "fictional", "session", "-"],
            input=json.dumps(self.session(), ensure_ascii=False).encode("utf-8"), capture_output=True, env=env, timeout=15)
        self.assertEqual(saved.returncode, 0, saved.stderr.decode("utf-8"))
        event = json.loads(saved.stdout.decode("utf-8"))
        self.assertEqual(event["payload"]["records"][1]["payload"]["text"], literal)
        resumed = subprocess.run([sys.executable, str(script), "--courses", str(self.h.store.courses), "resume", "fictional"], capture_output=True, env=env, timeout=15)
        self.assertEqual(resumed.returncode, 0, resumed.stderr.decode("utf-8"))
        self.assertEqual(json.loads(resumed.stdout.decode("utf-8"))["recent_observations"][-1]["payload"]["text"], literal)
