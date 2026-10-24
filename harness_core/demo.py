"""Explicit fictional data for UI and workflow checks; never the learner's history."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path

from .activities import publish
from .engine import Harness, require
from .store import now, stamp


DEMO_HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>
body{font:16px/1.8 system-ui;color:#294536;background:#fffdf8;padding:36px;max-width:760px;margin:auto}h1{font:36px/1.2 Georgia,serif}button{font:inherit;background:#edf2e5;border:1px solid #cfddc3;color:#385d38;padding:14px 18px;border-radius:8px;text-align:left;cursor:pointer;margin:8px 0;width:100%}button.selected{background:#dbe9cf;border-color:#749768}small{color:#8b937c}textarea{width:100%;min-height:100px;font:inherit;padding:12px;border:1px solid #d6dfca;border-radius:6px;box-sizing:border-box}#hint{background:#f6f0e1;padding:16px;border-radius:8px}#save{background:#264a35;color:white;text-align:center}</style></head><body>
<small>FICTIONAL TOOLING DEMONSTRATION · NO REAL LEARNER CLAIMS</small><h1>What does the evidence let us say?</h1><p>This miniature exercises prediction, help capture, saved state and return to conversation. It is not a researched lesson.</p><p>In a fictional comparison, one small sample improved after a change. Which statement preserves the uncertainty?</p><button class="choice" data-value="A">A. The change always produces improvement.</button><button class="choice" data-value="B">B. The sample improved; more evidence is needed to generalize.</button><label for="reason">Explain your prediction</label><textarea id="reason" placeholder="What made you choose that statement?"></textarea><button id="show-hint">Show a hint</button><p id="hint" hidden>Separate the observation in this sample from a claim about every possible case.</p><button id="save">Save my response & return to conversation ↗</button><script>
let choice='';const reason=document.querySelector('#reason');function draft(){LearningHarness.draft({answer:choice+' '+reason.value,state:{choice,reason:reason.value}});}document.querySelectorAll('.choice').forEach(b=>b.onclick=()=>{choice=b.dataset.value;document.querySelectorAll('.choice').forEach(x=>x.classList.toggle('selected',x===b));draft();});reason.oninput=draft;document.querySelector('#show-hint').onclick=()=>{document.querySelector('#hint').hidden=false;LearningHarness.help('Displayed the hint distinguishing sample observation from generalization.');};document.querySelector('#save').onclick=()=>{if(!choice||!reason.value.trim()){reason.focus();return;}LearningHarness.submit({answer:choice+': '+reason.value});};window.addEventListener('learning-harness-restore',e=>{choice=e.detail.state?.choice||'';reason.value=e.detail.state?.reason||'';document.querySelectorAll('.choice').forEach(b=>b.classList.toggle('selected',b.dataset.value===choice));});
</script></body></html>'''


def make_demo(output):
    output = Path(output).expanduser().resolve()
    require(not output.exists() or not any(output.iterdir()), "Demo output must be a new or empty directory")
    courses = output / "courses"
    start = now() - timedelta(days=9)
    current = [start]
    harness = Harness(courses, clock=lambda: current[0])
    fixtures = output / "fictional-material"
    fixtures.mkdir(parents=True)
    (fixtures / "index.html").write_text(DEMO_HTML, encoding="utf-8")
    (fixtures / "check.md").write_text("# Fictional independent check\n\nState what a small observation permits us to conclude. Explain one limit.\n\nThis is a tooling fixture, not actual teaching or real learner evidence.\n", encoding="utf-8")
    names = [
        ("academic-writing", "English for academic writing", "Write clear, well-supported academic arguments in my own research.", ["claims", "paragraphs", "revision"]),
        ("physics", "Physics: motion & models", "Connect physical models, predictions and observations.", ["forces", "models", "prediction"]),
        ("cpp", "C++: lifetime & ownership", "Explain object lifetime and investigate unfamiliar ownership bugs.", ["lifetime", "ownership", "debugging"]),
    ]
    for index, (cid, title, goal, concepts) in enumerate(names):
        harness.create(cid, title, goal, fictional=True)
        harness.record(cid, "goal", {"title": title, "goal": goal, "confirmed": True,
            "success_criteria": ["FICTIONAL fixture: use evidence and explain limits"], "reported_background": [], "constraints": {"fictional": True}})
        harness.record(cid, "resource", {"id": "fixture", "title": "Fictional author QA material", "url": (fixtures / "check.md").as_uri(),
            "why": "Demonstrate records without claiming real source research", "sections": ["Fictional independent check"],
            "inspection_notes": "This is explicitly invented demonstration material, not a subject teaching source.", "limitations": "Fictional workflow check only."})
        harness.record(cid, "graph", {"rationale": "Fictional provisional capability map for demonstrating the dashboard.",
            "nodes": [{"id": concept, "title": concept.title(), "goal_relevance": goal,
                "target_capability": "Explain a mechanism and its evidence limitations", "requires": [], "sources": ["fixture"],
                "provisional": True, "required": True} for concept in concepts]})
        specification = {"title": "A fresh look at the evidence", "instruction": "Make a prediction, explain your reasoning and save your work.",
            "why": "Fictional fixture connecting the learner's current work to a focused capability.", "concept_ids": [concepts[0]],
            "purpose": "check", "phase": "after_instruction", "evidence_scope": "assessment",
            "review_prompt": "Without reopening the example, explain the difference between an observation and a general claim.",
            "criteria": [{"id": "reasoning", "concept_id": concepts[0], "description": "Explain what the observation supports and one limitation."}],
            "private_evaluation": "Fictional author criterion; not delivered to the activity frame."}
        first = publish(harness, cid, specification, fixtures / "check.md", activity_id="evidence-check")
        submission = harness.submit(cid, first["activity"], "FICTIONAL answer: the observation is limited to the sample.", [], client_id="fixture-initial")
        harness.assess(cid, {"submission_id": submission["id"], "evaluator": "agent", "feedback": "FICTIONAL: the stated limitation addresses this task.",
            "limitations": "Fictional QA; establishes nothing about the real learner.", "findings": [{"criterion_id": "reasoning", "concept_id": concepts[0],
            "verdict": "correct", "rationale": "Fictional supplied answer includes the scope limitation.", "next_probe": "Reconstruct after a genuine delay."}]})
        current[0] = now() - timedelta(hours=3-index)
        guided = {**specification, "title": ["Make your claim match your evidence", "A prediction worth investigating", "Trace what changes and what stays alive"][index],
            "purpose": "practice", "evidence_scope": "guided"}
        activity = publish(harness, cid, guided, fixtures / "index.html", activity_id="next-step")
        harness.record(cid, "plan", {"purpose": "Distinguish what the observation supports", "concept_ids": [concepts[0]],
            "why": "Fictional evidence suggests a useful next step; the map remains provisional.",
            "support": "A targeted hint is available. Record it if used.", "fade_check": "Explain a different example without the hint.", "activity": activity["activity"]})
        harness.record(cid, "checkpoint", {"summary": "FICTIONAL checkpoint for demonstrating fresh-session continuity.",
            "next_action": "Try the current activity, then return to the agent conversation.", "activity": activity["activity"]})
        if index == 0:
            harness.submit(cid, activity["activity"], "FICTIONAL pending response for the feedback queue.", ["unknown"], client_id="fixture-pending")
        current[0] = start
    return {"courses": str(courses), "fictional": True,
            "preview_command": f"python3 learn.py --courses {courses} serve", "note": "No real learner evidence was created."}
