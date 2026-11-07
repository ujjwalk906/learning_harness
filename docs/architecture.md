# Architecture and continuation

`learn.py` enters `harness_core/cli.py`. The active agent supplies intelligence;
skills route it through goal discovery, source inspection, task/support selection,
surface creation, evidence interpretation and continuity. No background LLM is
started by the CLI, dashboard, submission or review queue.

`store.py` owns course identity, atomic writes, per-course advisory locks and a
sequence/hash-linked append-only event journal. `engine.py` validates operations
and derives the current view. Raw submissions embed file snapshots. Assessments
reference actual latest submissions and announced criterion IDs. Superseding a
judgment changes effective interpretation without adding a retrieval attempt.

An optional `session` event atomically stores a bounded ordered group of literal
observations and separate continuity records. Projection replay unpacks those
records with their parent event identity; the hashed journal entry remains the
authoritative source. Stable client IDs make uncertain-save retries idempotent.
This creates neither a submission nor an assessment. Coverage reports describe
teaching exposure and link to existing evidence; assessed capability still derives
only from actual activity submissions and separate criterion judgments. Study
budgets are explicit estimates with priorities and deferred work, not time tracking.

Publication I/O failures attempt to append an operational repair. Saved chat
specifications can be retried explicitly after access is restored; successful
publication is reused if saving its repair resolution fails. Asset retries require
manual inspection because source bytes can change. If the journal is unwritable,
the caller must preserve recovery files; there is no claim of a durable repair.
Projection-write failures after publication return the committed identity with a
rebuild warning. They do not authorize a second publication or a retroactive test.

The current state is derived afresh for dashboard reads. `state/current.json` and
RESUME.md are convenience snapshots that `rebuild` can recreate. The dashboard
does not guess progress from Markdown or file counts. It counts current required
graph capabilities with supported evidence. Practice, independent, transfer and
delayed dimensions overlap; missing judgments remain unassessed. Provisional graph
revisions and requirements are distinct from the learner's current understanding.

`activities.py` snapshots activity files and checks their hashes on retrieval.
Publication is versioned; old links and submissions retain their task identity.
Supported entrypoints are HTML, Markdown, notebooks, text, PDFs, images and media.
Private evaluation is excluded from browser activity data. The agent must keep
solution files out of the public activity bundle.

`server.py` binds to loopback, checks Host, protects writes with a per-server token
and origin checks, and isolates generated HTML with a sandbox and CSP. Only the
known frame may send bridge messages. The trusted host supplies course/activity
identity. Generated scripts cannot declare the learner independent; observed help
is retained separately. Activity scripts have no direct API mutation access.
These are local single-user boundaries, not multi-user authorization or protection
against a process with the user's filesystem permissions.

The browser's raw response panel works across surfaces. Drafts restore by exact
activity version and use revision checks to detect another tab's edits. Submission
retry IDs reject changed content and preserve one event for a repeated request.
File attachments are immutable snapshots, up to 8 MiB each and 16 MiB total.

`workbench.py` launches optional existing Jupyter environments and opens editable
copies under course drafts, preserving the published task. `notebook.py` provides
real temporary C/C++ compiled processes, shell execution and explicit Session
submission/observation tools. No execution automatically becomes an assessment.
Notebook AI uses the earlier toolkit's adapted MIT-licensed tutor configuration;
the active learning agent still handles formal evidence interpretation.

`sources.py` is reused from the earlier source-first toolkit under its MIT license.
It preserves acquisition receipts, selected originals and licenses and detects
edits/additions/deletions. Resource inspection is a separate agent record. Schema
and integrity checks cannot establish source quality or instructional truth.

Course folders are self-contained data, not self-contained executable installations.
They require a compatible shared harness (version recorded in course.json), and
optional runtime dependencies are separately installed. The current version uses
native Windows or POSIX advisory locking. Explicit migration will be needed if future schemas change.

`install.py` builds a single self-contained learning-guide skill from an explicit
allowlist. It includes the shared Python runtime, web assets, tool contracts and
companion workflows as references. Packaged `learn.py` uses
`scripts/installed_learn.py`, keeping course data in `~/Fieldnotes/courses` (or a
selected external data folder) instead of replaceable skill/plugin code. Source
checkout defaults remain unchanged. Both local agent installs and the portable
ZIP use this payload. The ChatGPT desktop target wraps it in a portable plugin
and merges a personal marketplace entry; enabling the plugin remains an app action.
No installation step creates learner evidence or starts a model. Updates preflight
ownership and data separation, smoke-check staged code, then replace installed code.
Windows staging folders inherit normal parent access instead of using mkdtemp's
owner-only ACL, so installed and published files remain readable to the sandbox.

Author checks, fictional demonstrations and harness development do not authorize
assessment of the developer. Keep QA state in temporary directories, and use
COURSE_AUTHOR_QA=1 for execution checks that must reject learner writes. No actual
learning effectiveness, calibrated memory model or universal ZPD score is claimed.
