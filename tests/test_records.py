from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

from harness_core.engine import Harness
from harness_core.sources import acquire, verify
from harness_core.store import Invalid, read_json
from support import Fixture


class RecordTests(Fixture):
    def test_empty_workspace_is_read_only(self):
        parent = self.root / "untouched"
        self.assertEqual(Harness(parent).overview()["courses"], [])
        self.assertFalse(parent.exists())

    def test_course_is_self_contained_and_can_move(self):
        activity = self.activity()
        submission = self.submit(activity)
        self.h.record("fictional", "checkpoint", {"summary": "Actual fictional work saved", "next_action": "Discuss the literal answer", "activity": activity})
        destination = self.root / "moved"
        shutil.copytree(self.h.store.courses, destination)
        resumed = Harness(destination).resume("fictional")
        self.assertEqual(resumed["pending"][0]["answer"], "Fictional literal answer")
        self.assertEqual(resumed["pending"][0]["id"], submission["id"])
        self.assertEqual(resumed["checkpoint"]["activity"], activity)
        self.assertTrue((destination / "fictional/AGENTS.md").exists())

    def test_fresh_process_resumes_exact_state(self):
        activity = self.activity()
        self.submit(activity, answer="A literal response that must survive")
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "learn.py"),
                   "--courses", str(self.h.store.courses), "resume", "fictional"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["pending"][0]["answer"], "A literal response that must survive")

    def test_rebuild_does_not_use_or_trust_derived_state(self):
        root = self.h.store.root("fictional")
        (root / "state/current.json").write_text('{"invented":"mastery"}')
        self.assertNotIn("invented", self.h.state("fictional"))
        self.h._snapshot("fictional")
        self.assertEqual(read_json(root / "state/current.json")["progress"]["independent"], 0)

    def test_tampered_event_is_reported(self):
        path = next((self.h.store.root("fictional") / "evidence/events").glob("*.json"))
        event = read_json(path); event["payload"]["goal"] = "Changed behind the tools"
        path.write_text(json.dumps(event))
        with self.assertRaisesRegex(Invalid, "integrity"):
            self.h.state("fictional")

    def test_deleted_interior_event_is_reported(self):
        files = sorted((self.h.store.root("fictional") / "evidence/events").glob("*.json"))
        files[1].unlink()
        with self.assertRaisesRegex(Invalid, "integrity"):
            self.h.state("fictional")

    def test_concurrent_records_keep_complete_hash_chain(self):
        def save(i):
            return self.h.record("fictional", "observation", {"role": "user", "kind": "conversation", "text": f"FICTIONAL concurrent response {i}"})["id"]
        with ThreadPoolExecutor(max_workers=5) as pool:
            ids = list(pool.map(save, range(12)))
        self.assertEqual(len(set(ids)), 12)
        events = self.h.store.events("fictional")
        self.assertEqual([e["sequence"] for e in events], list(range(1, len(events) + 1)))

    def test_stale_agent_decision_is_rejected(self):
        revision = self.h.state("fictional")["revision"]
        self.h.record("fictional", "observation", {"role": "user", "kind": "conversation", "text": "New fictional information"})
        with self.assertRaisesRegex(Invalid, "New records"):
            self.h.record("fictional", "checkpoint", {"summary": "Old context", "next_action": "Unjustified"}, expected_revision=revision)

    def test_new_chat_plan_takes_precedence_over_old_activity_checkpoint(self):
        activity = self.activity()
        self.h.record("fictional", "checkpoint", {"summary": "Earlier task", "next_action": "Continue earlier task", "activity": activity})
        self.h.record("fictional", "plan", {"purpose": "Explain a prerequisite directly in conversation", "concept_ids": ["claims"],
            "why": "Fictional learner requested direct explanation", "support": "Worked comparison", "fade_check": "Fresh brief explanation"})
        resumed = self.h.resume("fictional")
        self.assertIsNone(resumed["current_activity"])
        self.assertEqual(resumed["summary"]["next_action"], "Explain a prerequisite directly in conversation")

    def test_graph_rejects_cycles_missing_dependencies_and_unrecorded_sources(self):
        graph = self.graph(); graph["nodes"][0]["requires"] = ["missing"]
        graph["nodes"][0]["prerequisite_rationale"] = {"missing": "Because it is needed"}
        with self.assertRaisesRegex(Invalid, "Unknown prerequisite"):
            self.h.record("fictional", "graph", graph)
        graph = self.graph()
        for node, parent in zip(graph["nodes"], ["reasoning", "claims"]):
            node["requires"] = [parent]; node["prerequisite_rationale"] = {parent: "Fictional dependency"}
        with self.assertRaisesRegex(Invalid, "cycle"):
            self.h.record("fictional", "graph", graph)
        graph = self.graph(); graph["nodes"][0]["sources"] = ["uninspected"]
        with self.assertRaisesRegex(Invalid, "unrecorded resource"):
            self.h.record("fictional", "graph", graph)

    def test_scope_revision_keeps_historical_evidence(self):
        activity = self.activity(); submission = self.submit(activity); self.assess(submission)
        graph = self.graph(); graph["nodes"] = graph["nodes"][1:]
        self.h.record("fictional", "graph", graph)
        state = self.h.state("fictional")
        self.assertEqual(state["graph"]["scope_version"], 2)
        self.assertEqual(state["progress"]["total"], 1)
        self.assertEqual(state["progress"]["independent"], 0)
        self.assertIn(submission["id"], state["submissions"])
        self.assertTrue(state["learner"]["claims"]["independent"])

    def test_cannot_escape_course_or_use_symlink(self):
        with self.assertRaises(Invalid):
            self.h.create("../escape", "Bad", "Bad")
        (self.h.store.courses / "linked").symlink_to(self.h.store.root("fictional"), target_is_directory=True)
        with self.assertRaises(Invalid):
            self.h.state("linked")

    def test_source_receipts_never_bless_original_edits(self):
        material = self.root / "material"; material.mkdir()
        (material / "LICENSE").write_text("CC0 fictional fixture")
        (material / "chapter.md").write_text("# Fictional material\nOriginal bytes")
        root = self.h.store.root("fictional")
        acquire(root, source_id="fictional-source", title="Fixture", url=str(material), method="local", license="CC0-1.0", license_files=["LICENSE"])
        receipt = (root / "sources/receipts/fictional-source.json").read_bytes()
        self.assertTrue(verify(root)["ok"])
        (root / "sources/library/fictional-source/chapter.md").write_text("Changed")
        self.assertFalse(verify(root)["ok"])
        self.assertEqual(receipt, (root / "sources/receipts/fictional-source.json").read_bytes())
        with self.assertRaisesRegex(Invalid, "source integrity"):
            self.activity()

    def test_qa_cannot_write_learner_evidence(self):
        activity = self.activity(); submission = self.submit(activity)
        with patch.dict(os.environ, {"COURSE_AUTHOR_QA": "1"}):
            with self.assertRaises(Invalid):
                self.submit(activity)
            with self.assertRaises(Invalid):
                self.assess(submission)
            with self.assertRaises(Invalid):
                self.h.record("fictional", "observation", {"role": "user", "kind": "conversation", "text": "Invented"})
