#!/usr/bin/env python3
"""Install Fieldnotes for Claude Code, Codex or ChatGPT desktop; build skill ZIPs.

Python 3.11+, macOS/Linux; standard library only. No network calls or pip installs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
NAME = "learning-guide"
OWNER = "https://github.com/ujjwalk906/learning_harness"
MARKER = "fieldnotes.json"


def check_platform():
    if sys.version_info < (3, 11):
        raise ValueError("Fieldnotes needs Python 3.11 or newer. Ask your agent to help install it.")
    if os.name != "posix":
        raise ValueError("Use macOS, Linux, or a Linux environment in WSL. Native Windows is not supported.")


def payload():
    """Explicit allowlist: never distribute courses, credentials, caches or QA."""
    files = {Path("SKILL.md"): ROOT / "skills/learning-guide/SKILL.md",
             Path("learn.py"): ROOT / "scripts/installed_learn.py",
             Path("LICENSE"): ROOT / "LICENSE",
             Path("agents/openai.yaml"): ROOT / "skills/learning-guide/agents/openai.yaml",
             Path("references/contracts.md"): ROOT / "skills/learning-guide/references/contracts.md",
             Path("references/learning-activity.md"): ROOT / "skills/learning-activity/SKILL.md",
             Path("references/learning-research.md"): ROOT / "skills/learning-research/SKILL.md",
             Path("docs/jupyter-ai.md"): ROOT / "docs/jupyter-ai.md"}
    for folder, suffixes in [("harness_core", {".py"}), ("web", {".html", ".css", ".js"})]:
        for source in sorted((ROOT / folder).iterdir()):
            if source.suffix in suffixes:
                files[Path(folder) / source.name] = source
    result = {}
    for relative, source in files.items():
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing or linked distribution source: {source}")
        data = source.read_bytes()
        if relative == Path("SKILL.md"):
            data = data.replace(b"../learning-activity/SKILL.md", b"references/learning-activity.md")
            data = data.replace(b"../learning-research/SKILL.md", b"references/learning-research.md")
        # Companion skills become references, rather than separately discovered skills.
        if relative.name in {"learning-activity.md", "learning-research.md"}:
            data = data.split(b"---", 2)[2].lstrip()
        result[relative] = data
    return result


def config(data_dir=None):
    return {"source": OWNER, "format": 1, "data_dir": str(data_dir) if data_dir else None}


def build(folder, data_dir=None, plugin=False):
    if plugin:
        build(folder / "skills" / NAME, data_dir)
        manifest = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            "name": "fieldnotes", "version": "0.1.0",
            "description": "A personal learning guide with saved goals, activities, feedback and reviews.",
            "repository": OWNER, "license": "MIT",
            "extensions": {"com.openai": {
                "onboardingSkill": "./skills/learning-guide/SKILL.md",
                "interface": {"displayName": "Fieldnotes", "shortDescription": "Learn with a guide and keep your progress",
                              "category": "Productivity", "capabilities": ["Read", "Write"]}}}}
        (folder / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (folder / MARKER).write_text(json.dumps(config(data_dir), indent=2) + "\n", encoding="utf-8")
        return
    for relative, data in payload().items():
        dest = folder / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    (folder / MARKER).write_text(json.dumps(config(data_dir), indent=2) + "\n", encoding="utf-8")


def package(output):
    output = output.expanduser().absolute()
    if output.suffix != ".zip":
        raise ValueError("The package filename must end in .zip")
    files = payload()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids silently replacing a downloaded/released artifact.
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, data in files.items():
            archive.writestr(f"{NAME}/{relative.as_posix()}", data)
        archive.writestr(f"{NAME}/{MARKER}", json.dumps(config(), indent=2) + "\n")
    print(f"Skill ZIP: {output}")
    print("Includes the tutor instructions, research/activity guides, tools and dashboard. No learner data.")


def plan_destination(skills_dir, data_dir, update, name=NAME):
    # Resolve the parent, but reject a linked destination instead of following it.
    dest = skills_dir.expanduser().resolve() / name
    if dest.is_symlink():
        raise ValueError(f"Refusing to replace a linked skill: {dest}")
    saved = None
    if dest.exists():
        marker = dest / MARKER
        if not dest.is_dir() or not marker.is_file() or marker.is_symlink():
            raise ValueError(f"An unrelated skill already exists at {dest}; choose another --skills-dir.")
        saved = json.loads(marker.read_text(encoding="utf-8"))
        if not isinstance(saved, dict) or saved.get("source") != OWNER or saved.get("format") != 1:
            raise ValueError(f"Unrecognized installation at {dest}; it was left untouched.")
        if not update:
            raise ValueError(f"Fieldnotes is already installed at {dest}. Use --update to replace its code.")
        if (dest / "courses").exists() or (dest / "skills" / NAME / "courses").exists():
            raise ValueError(f"Move the courses folder out of {dest} before updating; learner data was left untouched.")
    selected_data = data_dir or (saved or {}).get("data_dir") or Path.home() / "Fieldnotes"
    selected_data = Path(selected_data).expanduser().resolve()
    if selected_data == dest or selected_data.is_relative_to(dest) or dest.is_relative_to(selected_data):
        raise ValueError("Choose a data folder separate from the installed skill folder.")
    return dest, selected_data


def install(dest, data_dir, plugin=False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fieldnotes-install-", dir=dest.parent) as temp:
        stage = Path(temp) / NAME
        build(stage, data_dir, plugin=plugin)
        entry = Path("skills") / NAME / "learn.py" if plugin else Path("learn.py")
        # Exercise the packaged runtime before replacing an existing installation.
        subprocess.run([sys.executable, str(stage / entry), "doctor"], check=True, capture_output=True, text=True, timeout=30)
        backup = Path(temp) / "previous"
        if dest.exists():
            dest.rename(backup)
        try:
            stage.rename(dest)
        except OSError:
            if backup.exists():
                backup.rename(dest)
            raise
    print(f"Installed: {dest}")
    print(f"Learning records: {data_dir / 'courses'}")
    print(f'Tools: {sys.executable} "{dest / entry}" list')


def marketplace(root):
    """Merge one local entry, leaving other plugins and metadata intact."""
    path = root / ".agents/plugins/marketplace.json"
    if path.is_symlink():
        raise ValueError(f"Refusing to replace a linked marketplace: {path}")
    catalog = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "name": "personal", "interface": {"displayName": "Personal plugins"}, "plugins": []}
    if not isinstance(catalog, dict) or not isinstance(catalog.get("name"), str) or not isinstance(catalog.get("plugins"), list):
        raise ValueError(f"Unrecognized marketplace at {path}; it was left untouched.")
    entry = {"name": "fieldnotes", "source": {"source": "local", "path": "./.codex/plugins/fieldnotes"},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}
    for existing in catalog["plugins"]:
        if not isinstance(existing, dict):
            raise ValueError(f"Unrecognized marketplace entry at {path}; it was left untouched.")
        if existing.get("name") == "fieldnotes":
            if existing.get("source") != entry["source"]:
                raise ValueError("An unrelated fieldnotes plugin is already registered; marketplace was left untouched.")
            return path, catalog
    catalog["plugins"].append(entry)
    return path, catalog


def save_marketplace(path, catalog):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        json.dump(catalog, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["claude", "codex", "chatgpt", "both"], default="both", help="Agent to install for (both means Claude Code and Codex)")
    parser.add_argument("--skills-dir", type=Path, help="Override one agent's skill directory; requires a single --target")
    parser.add_argument("--data-dir", type=Path, help="Persistent data folder (default: ~/Fieldnotes; preserved on update)")
    parser.add_argument("--update", action="store_true", help="Replace a recognized installation's code; preserve external learning records")
    parser.add_argument("--package", type=Path, help="Only build a portable skill ZIP; do not install")
    parser.add_argument("--marketplace-root", type=Path, help="ChatGPT marketplace root (default: your home folder)")
    args = parser.parse_args(argv)
    try:
        check_platform()
        if args.package:
            if args.skills_dir or args.data_dir or args.update or args.marketplace_root:
                raise ValueError("Use --package without installation options; portable ZIPs contain no machine-specific paths.")
            package(args.package)
            return
        if args.marketplace_root and args.target != "chatgpt":
            raise ValueError("Use --marketplace-root with --target chatgpt.")
        if args.skills_dir and args.target in {"both", "chatgpt"}:
            raise ValueError("Use --target claude or --target codex with --skills-dir.")
        if args.target == "chatgpt":
            root = (args.marketplace_root or Path.home()).expanduser().resolve()
            path, catalog = marketplace(root)
            dest, data = plan_destination(root / ".codex/plugins", args.data_dir, args.update, name="fieldnotes")
            install(dest, data, plugin=True)
            save_marketplace(path, catalog)
            print(f"Plugin source prepared in {path}. Restart ChatGPT desktop, open Plugins, select your personal source, and install Fieldnotes.")
            print("Then run its setup or ask Fieldnotes to help you learn. This does not publish a public plugin.")
            return
        targets = ["claude", "codex"] if args.target == "both" else [args.target]
        directories = {"claude": Path.home() / ".claude/skills", "codex": Path.home() / ".agents/skills"}
        # Preflight all targets before writing either one.
        plans = [plan_destination(args.skills_dir or directories[target], args.data_dir, args.update) for target in targets]
        for dest, data in plans:
            install(dest, data)
        print("Ready. Start a new agent conversation and say: Use learning-guide. Help me learn [your goal].")
        print("If the skill is not listed yet, restart your agent app. Both agents can use the same saved courses.")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Setup could not finish: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
