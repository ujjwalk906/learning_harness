---
name: learning-activity
description: Create or revise a focused learning activity in HTML, Jupyter, Markdown or another supported surface, with exact task identity, captured work and a return to the teaching conversation. Use when an interaction or artifact serves a learning purpose.
---

# Build the workbench the learning purpose needs

Read the current goal, plan and relevant exact evidence with shared `learn.py`.
Choose a surface for the learner's action: manipulate a simulation, annotate text,
write or speak, construct an explanation, execute code or inspect an experiment.
Conversation itself can be enough. Do not force nonprogramming learning into code.

Author only the next useful activity or a bounded connected group. Supply the
actual case, starting files/data, clear instructions, announced criteria and a
working place to respond. Teach the prerequisites needed to perform the task;
an optional low-stakes pretest may precede teaching. Label supplied orchestration
and environment boundaries. A model is not execution of the modeled mechanism.

Create activity files under the course's drafts/ or a temporary authoring folder,
then publish a snapshot using `learn.py publish COURSE SPEC.json --artifact PATH`.
PATH is a single file or a directory containing the declared entrypoint. Reusing
`--id ACTIVITY_ID` creates v002 and retains v001 and its work. Do not edit published
bytes. Keep solutions/private evaluation outside the served asset directory.

For chat-only tasks, omit entrypoint and use `publish COURSE SPEC.json --chat`.
It saves the exact question and announced criteria without creating a separate
interaction. Ask that question in the conversation and record the real response.

Specification:

```json
{
  "title": "Choose a defensible claim",
  "instruction": "Revise the supplied claim and explain one change.",
  "why": "Targets the observed difficulty connecting claims to evidence",
  "concept_ids": ["claims"],
  "purpose": "check",
  "phase": "after_instruction",
  "evidence_scope": "assessment",
  "review_prompt": "Reconstruct the claim/evidence distinction before reopening the reference.",
  "criteria": [{"id": "claim-scope", "concept_id": "claims", "description": "Match the strength of the claim to the supplied evidence"}],
  "entrypoint": "index.html"
}
```

Purposes: pretest, practice, check, retrieval, transfer, exploration. Phases:
before_instruction, after_instruction, delayed. Scopes: diagnostic, guided,
assessment. A pretest is before_instruction/diagnostic. Transfer needs `change`
describing a meaningful changed decision. Only actual later work can establish
delayed evidence. `private_evaluation` is optional and omitted from browser data.

HTML, Markdown, notebook v4, text, PDF, images, audio and video entrypoints are
supported. Assets are snapshotted and hash-checked; relative CSS/JS/media can live
beside the entrypoint. The host provides a persistent answer/attachment/assistance
panel for every surface. Do not expose the answer before an intended independent
attempt, imply that a visited page was understood, or submit on load/Run All.

HTML runs in an opaque sandbox. For custom controls use the injected bridge:

```javascript
LearningHarness.draft({answer: literalResponse, state: {selected: optionId}});
LearningHarness.help('Actually displayed this hint: ...');
LearningHarness.submit({answer: literalResponse});
window.addEventListener('learning-harness-restore', event => {
  // Restore your controls from event.detail.state; this is continuity, not evidence.
});
```

The host checks the sender, records help, saves version-specific drafts and handles
retry identities. Generated scripts cannot declare independence for the learner;
the host's assistance controls remain authoritative. Supply useful corrective
feedback for guided practice; the active agent makes the later assessment.

Notebook files have a browser preview and an editable Jupyter copy. `learn.py
notebook COURSE ID@v001 --python PYTHON` opens an installed environment; `--ai`
adds the optional existing Jupyter AI/Codex profile. Read docs/jupyter-ai.md before
using it. `%load_ext harness_core.notebook` provides real C/C++/shell cell magics;
the runtime uses a Python kernel with temporary compiled subprocesses. Other
kernels/environments need their own setup. Keep published notebooks unchanged.
Use `harness_core.notebook.Session` only for explicit submissions with exact IDs.

Start `learn.py serve` and check the returned local workspace before giving activity
links. Give the purpose, clickable returned URL path under that server, and ask the
learner to return to the conversation. Submitting saves evidence; it does not wake
an agent. On return, use pending/resume and inspect exact saved work. Test author
artifacts in temporary fictional folders; never generate learner evidence for QA.
