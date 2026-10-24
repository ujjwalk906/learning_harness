import base64
from copy import deepcopy
from datetime import timedelta

from harness_core.store import Invalid, stamp
from support import Fixture


class EvidenceTests(Fixture):
    def test_practice_and_pretest_do_not_become_independence(self):
        for scope, purpose, phase in [("guided", "practice", "after_instruction"), ("diagnostic", "pretest", "before_instruction")]:
            activity = self.activity(evidence_scope=scope, purpose=purpose, phase=phase)
            self.assess(self.submit(activity))
        state = self.h.state("fictional")
        self.assertEqual(state["progress"]["independent"], 0)
        self.assertEqual(state["reviews"], {})

    def test_observed_help_survives_claimed_unassisted_answer(self):
        activity = self.activity()
        hint = self.h.record("fictional", "observation", {"role": "observer", "kind": "help", "text": "Displayed a worked hint", "activity": activity})
        submission = self.submit(activity, assistance=[])
        assessment = self.assess(submission)
        state = self.h.state("fictional")
        self.assertIn(hint["id"], assessment["payload"]["observed_help_ids"])
        self.assertTrue(state["learner"]["claims"]["supported"])
        self.assertFalse(state["learner"]["claims"]["independent"])

    def test_unknown_assistance_and_self_judgment_are_not_independent(self):
        self.assess(self.submit(assistance=["unknown"]))
        self.assertFalse(self.h.state("fictional")["learner"]["claims"]["independent"])
        self.assess(self.submit(), evaluator="self")
        self.assertFalse(self.h.state("fictional")["learner"]["claims"]["independent"])

    def test_supported_success_does_not_erase_prior_independent_evidence(self):
        self.assess(self.submit())
        self.at += timedelta(hours=1)
        self.assess(self.submit(assistance=["targeted hint"]))
        state = self.h.state("fictional")["learner"]["claims"]
        self.assertTrue(state["independent"])
        self.assertTrue(state["supported"])
        self.assess(self.submit(), evaluator="self")
        self.assertTrue(self.h.state("fictional")["learner"]["claims"]["independent"])

    def test_actual_delay_advances_review_but_same_day_does_not(self):
        first = self.submit(); self.assess(first)
        initial = deepcopy(self.h.state("fictional")["reviews"]["claims"])
        self.at += timedelta(hours=2)
        self.assess(self.submit(self.activity(purpose="retrieval", phase="delayed")))
        repeated = self.h.state("fictional")["reviews"]["claims"]
        self.assertEqual(repeated["due_at"], initial["due_at"])
        self.assertFalse(self.h.state("fictional")["learner"]["claims"].get("delayed", False))
        self.at += timedelta(days=2)
        self.assess(self.submit(self.activity(purpose="retrieval", phase="delayed")))
        state = self.h.state("fictional")
        self.assertEqual(state["reviews"]["claims"]["step"], 1)
        self.assertEqual(state["reviews"]["claims"]["due_at"], stamp(self.at + timedelta(days=3)))
        self.assertTrue(state["learner"]["claims"]["delayed"])

    def test_delayed_label_without_prior_review_is_not_retention(self):
        self.assess(self.submit(self.activity(purpose="retrieval", phase="delayed")))
        self.assertFalse(self.h.state("fictional")["learner"]["claims"].get("delayed", False))

    def test_transfer_requires_changed_decision_and_later_failure_clears_readiness(self):
        with self.assertRaises(Invalid):
            self.activity(purpose="transfer")
        activity = self.activity(purpose="transfer", change="Changed constraint requires a new decision")
        self.assess(self.submit(activity))
        self.assertTrue(self.h.state("fictional")["learner"]["claims"]["transfer"])
        self.at += timedelta(hours=1)
        self.assess(self.submit(), verdict="incorrect")
        learner = self.h.state("fictional")["learner"]["claims"]
        self.assertFalse(learner["transfer"])
        self.assertFalse(learner["independent"])

    def test_schedule_has_no_mastery_credit_and_cannot_silently_postpone(self):
        schedule = {"concept_ids": ["claims"], "due_at": stamp(self.at + timedelta(days=1)),
                    "prompt": "Retrieve before reading", "reason": "First retrieval opportunity"}
        self.h.record("fictional", "schedule", schedule)
        self.assertEqual(self.h.state("fictional")["progress"]["independent"], 0)
        later = {**schedule, "due_at": stamp(self.at + timedelta(days=10))}
        self.h.record("fictional", "schedule", later)
        self.assertEqual(self.h.state("fictional")["reviews"]["claims"]["due_at"], schedule["due_at"])
        self.h.record("fictional", "schedule", {**later, "learner_override": True, "reason": "Fictional learner explicitly requested rescheduling"})
        self.assertEqual(self.h.state("fictional")["reviews"]["claims"]["due_at"], later["due_at"])

    def test_assessment_must_cite_latest_real_answer_and_cover_announced_criteria(self):
        activity = self.activity(); first = self.submit(activity)
        self.submit(activity, answer="A later literal answer")
        with self.assertRaisesRegex(Invalid, "Newer answer"):
            self.assess(first)
        latest = self.h.state("fictional")["pending"][-1]
        with self.assertRaises(Invalid):
            self.h.assess("fictional", {"submission_id": "invented"})
        p = self.assessment({"id": latest["id"], "payload": latest})
        p["findings"][0]["criterion_id"] = "unannounced"
        with self.assertRaisesRegex(Invalid, "announced criterion"):
            self.h.assess("fictional", p)

    def test_reassessment_preserves_history_without_extra_review_credit(self):
        submission = self.submit(); original = self.assess(submission)
        self.at += timedelta(days=5)
        with self.assertRaises(Invalid):
            self.assess(submission)
        self.assess(submission, supersedes=original["id"], feedback="Corrected wording with the same narrow evidence")
        state = self.h.state("fictional")
        self.assertEqual(state["reviews"]["claims"]["step"], 0)
        self.assertEqual(len([e for e in self.h.store.events("fictional") if e["type"] == "assessment"]), 2)

    def test_retry_is_idempotent_but_changed_payload_is_rejected(self):
        activity = self.activity()
        first = self.submit(activity, client_id="same-event")
        retry = self.submit(activity, client_id="same-event")
        self.assertEqual(first["id"], retry["id"])
        with self.assertRaisesRegex(Invalid, "different content"):
            self.submit(activity, answer="Different", client_id="same-event")

    def test_artifacts_remain_exact_after_file_edits(self):
        file = self.root / "response.txt"; file.write_text("Literal original bytes")
        event = self.submit(artifacts=[file])
        file.write_text("Later edits")
        snapshot = event["payload"]["artifacts"][0]
        self.assertEqual(base64.b64decode(snapshot["base64"]), b"Literal original bytes")

    def test_uploaded_artifact_names_and_sizes_are_validated(self):
        activity = self.activity()
        with self.assertRaises(Invalid):
            self.h.submit("fictional", activity, "Attached work", [], artifact_data=[{"name": "../escape", "base64": "YQ=="}])
        with self.assertRaises(Invalid):
            self.h.submit("fictional", activity, "Attached work", [], artifact_data=[{"name": "audio.wav", "base64": "not base64!"}])
