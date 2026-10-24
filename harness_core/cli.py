"""Shared agent tools. JSON inputs may be files or '-' for standard input."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from .engine import Harness
from .store import Invalid, read_json

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.load(sys.stdin) if path == "-" else read_json(path)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--courses", type=Path, default=ROOT / "courses", help="Parent directory containing course folders")
    p.add_argument("--runtime", type=Path, default=ROOT / ".runtime", help="Disposable private runtime directory")
    sub = p.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="Save an initial, unconfirmed learner goal")
    new.add_argument("id"); new.add_argument("--title", required=True); new.add_argument("--goal", required=True)
    sub.add_parser("list", help="Discover courses and read their dashboard summaries")
    for name in ["resume", "state", "pending", "rebuild", "verify-sources"]:
        sub.add_parser(name).add_argument("course")
    record = sub.add_parser("record", help="Publish a validated learning record")
    record.add_argument("course")
    record.add_argument("kind", choices=["goal", "graph", "resource", "plan", "observation", "checkpoint", "schedule", "status"])
    record.add_argument("file", help="JSON file or - for stdin")
    record.add_argument("--expected-revision", help="Reject stale agent publication")
    publish = sub.add_parser("publish", help="Snapshot an immutable activity and its assets")
    publish.add_argument("course"); publish.add_argument("file", help="Activity JSON specification")
    surface = publish.add_mutually_exclusive_group(required=True)
    surface.add_argument("--artifact", type=Path, help="Single entry file or a directory containing the declared entrypoint")
    surface.add_argument("--chat", action="store_true", help="Record the exact chat question without building a separate surface")
    publish.add_argument("--id", help="Existing activity ID creates a new version; old links stay intact")
    submit = sub.add_parser("submit", help="Save literal learner work, not generated answers")
    submit.add_argument("course"); submit.add_argument("activity", help="ACTIVITY_ID@v001")
    answer = submit.add_mutually_exclusive_group(required=True)
    answer.add_argument("--answer"); answer.add_argument("--answer-file", type=Path)
    help_group = submit.add_mutually_exclusive_group(required=True)
    help_group.add_argument("--unassisted", action="store_true"); help_group.add_argument("--assistance", action="append")
    submit.add_argument("--artifact", action="append", default=[], type=Path)
    submit.add_argument("--client-id", help="Stable identity for retrying the same submission")
    assess = sub.add_parser("assess", help="Record a separate criterion-based judgment against a real submission")
    assess.add_argument("course"); assess.add_argument("file", help="Assessment JSON file or -")
    evidence = sub.add_parser("evidence", help="Retrieve authoritative exact events, including raw artifacts")
    evidence.add_argument("course"); evidence.add_argument("id", nargs="?")
    serve = sub.add_parser("serve", help="Start the local dashboard and activity host")
    serve.add_argument("--port", type=int, default=8780); serve.add_argument("--jupyter-python", type=Path)
    notebook = sub.add_parser("notebook", help="Open an editable activity copy in an installed Jupyter environment")
    notebook.add_argument("course"); notebook.add_argument("activity"); notebook.add_argument("--python", type=Path)
    notebook.add_argument("--ai", action="store_true")
    sub.add_parser("stop-notebooks", help="Stop only notebooks launched through this runtime directory")
    acquire = sub.add_parser("acquire", help="Preserve licensed original material and immutable acquisition receipts")
    acquire.add_argument("course")
    for name in ["id", "title", "url", "license"]:
        acquire.add_argument("--" + name, required=True)
    acquire.add_argument("--license-file", action="append", required=True)
    acquire.add_argument("--method", choices=["file", "archive", "git", "local"], default="file")
    acquire.add_argument("--revision"); acquire.add_argument("--include", action="append", default=[])
    acquire.add_argument("--strip-components", type=int, default=0); acquire.add_argument("--sha256")
    acquire.add_argument("--filename"); acquire.add_argument("--reason", default="")
    acquire.add_argument("--role", default="primary-teaching", choices=["primary-teaching", "supporting-teaching", "technical-reference"])
    demo = sub.add_parser("demo", help="Build explicitly fictional fixtures in a separate directory")
    demo.add_argument("--output", type=Path, required=True)
    sub.add_parser("doctor", help="Read available optional tools; install nothing")
    return p


def dispatch(args):
    harness = Harness(args.courses)
    command = args.command
    if command == "new":
        return harness.create(args.id, args.title, args.goal)
    if command == "list":
        return harness.overview()
    if command == "resume":
        return harness.resume(args.course)
    if command == "state":
        return harness.state(args.course)
    if command == "pending":
        return harness.state(args.course)["pending"]
    if command == "record":
        return harness.record(args.course, args.kind, load(args.file), expected_revision=args.expected_revision)
    if command == "publish":
        from .activities import publish
        return publish(harness, args.course, load(args.file), args.artifact, activity_id=args.id)
    if command == "submit":
        answer = args.answer_file.read_text(encoding="utf-8") if args.answer_file else args.answer
        return harness.submit(args.course, args.activity, answer, [] if args.unassisted else args.assistance,
                              artifacts=args.artifact, client_id=args.client_id)
    if command == "assess":
        return harness.assess(args.course, load(args.file))
    if command == "evidence":
        events = harness.store.events(args.course)
        if not args.id:
            return [{k: e[k] for k in ["id", "sequence", "type", "at"]} for e in events]
        result = next((e for e in events if e["id"] == args.id), None)
        if result is None:
            raise Invalid("Evidence ID not found in this course")
        return result
    if command == "rebuild":
        harness._snapshot(args.course)
        return {"course": args.course, "revision": harness.state(args.course)["revision"], "rebuilt": "state/current.json and RESUME.md"}
    if command == "serve":
        from .server import serve
        serve(harness, args.port, runtime=args.runtime, jupyter_python=args.jupyter_python)
        return None
    if command == "notebook":
        from .workbench import open_notebook
        return open_notebook(harness, args.course, args.activity, args.runtime, python=args.python, ai=args.ai)
    if command == "stop-notebooks":
        from .workbench import stop_all
        stop_all(args.runtime)
        return {"status": "Owned notebook servers stopped"}
    if command == "verify-sources":
        from .sources import verify
        return verify(harness.store.root(args.course))
    if command == "acquire":
        from .sources import acquire
        harness.store.config(args.course)
        return acquire(harness.store.root(args.course), source_id=args.id, title=args.title, url=args.url,
            license=args.license, license_files=args.license_file, method=args.method, revision=args.revision,
            include=args.include, strip_components=args.strip_components, sha256=args.sha256,
            filename=args.filename, selection_reason=args.reason, role=args.role)
    if command == "demo":
        from .demo import make_demo
        return make_demo(args.output)
    if command == "doctor":
        return {"python": sys.version.split()[0], "courses_root": str(harness.store.courses),
                "optional_python": {name: importlib.util.find_spec(name) is not None for name in ["jupyterlab", "jupyter_ai", "IPython"]},
                "optional_commands": {name: shutil.which(name) for name in ["clang", "clang++", "cc", "g++", "node", "npm", "codex"]},
                "note": "The learning tools and dashboard use the standard library. No model or dependency was installed."}
    raise Invalid("Unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            if isinstance(result, dict) and result.get("ok") is False:
                raise SystemExit(1)
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
