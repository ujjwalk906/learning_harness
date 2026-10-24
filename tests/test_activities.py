import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

from harness_core.activities import publish, public_activity, read_asset, render
from harness_core.notebook import c, cpp, run, Session
from harness_core.store import Invalid
from harness_core.tutor import environment, jupyter_configuration
from harness_core.workbench import open_notebook
from support import Fixture


class ActivityTests(Fixture):
    def test_old_versions_and_submissions_survive_replacement(self):
        first = self.activity(activity_id="stable")
        submitted = self.submit(first)
        second = self.activity(activity_id="stable", source="# Changed question\nNew literal inputs")
        self.assertEqual(first, "stable@v001")
        self.assertEqual(second, "stable@v002")
        self.assertIn(b"supplied observation", read_asset(self.h, "fictional", first, "task.md"))
        self.assertEqual(self.h.state("fictional")["submissions"][submitted["id"]]["activity"], first)

    def test_activity_integrity_failure_is_visible(self):
        activity = self.activity()
        record = self.h.state("fictional")["activities"][activity]
        path = self.h.store.root("fictional") / record["path"] / record["entrypoint"]
        path.write_text("Secretly replaced question")
        with self.assertRaisesRegex(Invalid, "altered"):
            read_asset(self.h, "fictional", activity, record["entrypoint"])

    def test_chat_question_needs_no_browser_surface_and_keeps_exact_criteria(self):
        result = publish(self.h, "fictional", self.spec(), activity_id="chat-question")
        activity = self.h.state("fictional")["activities"][result["activity"]]
        self.assertEqual(activity["surface"], "conversation")
        self.assertIn(b"Explain the observation's limits", read_asset(self.h, "fictional", result["activity"], "question.md"))
        self.assess(self.submit(result["activity"]))
        self.assertEqual(self.h.state("fictional")["progress"]["independent"], 1)

    def test_markdown_and_notebook_render_without_execution(self):
        markdown = self.activity(source="# A title\n<script>alert('x')</script>\n**Bold text**")
        content, mime = render(self.h, "fictional", markdown, "task.md")
        self.assertIn(b"&lt;script&gt;", content)
        self.assertIn(b"<strong>Bold text</strong>", content)
        notebook = {"nbformat": 4, "cells": [{"cell_type": "code", "source": ["raise RuntimeError('must not run')"]}]}
        activity = self.activity(suffix=".ipynb", source=json.dumps(notebook))
        content, _ = render(self.h, "fictional", activity, "task.ipynb")
        self.assertIn(b"must not run", content)

    def test_surface_bundle_keeps_local_assets_and_rejects_symlinks(self):
        bundle = self.root / "bundle"; bundle.mkdir()
        (bundle / "index.html").write_text('<script src="app.js"></script>')
        (bundle / "app.js").write_text("console.log('fixture')")
        result = publish(self.h, "fictional", self.spec(), bundle)
        self.assertIn(b"console.log", read_asset(self.h, "fictional", result["activity"], "app.js"))
        (bundle / "escape").symlink_to(self.root / "outside")
        with self.assertRaisesRegex(Invalid, "symbolic links"):
            publish(self.h, "fictional", self.spec(), bundle)

    def test_private_evaluation_is_excluded_from_public_metadata(self):
        activity = self.activity(private_evaluation="Hidden answer criteria")
        record = self.h.state("fictional")["activities"][activity]
        self.assertNotIn("private_evaluation", public_activity(record))
        with self.assertRaisesRegex(Invalid, "Unknown activity fields"):
            self.activity(expected_answer="Accidental public answer")

    def test_pretest_has_diagnostic_scope_and_publication_needs_agreed_goal(self):
        with self.assertRaises(Invalid):
            self.activity(purpose="pretest", phase="before_instruction", evidence_scope="assessment")
        self.h.create("unconfirmed", "Fictional", "Fictional goal", fictional=True)
        self.h.record("unconfirmed", "graph", self.graph())
        with self.assertRaisesRegex(Invalid, "Agree on the goal"):
            self.activity(course="unconfirmed")

    def test_native_c_and_cpp_are_real_compiled_processes(self):
        if not shutil.which("cc") or not shutil.which("g++"):
            self.skipTest("No native compiler")
        self.assertEqual(c('#include <stdio.h>\nint main(void){printf("%d\\n",6*7);return 0;}').stdout, "42\n")
        self.assertEqual(cpp('#include <iostream>\nint main(){std::cout << 7*6 << std::endl;}').stdout, "42\n")

    def test_timeout_kills_and_reports_failed_process(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=.05)

    def test_notebook_session_requires_exact_task_and_blocks_author_qa(self):
        activity = self.activity()
        session = Session("fictional", activity, courses=self.h.store.courses)
        with patch.dict(os.environ, {"COURSE_AUTHOR_QA": "1"}):
            with self.assertRaises(RuntimeError):
                session.submit("Invented", assistance=[])
        with self.assertRaises(ValueError):
            Session("fictional", "wrong@v001", courses=self.h.store.courses)

    def test_missing_jupyter_is_reported_without_installing(self):
        activity = self.activity(suffix=".ipynb", source=json.dumps({"nbformat": 4, "cells": []}))
        with patch("harness_core.workbench.subprocess.run") as probe:
            probe.return_value.returncode = 1
            with self.assertRaisesRegex(Invalid, "not installed"):
                open_notebook(self.h, "fictional", activity, self.root / "runtime")
            self.assertEqual(probe.call_count, 1)
            self.assertNotIn("pip", probe.call_args.args[0])

    def test_ai_profile_retains_course_goal_and_private_configuration(self):
        with patch("harness_core.tutor.shutil.which", return_value="/fictional/codex"):
            value = environment({"title": "Fictional course", "goal": "Explain evidence"}, self.root / "runtime", {})
        config = json.loads(value["CODEX_CONFIG"])
        self.assertEqual(config["sandbox_mode"], "read-only")
        self.assertIn("Explain evidence", config["developer_instructions"])
        self.assertIn("Do not automatically write", config["developer_instructions"])
        self.assertIn("mcp_port = 0", jupyter_configuration())

    def test_selected_venv_python_keeps_its_environment_path(self):
        activity = self.activity(suffix=".ipynb", source=json.dumps({"nbformat": 4, "cells": []}))
        python = self.root / "private-venv/bin/python"
        python.parent.mkdir(parents=True)
        python.symlink_to(sys.executable)
        with patch("harness_core.workbench.subprocess.run") as probe:
            probe.return_value.returncode = 1
            with self.assertRaises(Invalid):
                open_notebook(self.h, "fictional", activity, self.root / "runtime", python=python)
            self.assertEqual(probe.call_args.args[0][0], str(python))
