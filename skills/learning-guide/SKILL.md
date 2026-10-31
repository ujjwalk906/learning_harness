---
name: learning-guide
description: Guide a persistent personal learning journey through the current agent conversation, using course-local goals, research, activities, evidence and reviews. Use for learning, continuation and recall; not harness development or inferring the developer's knowledge.
---

# Guide a learning journey

The current agent teaches; `learn.py` preserves records and projects the dashboard.
A complete syllabus, entrance exam, dashboard or second model runner is not needed
to begin. Let the learner's goal and actual work guide the next useful step.

## Enter or resume

Find `learn.py` beside this installed `SKILL.md`, or at the repository root in a
source checkout. Use its absolute path. If the runtime is missing, follow
`INSTALL.md`; instructions alone are not a complete installation.

On first use, read [tool contracts](references/contracts.md), run `doctor` and
`list`, and verify reference access and the intended course directory. Doctor
reports tools, not publication permissions. Installed defaults are
`~/Fieldnotes/courses`; checkout defaults are its `courses/`. `FIELDNOTES_HOME`
changes the installed data parent; `--courses PATH` selects a course parent.
Handle commands for the learner. In temporary environments, explain storage limits
and help preserve course folders. Never imply an installation on another machine.

Run `resume COURSE` before continuing; inspect pending work, due reviews, the
checkpoint and relevant exact evidence. `evidence COURSE ID` retrieves originals;
summaries do not replace disputed words or task bytes. Ask which journey only if
ambiguous. For a new goal, use `new`, clarify success and constraints just enough
to start, then record the agreed goal. Label reported background as reported.

If access fails, preserve literal exchanges separately from summaries and report
what was not saved. After access returns, inspect repairs and retry before claiming
recovery. Do not change machine permissions merely to teach. Use a dashboard only
when useful: start `serve`, verify the returned link is reachable, and explain that
submission saves work but does not wake an agent. Chat activities work without it.

## Plan at two scales

Use [learning-research](../learning-research/SKILL.md) to inspect suitable material.
For a broad goal, keep a coarse objective map; develop only the next connected
unit in detail. For an exam, map published objectives before reporting overall
coverage. Define observable capabilities and justify prerequisite edges by what
they enable; unrelated topics must not share a convenient concept ID.

Choose a unit using the learner's goal, requested topic, relevant evidence and due
reviews. Save a `plan` with why it is useful now, available support and a specific
`fade_check`; revise when direction changes, not for every short exchange.
At unit/session boundaries, reconcile evidence-linked `coverage` with what was
taught. Keep introduced/practised material, assessed ability, delayed evidence and
deferred work distinct. Missing coverage records do not mean a topic was untaught.

For a deadline, save a `budget` based on reported availability, priorities and
deferred work. Revisit estimates at boundaries or after a blocker; reserve time
for checks and repair. Offer scope/time tradeoffs for the learner to choose.
Do not turn an incomplete map or reading completion into a readiness percentage.

## Teach, practise, check, respond

For the chosen capability, identify the foundation needed, choose the appropriate
mode, then use the actual response to advance, repair a specific gap or defer it.
These are tutor decisions, not a script to recite or a quiz after every message.

| Mode | Teaching decision |
| --- | --- |
| Explanation | Trace one meaningful case from inputs through actions to result. Keep the case while mapping diagrams, words or code; define unfamiliar terms where they enter. |
| Guided practice | Demonstrate enough to enable a meaningful learner step, then respond to that attempt. Reduce support when warranted. |
| Check | Remove answer cues and change a relevant condition so the learner must select, explain or perform, rather than echo the example. |

A brief diagnostic prediction can help choose support; supply needed vocabulary
first and welcome uncertainty. Respect requests for a full explanation without
making an attempt a condition of receiving it. When relationships are hard to
visualize, use a sketch, analogy or paced animation with a useful learner action.
Watching a demonstration is instruction, not demonstrated ability.

Distinguish a misunderstood step from a missing framework. For the former, isolate
that step; for the latter, trace a small complete process connecting the needed
parts before returning to the difficulty. Do not infer a broad deficit from one
answer or mistake a tool failure or ambiguous prompt for a concept failure.
Example: "I know the terms but can't connect them" calls for a connected process,
not another list of definitions or another isolated either/or question.

Interpret success at the level actually shown. A correct label copied from the
question is supported recognition; acknowledging "got it" permits continuation but
does not establish understanding. Use a discriminating follow-up when needed.
Example: "Correct selection; the reason is still unclear" is more precise than
claiming the mechanism is understood. Grade only announced criteria; an optional
explanation cannot become a new requirement after the answer.

At a connected unit's boundary, offer a short check before expanding; later mix
in earlier material. After a long explanation sequence, choose consolidation
rather than automatically adding another topic. Respect an explicit request to
move on, retaining the unresolved check; revisit it at a useful boundary, and
surface the tradeoff if deferrals accumulate. Do not repeatedly interrupt with
quizzes or make progress conditional on testing.
Example: "We'll continue; that distinction stays open for a later mixed check."

Read [testing and feedback](references/testing.md) when authoring a check or
judging readiness. Use [learning-activity](../learning-activity/SKILL.md) to publish
formal tasks and capture work; ordinary explanations can remain observations.
If a lab is blocked, offer a concrete local trace, code/policy repair or other
appropriate task. Record what it checks and what still needs live performance.

## Preserve evidence and continuation

At useful boundaries, save substantive literal exchanges and a separate checkpoint
using `record COURSE session FILE`, or individual records from the contracts.
Keep the exact question, actual help and learner response, including uncertainty;
put interpretations in checkpoints, not learner quotations. Keep hidden reasoning,
tool chatter and fabricated work out. Inspect `resume` after a save or recovery.
Never edit published activities or journal events; use new versions and explicit
superseding assessments. Unfinished learner work stays intact.

For formal assessment, publish the question and criteria before asking, submit
the actual answer to that version, and assess against its criteria. Preserve shown
help. When independent evidence matters, ask explicitly about notes or assistance;
if unanswered, retain `unknown`. A declaration cannot erase observed help.
Correctness, supported performance, independence, transfer and delayed retention
are distinct; claim only what the saved task and response support. Do not infer a
global ability score, mastery or memory probability from limited evidence.

When asked to review later, save a specific reconstruction prompt with `schedule`
and verify its effective date/prompt in `resume` before confirming. At continuation,
invite due recall before reopening notes where appropriate. Respect learner
choices without silently moving due dates or marking acknowledgment as retrieval.
A checkpoint mention alone is not scheduling; on save failure, report it and retain
a repair where possible. Review intervals are heuristics, not external reminders.
