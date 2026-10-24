"""Validated agent operations and deterministic projections of real learner evidence."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import uuid

from .store import Invalid, Store, atomic_json, identity, now, safe_path, stamp, text, timestamp

INTERVALS = (1, 3, 7, 14, 30, 60)
PURPOSES = {"pretest", "practice", "check", "retrieval", "transfer", "exploration"}


def require(condition, message):
    if not condition:
        raise Invalid(message)


def string_list(value, label, *, nonempty=False):
    require(isinstance(value, list) and (not nonempty or value), f"{label} must be a list")
    for item in value:
        text(item, label)
    require(len(set(value)) == len(value), f"{label} contains duplicates")
    return value


def latest(events, kind, default=None):
    return next((e["payload"] for e in reversed(events) if e["type"] == kind), default)


def activity_key(activity):
    return activity["id"] + "@" + activity["version"]


def projection(config, events, *, at=None):
    """Read model only: never infer competence from visits, chat, runs or drafts."""
    at = at or now()
    goal = latest(events, "goal", {"title": config["title"], "goal": config["original_goal"], "confirmed": False})
    graph = latest(events, "graph", {"nodes": [], "rationale": "No graph yet; starting knowledge is unassessed"})
    resources = {e["payload"]["id"]: e["payload"] for e in events if e["type"] == "resource"}
    activities = {activity_key(e["payload"]): {**e["payload"], "published_at": e["at"]}
                  for e in events if e["type"] == "activity"}
    submissions = {e["id"]: {**e["payload"], "id": e["id"], "at": e["at"], "sequence": e["sequence"]}
                   for e in events if e["type"] == "submission"}
    assessments = {e["payload"]["submission_id"]: {**e["payload"], "id": e["id"], "at": e["at"]}
                   for e in events if e["type"] == "assessment"}
    reviews, learner = {}, {}
    # Explicit review plans and assessed attempts are replayed in observation order.
    timeline = [(e["at"], e["sequence"], "schedule", e["payload"]) for e in events if e["type"] == "schedule"]
    for submission in submissions.values():
        assessment = assessments.get(submission["id"])
        if assessment:
            timeline.append((submission["at"], submission["sequence"], "assessment", (submission, assessment)))
    for occurred, _, kind, value in sorted(timeline, key=lambda item: (timestamp(item[0]), item[1])):
        if kind == "schedule":
            for cid in value["concept_ids"]:
                existing = reviews.get(cid)
                if existing and not value.get("learner_override") and timestamp(value["due_at"]) > timestamp(existing["due_at"]):
                    continue
                reviews[cid] = {"concept_id": cid, "due_at": value["due_at"], "prompt": value["prompt"],
                                "reason": value["reason"], "step": existing["step"] if existing else 0,
                                "status": "scheduled-retrieval", "evidence_id": None}
            continue
        submission, assessment = value
        activity = activities[submission["activity"]]
        guided = activity["evidence_scope"] != "assessment"
        unassisted = submission["assistance"] == [] and assessment["evaluator"] != "self"
        for cid in activity["concept_ids"]:
            findings = [f for f in assessment["findings"] if f["concept_id"] == cid]
            passed = bool(findings) and all(f["verdict"] == "correct" for f in findings)
            previous = learner.get(cid, {})
            record = {**previous, "last_evidence": submission["id"], "assessment_id": assessment["id"],
                      "last_at": occurred, "rationale": " ".join(f["rationale"] for f in findings),
                      "next_probe": " ".join(f.get("next_probe", "") for f in findings),
                      "uncertainty": "Limited to saved tasks, observed help and declared assistance"}
            if activity["purpose"] != "pretest":
                record["practiced"] = True
            if guided and passed:
                record["supported"] = True
            if not guided:
                record["independent"] = (passed and unassisted) or (passed and previous.get("independent", False))
                record["supported"] = passed and not unassisted
                # A contradiction requires fresh evidence; old successes remain in the journal.
                if not passed:
                    record["transfer"] = False
                    record["delayed"] = False
                if passed and unassisted and activity["purpose"] == "transfer":
                    record["transfer"] = True
            learner[cid] = record
            if guided:
                continue
            prior = reviews.get(cid)
            step = prior["step"] if prior else 0
            successful = passed and unassisted
            delayed = (successful and activity["phase"] == "delayed" and prior is not None
                       and timestamp(occurred) >= timestamp(prior["due_at"]))
            if delayed:
                step = min(step + 1, len(INTERVALS) - 1)
                learner[cid]["delayed"] = True
            elif successful and prior:
                continue  # An immediate repeat cannot push an existing review out.
            elif not successful:
                step = 0
            due = stamp(timestamp(occurred) + timedelta(days=INTERVALS[step]))
            if prior and not successful and timestamp(prior["due_at"]) < timestamp(due):
                due = prior["due_at"]
            reviews[cid] = {"concept_id": cid, "due_at": due, "step": step,
                "prompt": activity.get("review_prompt") or "Reconstruct the mechanism before reopening the explanation; then attempt a changed example.",
                "reason": "Successful delayed retrieval" if delayed else "Fresh independent retrieval is still needed",
                "status": "delayed-observed" if delayed else ("independent-attempt" if successful else "practice-needed"),
                "evidence_id": submission["id"]}
    for review in reviews.values():
        review["due"] = timestamp(review["due_at"]) <= at
    targets = [n for n in graph["nodes"] if n.get("required", True)]
    counts = {dimension: sum(bool(learner.get(n["id"], {}).get(dimension)) for n in targets)
              for dimension in ["practiced", "independent", "transfer", "delayed"]}
    counts["total"] = len(targets)
    counts["unassessed"] = sum(n["id"] not in learner for n in targets)
    latest_submissions = {s["activity"]: s for s in submissions.values()}
    pending = [s for s in latest_submissions.values() if s["id"] not in assessments]
    plan = latest(events, "plan", None)
    checkpoint = latest(events, "checkpoint", None)
    status = latest(events, "status", {"status": "active"})["status"]
    navigation = next((e["payload"] for e in reversed(events) if e["type"] in {"plan", "checkpoint"}), None)
    return {"course": config, "goal": goal, "graph": graph, "resources": list(resources.values()),
            "activities": activities, "submissions": submissions, "assessments": assessments,
            "learner": learner, "reviews": reviews, "progress": counts, "pending": pending,
            "plan": plan, "checkpoint": checkpoint, "navigation": navigation, "status": status,
            "revision": events[-1]["sha256"] if events else None,
            "updated_at": events[-1]["at"] if events else config["created_at"]}


class Harness:
    def __init__(self, courses, clock=now):
        self.store = Store(courses)
        self.clock = clock

    def create(self, course, title, goal, *, fictional=False):
        result = self.store.create(course, title, goal, fictional=fictional, at=self.clock())
        self._snapshot(course)
        return result

    def state(self, course):
        return projection(self.store.config(course), self.store.events(course), at=self.clock())

    def _concepts(self, state, ids):
        string_list(ids, "concept_ids", nonempty=True)
        known = {n["id"] for n in state["graph"]["nodes"]}
        require(set(ids) <= known, f"Unknown concepts: {sorted(set(ids) - known)}")

    def record(self, course, kind, payload, *, expected_revision=None):
        if kind in {"observation", "plan", "checkpoint", "schedule", "status"}:
            require(os.environ.get("COURSE_AUTHOR_QA") != "1", "Author QA cannot write learner records")
        require(isinstance(payload, dict), "Record must be a JSON object")
        payload = deepcopy(payload)
        with self.store.locked(course):
            state = self.state(course)
            if expected_revision is not None:
                require(state["revision"] == expected_revision, "New records arrived; resume before publishing this change")
            self._validate(kind, payload, state)
            event = self.store.append_locked(course, kind, payload, at=self.clock())
            self._snapshot(course)
            return event

    def _validate(self, kind, p, state):
        if kind == "goal":
            for field in ["title", "goal"]:
                text(p.get(field), field)
            require(type(p.get("confirmed")) is bool, "Record whether the learner agreed to the goal")
            for field in ["success_criteria", "reported_background"]:
                string_list(p.setdefault(field, []), field)
            require(isinstance(p.setdefault("constraints", {}), dict), "constraints must be an object")
            if state["goal"].get("confirmed") and p["goal"] != state["goal"]["goal"]:
                text(p.get("change_reason"), "Explain the learner-authorized goal change")
        elif kind == "graph":
            text(p.get("rationale"), "Graph rationale")
            require(isinstance(p.get("nodes"), list), "nodes must be a list")
            known, by_id = set(), {}
            resources = {r["id"] for r in state["resources"]}
            for node in p["nodes"]:
                require(isinstance(node, dict), "Each node must be an object")
                cid = identity(node.get("id"))
                require(cid not in known, "Duplicate concept")
                known.add(cid); by_id[cid] = node
                for field in ["title", "goal_relevance", "target_capability"]:
                    text(node.get(field), field)
                string_list(node.setdefault("requires", []), "requires")
                string_list(node.setdefault("sources", []), "sources")
                require(set(node["sources"]) <= resources, "Concept cites an unrecorded resource")
                require(type(node.setdefault("provisional", not node["sources"])) is bool, "provisional must be boolean")
                require(node["sources"] or node["provisional"], "Unsourced concepts must stay provisional")
                require(type(node.setdefault("required", True)) is bool, "required must be boolean")
                rationales = node.setdefault("prerequisite_rationale", {})
                require(isinstance(rationales, dict), "prerequisite_rationale must be an object")
                for parent in node["requires"]:
                    text(rationales.get(parent), "Explain each prerequisite")
            visited, active = set(), set()
            def visit(cid):
                require(cid in known, f"Unknown prerequisite: {cid}")
                require(cid not in active, "Prerequisite cycle")
                if cid in visited:
                    return
                active.add(cid)
                for parent in by_id[cid]["requires"]:
                    visit(parent)
                active.remove(cid); visited.add(cid)
            for cid in known:
                visit(cid)
            p["scope_version"] = state["graph"].get("scope_version", 0) + 1
        elif kind == "resource":
            identity(p.get("id"))
            for field in ["title", "url", "why", "inspection_notes"]:
                text(p.get(field), field)
            require(p["url"].startswith(("https://", "http://", "file://")), "Use an HTTP(S) or local file reference")
            string_list(p.setdefault("sections", []), "sections")
            p.setdefault("limitations", "Inspection notes are an agent judgment; consult the original for disputed claims.")
        elif kind == "plan":
            self._concepts(state, p.get("concept_ids"))
            for field in ["purpose", "why", "support", "fade_check"]:
                text(p.get(field), field)
            if p.get("activity"):
                require(p["activity"] in state["activities"], "Plan references an unknown activity version")
            if p.get("evidence_ids"):
                known = {e["id"] for e in self.store.events(state["course"]["id"])}
                require(set(string_list(p["evidence_ids"], "evidence_ids")) <= known, "Plan cites nonexistent evidence")
        elif kind == "observation":
            text(p.get("text"), "Literal observation")
            require(p.get("role") in {"user", "assistant", "observer"}, "role must be user, assistant or observer")
            require(p.get("kind") in {"conversation", "prediction", "execution", "help", "learner_feedback"}, "Unknown observation kind")
            if p.get("activity"):
                require(p["activity"] in state["activities"], "Unknown activity version")
        elif kind == "checkpoint":
            for field in ["summary", "next_action"]:
                text(p.get(field), field)
            if p.get("activity"):
                require(p["activity"] in state["activities"], "Unknown activity version")
            string_list(p.setdefault("open_questions", []), "open_questions")
            p.setdefault("draft", "")
        elif kind == "schedule":
            self._concepts(state, p.get("concept_ids"))
            timestamp(p.get("due_at"))
            for field in ["prompt", "reason"]:
                text(p.get(field), field)
            require(type(p.setdefault("learner_override", False)) is bool, "learner_override must be boolean")
        elif kind == "status":
            require(p.get("status") in {"active", "paused", "archived"}, "Use active, paused or archived")
            text(p.get("reason"), "Status reason")
        else:
            raise Invalid(f"Unsupported record type: {kind}")

    def validate_activity(self, p, state):
        require(state["goal"].get("confirmed"), "Agree on the goal before publishing an activity")
        allowed = {"title", "instruction", "why", "review_prompt", "concept_ids", "purpose", "phase",
                   "evidence_scope", "criteria", "change", "entrypoint", "private_evaluation"}
        require(set(p) <= allowed, f"Unknown activity fields: {sorted(set(p) - allowed)}. Put private answer criteria in private_evaluation.")
        for field in ["title", "instruction", "why", "review_prompt"]:
            text(p.get(field), field)
        self._concepts(state, p.get("concept_ids"))
        require(p.get("purpose") in PURPOSES, "Unknown activity purpose")
        require(p.get("phase") in {"before_instruction", "after_instruction", "delayed"}, "Unknown phase")
        require(p.get("evidence_scope") in {"diagnostic", "guided", "assessment"}, "Specify diagnostic, guided or assessment")
        if p["purpose"] == "pretest":
            require(p["phase"] == "before_instruction" and p["evidence_scope"] == "diagnostic", "Pretests are diagnostic attempts before instruction")
        if p["purpose"] == "transfer":
            text(p.get("change"), "Explain the meaningful change in the transfer task")
        criteria = p.get("criteria")
        require(isinstance(criteria, list) and criteria, "Supply announced assessment criteria")
        seen = set()
        for criterion in criteria:
            require(isinstance(criterion, dict), "Criterion must be an object")
            identity(criterion.get("id"))
            require(criterion["id"] not in seen, "Duplicate criterion")
            seen.add(criterion["id"])
            require(criterion.get("concept_id") in p["concept_ids"], "Criterion targets unknown concept")
            text(criterion.get("description"), "Criterion description")
        require({c["concept_id"] for c in criteria} == set(p["concept_ids"]), "Every targeted concept needs a criterion")

    def submit(self, course, activity, answer, assistance, *, client_id=None, artifacts=(), artifact_data=()):
        require(os.environ.get("COURSE_AUTHOR_QA") != "1", "Author QA cannot submit learner evidence")
        text(answer, "Literal answer")
        string_list(assistance, "assistance")
        if client_id:
            text(client_id, "Submission retry identity", 120)
        snapshots = []
        for path in map(Path, artifacts):
            require(path.is_file() and not path.is_symlink(), "Artifact must be a regular file")
            data = path.read_bytes()
            require(len(data) <= 8 * 1024 * 1024, "Artifact exceeds 8 MiB")
            snapshots.append({"name": path.name, "sha256": hashlib.sha256(data).hexdigest(),
                              "bytes": len(data), "base64": base64.b64encode(data).decode()})
        require(isinstance(artifact_data, (list, tuple)), "artifacts must be a list")
        for item in artifact_data:
            require(isinstance(item, dict), "Artifact must be an object")
            name = text(item.get("name"), "Artifact name", 250)
            require(Path(name).name == name and "/" not in name and "\\" not in name, "Use a filename without directories")
            try:
                data = base64.b64decode(item.get("base64", ""), validate=True)
            except (ValueError, TypeError) as exc:
                raise Invalid("Invalid artifact encoding") from exc
            require(0 < len(data) <= 8 * 1024 * 1024, "Artifact must contain 1 byte to 8 MiB")
            snapshots.append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                              "base64": base64.b64encode(data).decode()})
        require(sum(a["bytes"] for a in snapshots) <= 16 * 1024 * 1024, "Submission artifacts exceed 16 MiB total")
        with self.store.locked(course):
            state = self.state(course)
            require(activity in state["activities"], "Unknown activity version")
            for event in self.store.events(course):
                if client_id and event["type"] == "submission" and event["payload"].get("client_id") == client_id:
                    require(event["payload"]["activity"] == activity and event["payload"]["answer"] == answer
                            and event["payload"]["declared_assistance"] == assistance
                            and event["payload"].get("artifacts", []) == snapshots, "Retry identity reused with different content")
                    return event
            observed_help = [e["id"] for e in self.store.events(course) if e["type"] == "observation"
                and e["payload"].get("activity") == activity and e["payload"]["kind"] == "help"]
            effective_assistance = [*assistance]
            if observed_help:
                effective_assistance.append("observed activity help")
            event = self.store.append_locked(course, "submission", {"activity": activity, "answer": answer,
                "declared_assistance": assistance, "assistance": effective_assistance, "observed_help_ids": observed_help,
                "artifacts": snapshots, "client_id": client_id}, at=self.clock())
            self._snapshot(course)
            return event

    def assess(self, course, p):
        require(os.environ.get("COURSE_AUTHOR_QA") != "1", "Author QA cannot assess learner work")
        require(isinstance(p, dict), "Assessment must be an object")
        p = deepcopy(p)
        with self.store.locked(course):
            state = self.state(course)
            submission = state["submissions"].get(p.get("submission_id"))
            require(submission is not None, "Cite a real submission ID")
            same = [s for s in state["submissions"].values() if s["activity"] == submission["activity"]]
            require(same[-1]["id"] == submission["id"], "Newer answer exists; assess the latest saved answer")
            prior = state["assessments"].get(submission["id"])
            require(p.get("supersedes") == (prior["id"] if prior else None), "Reassessment must explicitly supersede the prior assessment")
            require(p.get("evaluator") in {"self", "agent", "human"}, "Name the evaluator")
            text(p.get("feedback"), "Actionable feedback")
            text(p.get("limitations"), "Assessment limitations")
            activity = state["activities"][submission["activity"]]
            criteria = {c["id"]: c for c in activity["criteria"]}
            findings = p.get("findings")
            require(isinstance(findings, list) and findings, "Supply findings")
            require(all(isinstance(f, dict) for f in findings), "Each finding must be an object")
            require(len(findings) == len(criteria) and {f.get("criterion_id") for f in findings} == criteria.keys(), "Cover every announced criterion exactly once")
            for finding in findings:
                criterion = criteria[finding["criterion_id"]]
                require(finding.get("concept_id") == criterion["concept_id"], "Finding targets the wrong concept")
                require(finding.get("verdict") in {"correct", "partial", "incorrect", "uncertain"}, "Unknown verdict")
                text(finding.get("rationale"), "Evidence-based finding rationale")
                text(finding.get("next_probe"), "Specific next probe or advancement reason")
            p["observed_help_ids"] = submission["observed_help_ids"]
            event = self.store.append_locked(course, "assessment", p, at=self.clock())
            self._snapshot(course)
            return event

    def _snapshot(self, course):
        state = self.state(course)
        root = self.store.root(course)
        # These are disposable projections. The verified journal is authoritative.
        atomic_json(safe_path(root, "state/current.json"), state)
        checkpoint = state["checkpoint"]
        content = (f"# Resume {state['goal']['title']}\n\n"
            f"Run the shared learn.py resume {course} with --courses pointing to this folder's parent.\n\n"
            f"Goal: {state['goal']['goal']}\n\n"
            f"Next: {self.summary(state)['next_action']}\n\n"
            "Read exact evidence and activity versions before judging understanding. state/current.json is a rebuildable view; "
            "evidence/events is the authoritative history. Sources and all learner records travel with this folder.\n")
        target = safe_path(root, "RESUME.md")
        target.write_text(content, encoding="utf-8")

    def overview(self):
        result, errors = [], []
        if self.store.courses.exists():
            for path in sorted(self.store.courses.iterdir()):
                if path.is_dir() and (path / "course.json").exists():
                    try:
                        state = self.state(path.name)
                        result.append(self.summary(state))
                    except (Invalid, OSError, KeyError, TypeError) as exc:
                        errors.append({"course": path.name, "error": str(exc)})
        return {"courses": result, "errors": errors, "courses_root": str(self.store.courses),
                "at": stamp(self.clock())}

    def summary(self, state):
        pending = state["pending"]
        current = (state["navigation"] or {}).get("activity")
        if not state["navigation"] and state["activities"]:
            current = list(state["activities"])[-1]
        activities = state["activities"]
        activity = activities.get(current)
        if activity:
            activity = {k: v for k, v in activity.items() if k not in {"private_evaluation", "files"}}
        return {"id": state["course"]["id"], "title": state["goal"]["title"], "goal": state["goal"]["goal"],
            "fictional": state["course"]["fictional"], "confirmed": state["goal"].get("confirmed", False),
            "status": state["status"], "progress": state["progress"], "revision": state["revision"],
            "scope_version": state["graph"].get("scope_version", 0),
            "updated_at": state["updated_at"], "due_reviews": [{**r, "concept_title": next((n["title"] for n in state["graph"]["nodes"] if n["id"] == r["concept_id"]), r["concept_id"])} for r in state["reviews"].values() if r["due"]],
            "pending_count": len(pending), "current_activity": activity,
            "next_action": (state["navigation"] or {}).get("next_action") or (state["navigation"] or {}).get("purpose") or "Start with your goal in the agent conversation",
            "plan": state["plan"], "resource_count": len(state["resources"]), "activity_count": len(activities)}

    def resume(self, course):
        state = self.state(course)
        summary = self.summary(state)
        activity = summary["current_activity"]
        if activity:
            activity = state["activities"][activity_key(activity)]
        return {"summary": summary, "goal": state["goal"], "graph": state["graph"],
            "learner": state["learner"], "reviews": state["reviews"], "plan": state["plan"],
            "checkpoint": state["checkpoint"], "pending": state["pending"], "current_activity": activity,
            "current_submissions": [s for s in state["submissions"].values() if activity and s["activity"] == activity_key(activity)],
            "resources": state["resources"],
            "recent_observations": [e for e in self.store.events(course) if e["type"] == "observation"][-12:],
            "course_root": str(self.store.root(course)), "revision": state["revision"],
            "notes": "Retrieve exact evidence with evidence COURSE ID. Chat submission does not automatically wake an agent. "
                     "A provisional graph is not a diagnosis. Progress dimensions overlap; missing evidence is unassessed."}
