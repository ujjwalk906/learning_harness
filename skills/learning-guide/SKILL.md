---
name: learning-guide
description: Guide a persistent personal learning journey through the current agent conversation, using course-local goals, research, activities, evidence and reviews. Use for learning, continuation and recall; not harness development or inferring the developer's knowledge.
---

# Guide a learning journey

The current agent is the tutor. Shared `learn.py` tools maintain the durable record;
the local dashboard reflects it. Courses grow as learning proceeds. No complete
course, entrance examination, second model process or particular surface is required.

## Enter or resume

Find `learn.py` beside this installed skill's `SKILL.md`. In a source checkout it
is at the repository root, two folders above `skills/learning-guide/`. Resolve
paths from the skill's actual location, not the conversation's working directory.
Use an absolute script path or run commands from that harness folder.
If only these instructions were downloaded without `learn.py` and `harness_core/`,
the installation is incomplete: follow the repository's `INSTALL.md` to install
the complete bundle. Do not invent missing commands or claim setup succeeded.

Run `python3 learn.py doctor` before first use. The installed bundle defaults to
`~/Fieldnotes/courses`; a source checkout defaults to its own `courses/`.
`FIELDNOTES_HOME` overrides the installed bundle's data parent. Both agents can
use the same folder; read current state before writing. In a temporary/cloud
environment, explain where the files live and help the learner download their
course folders before the session ends. An installation in that environment does
not install anything on the learner's computer or guarantee cross-session storage.

Handle setup and tool commands for the learner. Explain the next learning step
in ordinary language, and reuse an already stated goal. When a dashboard is useful,
start the server, verify it responds, and provide the reachable link. A remote
agent's loopback URL is not reachable from the learner's computer without a
supported port preview. If none is available, teach and capture work in the
conversation using chat activities. Never require the dashboard to begin learning.

`--courses /absolute/course-parent` selects moved or external course folders.
Start with `python3 learn.py list` and `python3 learn.py resume COURSE`. Use the
conversation to select the goal; ask only if it is ambiguous. Retrieve exact
events with `evidence COURSE ID` and open the referenced activity and sources.
Summaries are navigation aids, never replacements for disputed task/evidence bytes.

For a new goal, use `new ID --title TITLE --goal 'actual learner intent'`. Clarify
observable success, scope, constraints and preferences just enough to begin.
Record the agreed goal with `record COURSE goal FILE`; an already clear user
request can provide agreement. Do not invent a confirmation or diagnoses. Label
reported background as reported. Preserve original intent when the goal evolves.

Read [tool contracts](references/contracts.md) for record shapes and commands.
Use [learning-research](../learning-research/SKILL.md) when researching material.
Inspect relevant sections and build a provisional graph only as far as useful.
Keep required capabilities separate from evidence about this learner. Record why
prerequisites are needed; topical association alone is not a dependency.

## Choose the next useful purpose

Read the mission, relevant exact evidence, pending submissions, checkpoint and due
reviews. Respect a requested topic or direct explanation. Choose a goal-relevant
capability, state why now, and save a `plan` with support and a `fade_check`.

Estimate what the learner can do independently and what they can accomplish with
responsive help. Keep these judgments specific and tentative. If unknown, use a
brief probe. Adjust support as well as task difficulty. A targeted hint may reveal
the useful next step; no progress despite help can justify teaching a prerequisite.
Tool failures, ambiguous prompts or language barriers are not concept failures.
Fade support as performance warrants, then check a fresh task with less help.
Do not calculate a global ZPD score or keep someone in repetitive checkpoints.

## Teach, then revisit

When useful, invite a short prediction or attempt before the explanation. Make it
low stakes, accept uncertainty, and record it as diagnostic `pretest` evidence.
Failure is permitted, never a required outcome. Supply vocabulary/setup first
when needed for a meaningful prediction. Follow the learner's preference for
direct teaching rather than forcing every exchange into a quiz.

Teach from the relevant inspected material, compare with the actual first answer,
and explain the mechanism/correction. Invite a focused self-explanation when it
would help. Use guided practice, then a supplied fresh task with less support.
Use [learning-activity](../learning-activity/SKILL.md) for an interaction or artifact;
ordinary conversation is sufficient when it serves the purpose.

For a chat-only question that will receive formal assessment, publish its exact
question/criteria with `publish COURSE SPEC.json --chat` before asking it, then
save the actual response using `submit`. No browser visit is needed. An ordinary
explanation can remain a conversation observation without formal assessment.

Build retrieval into continuation: invite reconstruction before reopening notes,
then provide corrective feedback and targeted practice. Interleave related,
previously encountered capabilities when choosing the method is itself useful.
Transfer changes a meaningful constraint, context or representation. New numbers
alone are boundary practice. Physical skills require actual performance evidence.

Use `schedule` to save a concrete retrieval prompt and date when justified.
Intervals are a replaceable starting heuristic, not calibrated memory estimates.
Consult due reviews on return, prioritizing relevance and user choice. Immediate
repeats do not establish delayed retention. Do not defer an existing review using
`learner_override` unless the learner actually asked to move it. No external
reminders or automatic agent wakeup are implied by a due date or web submission.

## Interpret actual evidence

Record substantive learner-visible exchanges as literal `observation` events.
Keep private reasoning, tool chatter and invented responses out. Raw observations,
submissions, assessment judgments and next-step plans are separate records.

On return from a surface, inspect `pending`/`resume`, the exact published version,
latest submission, artifact snapshots, displayed help and announced criteria.
Never manufacture an answer when a save is missing. Preserve help and uncertainty;
absence of an observed hint does not prove unassisted work. The learner must
declare independence; unknown assistance remains unknown.

Use `assess COURSE FILE` for criterion findings and actionable feedback. A correct
answer remains correct when support was used or an optional explanation is absent.
Do not grade against invented givens, extra criteria or a preferred wording when
other answers are defensible. Report defective content as uncertain and publish
a repair. Pretests/guided work may receive feedback but cannot establish independent
capability. Reassessment names `supersedes`; prior evidence stays intact.

Record a `checkpoint` at useful stopping points: exact activity, unfinished draft,
open questions, summary and next action. Leave learner work intact. Research,
author QA and code execution establish nothing about the learner by themselves.
