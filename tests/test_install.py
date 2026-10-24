"""Distribution checks use isolated folders and explicitly fictional evidence."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.request import ProxyHandler, build_opener
import zipfile

from harness_core.engine import Harness

ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fieldnotes-fictional-install-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "Fictional learning records"
        self.skills = self.root / "agent skills"
        self.skill = self.skills / "learning-guide"
        self.env = dict(os.environ)
        self.env.pop("FIELDNOTES_HOME", None)
        self.env.pop("PYTHONPATH", None)

    def command(self, *args, success=True, env=None):
        result = subprocess.run([sys.executable, *map(str, args)], cwd=self.root,
                                env=env or self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def install(self, *args, success=True):
        return self.command(ROOT / "install.py", "--target", "codex", "--skills-dir", self.skills,
                            "--data-dir", self.data, *args, success=success)

    def test_installed_runtime_is_self_contained_and_update_preserves_evidence(self):
        self.install()
        self.assertFalse(self.data.exists(), "Installation must not create learner state")
        h = Harness(self.data / "courses")
        h.create("fictional", "Fictional installation QA", "Fictional fixture; no learner conclusions", fictional=True)
        before = {p.relative_to(self.data): p.read_bytes() for p in self.data.rglob("*") if p.is_file()}
        result = json.loads(self.command(self.skill / "learn.py", "list").stdout)
        self.assertEqual(result["courses"][0]["id"], "fictional")
        self.assertEqual(Path(result["courses_root"]), self.data / "courses")
        claude_skills = self.root / "claude skills"
        self.command(ROOT / "install.py", "--target", "claude", "--skills-dir", claude_skills, "--data-dir", self.data)
        resumed = json.loads(self.command(claude_skills / "learning-guide/learn.py", "resume", "fictional").stdout)
        self.assertEqual(resumed, h.resume("fictional"))
        # No --data-dir on update: the installed choice must be preserved.
        self.command(ROOT / "install.py", "--target", "codex", "--skills-dir", self.skills, "--update")
        after = {p.relative_to(self.data): p.read_bytes() for p in self.data.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(json.loads(self.command(self.skill / "learn.py", "list").stdout)["courses_root"], str(self.data / "courses"))
        self.assertFalse((self.skill / "courses").exists())

    def test_refuses_conflicts_and_data_inside_installation(self):
        self.skill.mkdir(parents=True)
        note = self.skill / "personal.txt"
        note.write_text("unrelated skill", encoding="utf-8")
        self.install("--update", success=False)
        self.assertEqual(note.read_text(), "unrelated skill")
        note.unlink()
        self.skill.rmdir()
        self.command(ROOT / "install.py", "--target", "codex", "--skills-dir", self.skills,
                     "--data-dir", self.skill / "private-data", success=False)
        self.assertFalse(self.skill.exists())
        self.install()
        self.install(success=False)
        (self.skill / "courses").mkdir()
        self.install("--update", success=False)
        self.assertTrue((self.skill / "courses").exists())

    def test_environment_and_explicit_course_overrides(self):
        self.install()
        env = {**self.env, "FIELDNOTES_HOME": str(self.root / "session-data")}
        report = json.loads(self.command(self.skill / "learn.py", "doctor", env=env).stdout)
        self.assertEqual(report["courses_root"], str(self.root / "session-data/courses"))
        report = json.loads(self.command(self.skill / "learn.py", "--courses", self.root / "other-courses", "doctor", env=env).stdout)
        self.assertEqual(report["courses_root"], str(self.root / "other-courses"))

    def test_zip_has_runtime_valid_references_and_no_private_or_checkout_files(self):
        output = self.root / "learning-guide.zip"
        self.command(ROOT / "install.py", "--package", output)
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertTrue(all(n.startswith("learning-guide/") for n in names))
            self.assertFalse(any(part in {"courses", ".git", ".runtime", "__pycache__", "tests"}
                                 for n in names for part in Path(n).parts))
            self.assertIsNone(json.loads(archive.read("learning-guide/fieldnotes.json"))["data_dir"])
            archive.extractall(self.root / "extracted")
        bundle = self.root / "extracted/learning-guide"
        for relative in ["SKILL.md", "references/contracts.md", "references/learning-activity.md", "references/learning-research.md"]:
            text = (bundle / relative).read_text()
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" not in target:
                    self.assertTrue(((bundle / relative).parent / target).is_file(), target)
        self.command(bundle / "learn.py", "--courses", self.data / "courses", "doctor")
        self.command(ROOT / "install.py", "--package", output, success=False)

    def test_packaged_dashboard_serves_without_checkout_assets(self):
        self.install()
        proc = subprocess.Popen([sys.executable, str(self.skill / "learn.py"), "serve", "--port", "0"],
                                cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = proc.stdout.readline().strip()
            self.assertTrue(line.startswith("Learning dashboard: http://127.0.0.1:"), line)
            base = line.removeprefix("Learning dashboard: ")
            opener = build_opener(ProxyHandler({}))
            for path in ["/", "/app.js", "/styles.css", "/bridge.js"]:
                with opener.open(base + path, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.read())
        finally:
            proc.terminate()
            proc.communicate(timeout=5)

    def test_chatgpt_plugin_preserves_other_marketplace_entries(self):
        home = self.root / "fictional-desktop"
        catalog_path = home / ".agents/plugins/marketplace.json"
        catalog_path.parent.mkdir(parents=True)
        existing = {"name": "my-plugins", "plugins": [{"name": "other", "source": "./other"}], "custom": "preserve"}
        catalog_path.write_text(json.dumps(existing), encoding="utf-8")
        args = [ROOT / "install.py", "--target", "chatgpt", "--marketplace-root", home, "--data-dir", self.data]
        self.command(*args)
        catalog = json.loads(catalog_path.read_text())
        self.assertEqual(catalog["plugins"][0], existing["plugins"][0])
        self.assertEqual(catalog["custom"], "preserve")
        plugin = home / catalog["plugins"][1]["source"]["path"]
        manifest = json.loads((plugin / "plugin.json").read_text())
        self.assertTrue((plugin / manifest["extensions"]["com.openai"]["onboardingSkill"]).is_file())
        self.command(plugin / "skills/learning-guide/learn.py", "doctor")
        self.command(*args, "--update")
        self.assertEqual(len(json.loads(catalog_path.read_text())["plugins"]), 2)
        self.assertFalse(self.data.exists())

    def test_invalid_marketplace_is_left_untouched_before_install(self):
        home = self.root / "fictional-desktop"
        catalog_path = home / ".agents/plugins/marketplace.json"
        catalog_path.parent.mkdir(parents=True)
        catalog_path.write_text('{"plugins": false}', encoding="utf-8")
        self.command(ROOT / "install.py", "--target", "chatgpt", "--marketplace-root", home, success=False)
        self.assertEqual(catalog_path.read_text(), '{"plugins": false}')
        self.assertFalse((home / ".codex/plugins").exists())
