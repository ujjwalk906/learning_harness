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

Doctor reports available tools; it does not prove that references can be read or
activities can be published. Read the contracts and run `list` in the actual
learning session. If access fails, preserve literal exchanges separately from
summaries and state what was not saved. After access returns, inspect `resume`
for open repairs and retry the failed operation before declaring setup restored.
Never change machine permissions or agent configuration merely to teach a lesson.

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

Keep the graph aligned with the objectives actually being taught. For a broad
exam or deadline, map the published objectives before reporting overall coverage;
expand detail only as needed. Save `coverage` reports linked to real exchanges.
Use `resume` to distinguish introduced/practised topics, assessed attempts,
independent evidence, due recall, and blocked labs. A coverage report never grants
competence. Do not manufacture a completion percentage from an incomplete graph.

When time is constrained, save a `budget` with the learner's remaining study-time
estimate, deadline, priorities and deferred work. Revisit it at session boundaries,
after a blocked lab or when coverage lags. Compare remaining objectives with time,
offer a concrete tradeoff, and let the learner choose scope, pace or date.

## Choose the next useful purpose

Read the mission, relevant exact evidence, pending submissions, checkpoint and due
reviews. Respect a requested topic or direct explanation. Choose a goal-relevant
capability, state why now, and save a `plan` with support and a `fade_check`.

Distinguish predicting a result or recognizing a pattern, carrying out a procedure,
and explaining how the operation produces its result. Success in one leaves the
others open. Reported familiarity may still need a brief, local refresh; do not
infer a broad prerequisite deficit from difficulty with one example.

Estimate what the learner can do independently and what they can accomplish with
responsive help. Keep these judgments specific and tentative. If unknown, use a
brief probe. Adjust support as well as task difficulty. A targeted hint may reveal
the useful next step; no progress despite help can justify teaching a prerequisite.
Tool failures, ambiguous prompts or language barriers are not concept failures.
Fade support as performance warrants, then check a fresh task with less help.
Do not calculate a global ZPD score or keep someone in repetitive checkpoints.

If a lab is blocked, offer a local fixture, request/response trace, code repair,
policy inspection or architecture decision with a concrete learner output. Name
the skill this checks and what still requires live execution; keep the lab
deferred and visible rather than counting the substitute as cloud execution.

## Teach, then revisit

When useful, invite a short prediction or attempt before the explanation. Make it
low stakes, accept uncertainty, and record it as diagnostic `pretest` evidence.
Failure is permitted, never a required outcome. Supply vocabulary/setup first
when needed for a meaningful prediction. Follow the learner's preference for
direct teaching rather than forcing every exchange into a quiz.

Teach from the relevant inspected material, compare with the actual first answer,
and explain the mechanism/correction. When the learner cannot trace an operation,
start with the smallest meaningful case. Connect its inputs, actions and result
before adding repetition, aggregation or abstraction. When changing representation
(example, diagram, notation, code), explicitly map corresponding parts and explain
changes in orientation, ordering or terminology. Keep the same case while making
that connection so the learner can follow what stays the same.

For guided practice, demonstrate enough to make the next action possible, then
leave a meaningful step for the learner before revealing the rest. This might be
one calculation, a sentence revision or the next step in a process. Respond to the
actual attempt; if the learner goes further successfully, reduce support rather
than making them repeat every small step. A complete worked explanation remains
appropriate when requested; do not make participation a condition of receiving it.

When the learner cannot visualize a mechanism, offer a representation that makes
the relevant relationships visible and connect it to a short learner action.
A static sketch, physical analogy or annotated example may suffice. Use animation
when change or movement clarifies the mechanism, with learner-controlled pacing;
watching it is supported instruction, not evidence of understanding.

If the learner reports increased confusion, narrow the explanation to the unresolved
step and reduce simultaneous concepts or representations. For a broad question
arising from that confusion, give a brief orientation and offer further detail
without introducing a catalogue of related topics. Check whether the smaller
explanation helps before expanding again.

Use a focused self-explanation or a fresh task with less support when useful.
Choose the task to distinguish reconstructing the mechanism from repeating a
shortcut in the worked example. Preserve the help given; immediate supported
success and the learner's report that it makes sense do not establish retention.
Use [learning-activity](../learning-activity/SKILL.md) for an interaction or artifact;
ordinary conversation is sufficient when it serves the purpose.

For a chat-only question that will receive formal assessment, publish its exact
question/criteria with `publish COURSE SPEC.json --chat` before asking it, then
save the actual response using `submit`. No browser visit is needed. An ordinary
explanation can remain a conversation observation without formal assessment.

Read [testing and feedback](references/testing.md) when planning checks, topic
transitions, mixed practice or readiness testing. Use short fresh checks after a
useful topic group, later interleave earlier topics, and offer timed practice when
the goal calls for it. Adapt cadence to the learner; "next" can defer a check
without establishing success. Do not let a long run of explanations silently
replace all testing. Use the published criteria to give precise partial credit.

Build retrieval into continuation: invite reconstruction before reopening notes,
then provide corrective feedback and targeted practice. Interleave related,
previously encountered capabilities when choosing the method is itself useful.
Transfer changes a meaningful constraint, context or representation. New numbers
alone are boundary practice. Physical skills require actual performance evidence.

Use `record COURSE schedule FILE` to save a concrete retrieval prompt and date when justified.
Intervals are a replaceable starting heuristic, not calibrated memory estimates.
When the learner says "review this later", save a specific reconstruction prompt
with `record ... schedule`, then inspect `resume` and confirm the effective date
and prompt. A checkpoint mention alone is not a scheduled review. If saving fails,
say so and leave an open `repair`; retry when access returns. Do not claim a review
is complete or advance its date from a conversational acknowledgment.
Consult due reviews on return, prioritizing relevance and user choice. Immediate
repeats do not establish delayed retention. Do not defer an existing review using
`learner_override` unless the learner actually asked to move it. No external
reminders or automatic agent wakeup are implied by a due date or web submission.

## Interpret actual evidence

Record substantive learner-visible exchanges as literal `observation` events.
For a connected exchange, `record COURSE session FILE` saves ordered observations
and a separate checkpoint in one immutable event with a retry identity. Include
the exact question, actual help and literal answer, retaining spelling and
uncertainty. Summaries belong in checkpoints, never in learner observations.
Read the session contract before using it; do not include hidden reasoning or
shell logs. Batch at a useful boundary rather than issuing several commands for
every short message. Inspect `resume` after saving or recovering a failed save.
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
