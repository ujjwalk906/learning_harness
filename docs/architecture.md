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
POSIX locking. Explicit migration will be needed if future schemas change.

Author checks, fictional demonstrations and harness development do not authorize
assessment of the developer. Keep QA state in temporary directories, and use
COURSE_AUTHOR_QA=1 for execution checks that must reject learner writes. No actual
learning effectiveness, calibrated memory model or universal ZPD score is claimed.
