# Shared learning-tool contracts

Run from the shared folder containing `learn.py`. Add `--courses PATH` before the
command when course folders live elsewhere. JSON inputs accept a file or `-` for
stdin; use structured writes rather than interpolating learner text into a shell.
`python3 learn.py --help` is the executable command reference.

## Goal and graph

```sh
python3 learn.py new academic-writing --title 'Academic writing' --goal 'Actual learner intent'
python3 learn.py record academic-writing goal goal.json
python3 learn.py record academic-writing resource resource.json
python3 learn.py record academic-writing graph graph.json
```

Goal: `{title, goal, confirmed: boolean, success_criteria: [text],
reported_background: [text], constraints: object}`. A changed agreed goal needs a
`change_reason` supported by actual learner authorization. New goals retain their
original intent in course.json.

Resource: `{id, title, url, why, sections: [text], inspection_notes, limitations}`.
Record what was actually inspected and at what scope. HTTP(S) and local file
references are accepted. Acquisition and inspection are separate operations.

Graph: `{rationale, nodes: [...]}`. Each node has `id`, `title`, `goal_relevance`,
`target_capability`, `requires: [concept-id]`, `prerequisite_rationale: {id: why}`,
`sources: [resource-id]`, `required: boolean`, `provisional: boolean`. IDs contain
lowercase letters, digits, hyphens or underscores. Sources must already be recorded.
Unsourced hypotheses stay provisional. Graph revisions increment `scope_version`;
removing a node from current scope does not erase historical evidence.

## Next purpose and continuity

Plan: `{purpose, concept_ids: [id], why, support, fade_check, activity?: 'id@v001',
evidence_ids?: [event-id]}`. This is an agent decision, not a diagnostic fact.
For evidence-sensitive publication, use `record ... --expected-revision HASH`
with the revision returned by resume; stale publication is rejected.

Observation: `{role: 'user'|'assistant'|'observer', kind:
'conversation'|'prediction'|'execution'|'help'|'learner_feedback', text,
activity?: 'id@v001'}`. Capture actual learner-visible words/actions. Help events
associated with an activity are retained when assessing its submissions.

Checkpoint: `{summary, next_action, activity?: 'id@v001', draft?: text,
open_questions?: [text]}`. `resume COURSE` returns the current goal/graph, plan,
checkpoint, due reviews, recent observations, pending submissions and exact current
activity. `evidence COURSE ID` retrieves raw historical events and artifact bytes.
`state/current.json` and RESUME.md can be regenerated with `rebuild COURSE`.

## Coverage, time and operational repairs

Use `record COURSE coverage FILE` with `{concept_ids: [id], stage:
'introduced'|'practised', reason, evidence_ids: [existing-event-id]}`. This is a
tutor coverage report tied to saved exchanges, not an assessment. `resume` and
the dashboard expose it separately from actual submissions, checked criteria,
independent evidence and scheduled reviews. Add newly taught objectives to the
graph before recording them; do not map unrelated topics to a convenient old ID.

Budget: `{remaining_minutes: nonnegative-integer, deadline: timezone-aware-ISO8601,
priorities: [text], deferred: [text], reason}`. These are explicit planning
estimates, not automatically measured study time. Update after discussing actual
availability and scope; retain permission-blocked labs in deferred work.

Repair: `{id, status: 'open'|'resolved'|'deferred', operation, detail, next_action,
evidence_ids: [existing-event-id]}`. A resolved repair needs evidence IDs supporting
the successful operation. `resume` reports unresolved repairs; inspect them after
access returns. Chat publication I/O failures automatically attempt to save an
open repair with the exact specification and activity ID. Run
`retry-publication COURSE REPAIR_ID` once after fixing access; retries reuse a
committed matching publication if the repair's final save previously failed.
Review changed asset bundles manually before retrying asset publication. If the
journal itself is blocked, no repair record can be promised; preserve recovery
files separately. A warning that publication committed but projection rebuilding
failed means keep the returned identity and run `rebuild`, not publish again.

