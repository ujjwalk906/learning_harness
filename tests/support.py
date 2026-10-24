from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from harness_core.activities import publish
from harness_core.engine import Harness


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fieldnotes-fictional-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.at = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        self.h = Harness(self.root / "courses", clock=lambda: self.at)
        self.create("fictional")

    def create(self, course):
        self.h.create(course, "Fictional journey", "Fictional fixture; no learner conclusions", fictional=True)
        self.h.record(course, "goal", {"title": "Fictional journey", "goal": "Fictional fixture; no learner conclusions", "confirmed": True})
        self.h.record(course, "graph", self.graph())

    def graph(self):
        return {"rationale": "Fictional provisional graph", "nodes": [
            {"id": cid, "title": cid.title(), "goal_relevance": "Fictional goal", "target_capability": "Explain an observation",
             "requires": [], "sources": [], "provisional": True, "required": True} for cid in ["claims", "reasoning"]]}

    def spec(self, **overrides):
        result = {"title": "Fictional task", "instruction": "Explain the given observation", "why": "Fictional task selection",
            "concept_ids": ["claims"], "purpose": "check", "phase": "after_instruction", "evidence_scope": "assessment",
            "review_prompt": "Reconstruct the mechanism before opening notes",
            "criteria": [{"id": "scope", "concept_id": "claims", "description": "Explain the observation's limits"}]}
        result.update(overrides)
        return result

    def activity(self, *, course="fictional", activity_id=None, suffix=".md", source=None, **overrides):
        path = self.root / ("task" + suffix)
        path.write_text(source or "# Fictional task\n\nA supplied observation. Explain its limits.", encoding="utf-8")
        return publish(self.h, course, self.spec(**overrides), path, activity_id=activity_id)["activity"]

    def submit(self, activity=None, *, answer="Fictional literal answer", assistance=None, course="fictional", **kwargs):
        return self.h.submit(course, activity or self.activity(), answer, assistance if assistance is not None else [], **kwargs)

    def assessment(self, submission, *, course="fictional", verdict="correct", **overrides):
        activity = self.h.state(course)["activities"][submission["payload"]["activity"]]
        p = {"submission_id": submission["id"], "evaluator": "agent", "feedback": "Fictional actionable feedback",
            "limitations": "Fictional QA, not actual learner evidence", "findings": [
                {"criterion_id": c["id"], "concept_id": c["concept_id"], "verdict": verdict,
                 "rationale": "Fictional evidence rationale", "next_probe": "Fresh independent reasoning"} for c in activity["criteria"]]}
        p.update(overrides)
        return p

    def assess(self, submission, *, course="fictional", verdict="correct", **overrides):
        return self.h.assess(course, self.assessment(submission, course=course, verdict=verdict, **overrides))
