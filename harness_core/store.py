"""Atomic, locked, append-only course journals with verified hash chains."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import uuid


class Invalid(ValueError):
    pass


def now():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat()


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise Invalid("Use a timezone-aware ISO 8601 timestamp") from exc


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value):
        raise Invalid("Identity must contain 1–80 lowercase letters, digits, underscores or hyphens")
    return value


def text(value, label, limit=100000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Invalid(f"{label} must be nonempty text (at most {limit} characters)")
    return value


def safe_path(root, relative):
    root = Path(root).resolve()
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or Path(relative).is_absolute() or PureWindowsPath(relative).drive
            or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise Invalid("Use a relative path inside the course")
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise Invalid("Course paths cannot traverse symbolic links")
    result = cursor.resolve()
    if not result.is_relative_to(root):
        raise Invalid("Path escapes the course")
    return result


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise Invalid(f"Cannot read {path}: {exc}") from exc


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Store:
    def __init__(self, courses):
        self.courses = Path(courses).expanduser().resolve()

    def root(self, course):
        return safe_path(self.courses, identity(course))

    def config(self, course):
        value = read_json(safe_path(self.root(course), "course.json"))
        if value.get("id") != course or value.get("schema_version") != 1:
            raise Invalid("Invalid course manifest")
        return value

    @contextmanager
    def locked(self, course):
        self.config(course)
        with safe_path(self.root(course), ".lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def events(self, course):
        config = self.config(course)
        directory = safe_path(self.root(course), "evidence/events")
        events, previous = [], None
        for path in sorted(directory.glob("*.json")):
            if path.is_symlink():
                raise Invalid("Evidence cannot be a symbolic link")
            event = read_json(path)
            checksum = event.pop("sha256", None)
            if (digest(event) != checksum or event.get("previous") != previous
                    or event.get("sequence") != len(events) + 1
                    or event.get("course_instance_id") != config["instance_id"]):
                raise Invalid(f"Evidence integrity failure: {path.name}")
            event["sha256"] = checksum
            events.append(event)
            previous = checksum
        return events

    def append_locked(self, course, kind, payload, *, at=None):
        events = self.events(course)
        event = {"schema_version": 1, "id": "e_" + uuid.uuid4().hex,
                 "sequence": len(events) + 1, "course_instance_id": self.config(course)["instance_id"],
                 "type": kind, "at": stamp(at or now()), "payload": payload,
                 "previous": events[-1]["sha256"] if events else None}
        event["sha256"] = digest(event)
        target = safe_path(self.root(course), f"evidence/events/{event['sequence']:08d}-{event['id']}.json")
        atomic_json(target, event)
        return event

    def create(self, course, title, goal, *, fictional=False, at=None):
        identity(course)
        text(title, "Title", 300)
        text(goal, "Goal")
        self.courses.mkdir(parents=True, exist_ok=True)
        root = self.root(course)
        try:
            root.mkdir()
        except FileExistsError as exc:
            raise Invalid("Course already exists; resume it or choose another ID") from exc
        for directory in ["evidence/events", "activities", "sources/library", "sources/catalog",
                          "sources/receipts", "research", "state", "drafts"]:
            (root / directory).mkdir(parents=True, exist_ok=True)
        config = {"schema_version": 1, "id": course, "instance_id": str(uuid.uuid4()),
                  "title": title, "original_goal": goal, "created_at": stamp(at or now()),
                  "harness_version": "0.1.0", "fictional": fictional}
        atomic_json(root / "course.json", config)
        (root / "AGENTS.md").write_text(
            "# Continue this learning journey\n\n"
            "Use the shared harness skills/learning-guide/SKILL.md. The shared harness is the folder "
            "containing learn.py; use --courses with this folder's parent if it has moved. "
            "Run learn.py resume COURSE_ID before teaching. Read the exact task and evidence referenced "
            "there. Keep the learner's literal responses, help, and judgments separate. "
            "Research and teach incrementally; there is no requirement to finish a course before learning. "
            "Use the tools for all evidence and state changes. Never invent learner work.\n",
            encoding="utf-8")
        with self.locked(course):
            self.append_locked(course, "goal", {"title": title, "goal": goal,
                "confirmed": False, "constraints": {}, "success_criteria": [], "reported_background": []}, at=at)
        return config