## One-save conversation capture

`record COURSE session FILE --expected-revision HASH` accepts:

```json
{
  "client_id": "unique-stable-exchange-id",
  "records": [
    {"kind": "observation", "payload": {"role": "assistant", "kind": "conversation", "text": "Exact learner-visible question"}},
    {"kind": "observation", "payload": {"role": "user", "kind": "conversation", "text": "Exact actual answer, unchanged"}},
    {"kind": "checkpoint", "payload": {"summary": "Separate tutor interpretation", "next_action": "Concrete continuation"}}
  ]
}
```

Session records may be observations, checkpoints, schedules, coverage reports,
budgets or repairs. All are validated before one journal event is appended; an
invalid part writes nothing. Graph and referenced evidence must already exist.
Reusing a client ID with identical content returns the original event; changed
content is rejected. After an uncertain save, retry the same input and identity.
Rebuildable projections expose the nested records, retaining the parent event ID
for exact retrieval with `evidence`. This operation never creates a submission or
assessment. Activity-linked help retains its effect on later submissions.

After scheduling (alone or within a session), inspect `resume` for the effective
prompt and date before confirming it to the learner. An existing earlier review
may take precedence over the requested date. A checkpoint is not a queue entry.

## Activities and actual submissions

Read the companion learning-activity skill before publishing. The returned identity
is `ACTIVITY_ID@v001`; old versions remain available after revision.

```sh
python3 learn.py publish COURSE specification.json --artifact ./activity-directory --id paragraph-check
python3 learn.py submit COURSE paragraph-check@v001 --answer-file learner.txt --assistance unknown
python3 learn.py submit COURSE paragraph-check@v001 --answer-file learner.txt --unassisted --artifact answer.docx
python3 learn.py pending COURSE
```

Only submit actual learner work. File artifacts are copied into the immutable
submission event, up to 8 MiB each / 16 MiB total. A stable `--client-id` makes
retries idempotent and rejects changed content under the same retry identity.
Browser drafts are continuity state, never capability evidence.

## Assessment and review

```json
{
  "submission_id": "e_ACTUAL_SAVED_ID",
  "evaluator": "agent",
  "feedback": "Actionable feedback against the displayed task",
  "limitations": "What this particular attempt does not establish",
  "findings": [{
    "criterion_id": "claim-scope",
    "concept_id": "claims",
    "verdict": "correct",
    "rationale": "Specific support in the literal saved response",
    "next_probe": "A targeted next check or reason to advance"
  }]
}
```

Use `assess COURSE FILE`. Cover every announced criterion exactly once. Verdicts:
`correct`, `partial`, `incorrect`, `uncertain`; evaluators: `agent`, `human`, `self`.
Reassessment requires `supersedes: prior-assessment-event-id`. Only the latest answer
to the exact activity version may be assessed. Observed help is carried forward.
Self judgments do not establish independently demonstrated capability.

An assessment-scope correct attempt with explicit empty assistance can support a
narrow independent claim. Diagnostic and guided scope cannot. Transfer additionally
requires a transfer task with an explicit meaningful change. Delayed evidence
requires a delayed task submitted at or after the prior review's due date.
Contradictory subsequent assessed work requires fresh independent evidence.

Schedule: `{concept_ids: [id], due_at: timezone-aware-ISO8601, prompt, reason,
learner_override?: false}`. This can invite first recall after teaching without
claiming success. A schedule cannot silently postpone an existing earlier review.
Intervals are 1/3/7/14/30/60 days. Immediate success preserves an existing due date;
eligible delayed success advances the step; assisted/uncertain/failed checks need
earlier practice. Historical events remain intact. Do not interpret these intervals
as a scientific estimate of a learner's memory or create a mastery badge.

Status: `{status: 'active'|'paused'|'archived', reason}`. Status is learner workflow,
not competency. Development and author QA must not create real learner events.
