# Tests, feedback and readiness

Use this reference for checks and readiness decisions. The active agent authors
and interprets the tasks; the tools preserve their identity, actual work and help.

## Choose evidence to match the question

| Purpose | Task design | What it can establish |
| --- | --- | --- |
| Diagnostic | Brief prediction before teaching; uncertainty welcome | Starting point for support |
| Guided practice | Leave a meaningful step after a worked example | Performance with that help |
| Topic check | Fresh case, no answer-bearing example beside it | Application on the announced criteria |
| Mixed check | Interleave earlier topics without naming the method | Choosing and applying a method |
| Delayed retrieval | Reconstruct after the saved due date, before notes | Later performance with declared assistance |
| Timed practice | Representative scope, explicit time allowance | Performance under that recorded constraint |

Select a cadence that fits the goal and learner. After a connected topic group,
offer a small check before extending the explanation. At later session boundaries,
include earlier topics. For deadline or exam goals, reserve time for mixed and
timed practice instead of spending the whole budget on new material. A requested
explanation or "move on" can defer a check; retain the unresolved check in the
checkpoint or budget. Do not enforce a fixed number of questions per topic.

## Publish before asking

Use the activity workflow and `publish --chat` for conversation tests. Specify
the complete scenario, assumptions, question and observable criteria before the
attempt. Store expected answers and distractor explanations in `private_evaluation`,
outside public assets. For a set of questions, announce criteria per item and
target each relevant concept. Mixed practice can use several concept IDs; timed
practice should state the allowance in its instruction. Record actual timing only
when observed or explicitly reported, with its provenance.

Change the decision needed, not just names and numbers. Avoid putting the target
term in the question or reproducing the worked example. When useful, ask for a
choice and a reason, a rejected alternative, or the smallest change that would
make another answer correct. Follow the goal: a code-reading exercise is useful
for debugging, but cannot establish blank-file implementation ability.

Publish success must return an activity identity before the task is presented as
a formal test. On an I/O failure, `resume` exposes a saved repair when the journal
remains writable. `retry-publication COURSE REPAIR_ID` retries its exact chat
specification once after access is restored. Inspect the saved question, then ask
for a fresh attempt. Do not backfill an earlier conversational response as an
independent answer to a newly published task. If even the repair cannot be saved,
preserve the specification and exchange as recovery files and report that gap.

## Capture and judge the actual attempt

Save the literal answer using `submit`, naming the exact version and assistance.
Use `--assistance unknown` unless the learner explicitly declared independence.
Record displayed hints as activity-linked `help` observations; a later empty
assistance declaration does not erase them. Tests with provided support remain
useful, but do not count them as independent performance.

Grade against the announced criteria. Separate a correct choice, a sound reason,
and a demonstrated implementation when the task asks for each. For partial or
ambiguous wording, identify exactly what is established and what remains unclear.
Use one discriminating counterexample or follow-up rather than automatically
repeating a whole lesson. Do not require vocabulary precision unless the task
requires it, or call an ambiguity fully correct and then contradict that praise.

Give feedback after the intended attempt, explain mistakes and distractors, and
offer focused repair followed by a fresh check. Reusing a disclosed answer is
practice. Neither an immediate correct response nor a self-report of understanding
establishes delayed retention.

## Report readiness with limits

Use current objective coverage, saved findings across unfamiliar mixed cases,
delayed evidence, timing where relevant, and deferred practical work. Show gaps
and propose how to spend remaining time. Do not infer an exam score, calibrated
pass probability or mastery percentage from a small tutor-authored test. Clearly
distinguish official practice results, learner-reported results and local checks.
