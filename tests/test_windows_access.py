"""Optional real Windows sandbox regression; no model or real learner data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from harness_core.engine import Harness
from harness_core.filesystem import staging_directory


@unittest.skipUnless(os.name == "nt" and shutil.which("codex") and os.environ.get("FIELDNOTES_SANDBOX_QA") == "1",
                     "Set FIELDNOTES_SANDBOX_QA=1 on Windows with a configured Codex sandbox")
class WindowsAccessTests(unittest.TestCase):
    def test_installed_references_and_published_chat_remain_readable_in_sandbox(self):
        repo = Path(__file__).resolve().parents[1]
        with staging_directory(tempfile.gettempdir(), "fieldnotes-fictional-sandbox-") as root:
            skill = root / "skills/learning-guide"
            courses = root / "data/courses"
            subprocess.run([sys.executable, str(repo / "install.py"), "--target", "codex", "--skills-dir", str(skill.parent),
                            "--data-dir", str(courses.parent)], check=True, capture_output=True, timeout=30)
            h = Harness(courses)
            h.create("fictional", "Fictional access QA", "Fictional sandbox test", fictional=True)
            h.record("fictional", "goal", {"title": "Fictional access QA", "goal": "Fictional sandbox test", "confirmed": True})
            h.record("fictional", "graph", {"rationale": "Fictional scope", "nodes": [{"id": "claims", "title": "Claims",
                "goal_relevance": "Fictional", "target_capability": "Explain a limit", "provisional": True}]})
            spec = {"title": "Fictional test", "instruction": "Explain a limit", "why": "Fictional access QA",
                "review_prompt": "Recall later", "concept_ids": ["claims"], "purpose": "check", "phase": "after_instruction",
                "evidence_scope": "assessment", "criteria": [{"id": "limit", "concept_id": "claims", "description": "Explain the limit"}]}
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")

            def sandbox(*command):
                result = subprocess.run([shutil.which("codex"), "sandbox", "-C", str(root), "-P", ":workspace", *map(str, command)],
                    capture_output=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
                return result.stdout

            sandbox(sys.executable, "-c", "from pathlib import Path; import sys; [print(Path(p).read_text(encoding='utf-8')[:20]) for p in sys.argv[1:]]",
                    skill / "SKILL.md", skill / "references/contracts.md", skill / "references/testing.md")
            listed = json.loads(sandbox(sys.executable, skill / "learn.py", "list"))
            self.assertEqual(listed["courses"][0]["id"], "fictional")
            published = json.loads(sandbox(sys.executable, skill / "learn.py", "publish", "fictional", spec_path, "--chat", "--id", "access"))
            sandbox(sys.executable, "-c", "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text(encoding='utf-8'))",
                    Path(published["path"]) / "question.md")
