# Fieldnotes: an agent-guided learning harness

An evolving learning workspace: the active agent discovers the goal, researches,
teaches, diagnoses and chooses the next purpose. Shared Python tools preserve
course-local records, publish interaction surfaces, capture actual work and supply
a dashboard. There is no requirement to generate a whole course before learning.

## Start

Python 3.11+ on Linux/macOS is sufficient for the tools and dashboard; there are
no required packages, API keys, model jobs or build step. File locking uses POSIX
`fcntl`. Windows is not supported by this first version.

```sh
cd learning_harness
python3 learn.py serve
```

Open **http://127.0.0.1:8780**. The default `courses/` starts empty. Create a journey
there or tell the agent your learning goal. Opening this folder in an agent session
loads AGENTS.md, which points to `skills/learning-guide/SKILL.md`. You can explicitly
ask it to read that file. No global skill installation or configuration is required.

Example learner request (not a command to assess the developer):

> Read skills/learning-guide/SKILL.md. I want to learn English for writing academic
> papers. Help clarify my goal, inspect good material and begin a useful learning
> journey. Build an interaction surface when it helps and keep my work resumable.

The dashboard reads saved state, displays active journeys, due reviews, capability
evidence and pending feedback, and provides continuation prompts. Page loads and
dashboard actions do not invoke a model. The learner returns to the active agent
conversation after submitting; automatic wakeup is not implemented.

Use **Dark mode** in the header to switch themes. The workspace follows your system
theme until you choose one; that choice is saved in your browser and shared across
dashboard, journey and activity pages.

## Tools and records

```sh
python3 learn.py --help
python3 learn.py list
python3 learn.py new writing --title 'Academic writing' --goal 'My actual intent'
python3 learn.py resume writing
python3 learn.py record writing goal goal.json
python3 learn.py record writing graph graph.json
python3 learn.py publish writing activity.json --artifact ./draft-activity --id paragraph-check
python3 learn.py publish writing chat-question.json --chat
python3 learn.py pending writing
python3 learn.py assess writing assessment.json
```

Record shapes and the complete learning workflow live in the
[learning-guide skill](skills/learning-guide/SKILL.md) and its
[tool contracts](skills/learning-guide/references/contracts.md). All commands accept
`--courses /absolute/course-parent` before the command for relocated course folders.
Activities get stable `ID@v001` identities, and revisions retain old versions.

```text
courses/COURSE/
  course.json                 stable identity and original intent
  AGENTS.md + RESUME.md        entry and continuation instructions
  evidence/events/            authoritative hashed event journal
  state/current.json          disposable dashboard/learner-state projection
  activities/ID/v001/          immutable task and surface assets
  drafts/                     editable work, browser drafts, notebook copies
  sources/library/            original local materials
  sources/receipts/            immutable acquisition receipts
  sources/catalog/            source metadata and inspection notes
  research/                   focused research notes as needed
```

Copying the course folder carries its records, source materials, work and history.
Use the shared harness with its new parent via `--courses`; `rebuild COURSE` recreates
projections from verified events. Runtime environments and login credentials are
separate and must be set up on a new machine. The implementation is shared rather
than copied into every course. Do not publish personal course folders accidentally.

## Learning behavior

Skills make goal discovery, research, brief pretesting, source teaching, feedback,
fresh practice, retrieval, transfer and responsive scaffolding explicit. The agent
records why a task is useful now, what support is available and what would justify
less help. It respects direct explanations and user overrides.

Correctness, declared assistance, guided practice, independent evidence, transfer
and delayed retrieval are distinct. Review intervals are a replaceable 1/3/7/14/30/60
day heuristic. No mastery or memory probability is inferred from visits, notebook
runs, copied solutions or fluent chat. Reviews are shown on the dashboard; there
are no external reminders. Scope revisions remain visible and historical evidence
survives graph changes.

## Learning surfaces

HTML, Markdown, notebook v4, text, PDFs, images, audio and video are supported.
Each activity has a persistent response/attachment/assistance panel. Custom HTML
can use the small capture bridge. See [the activity skill](skills/learning-activity/SKILL.md).
The Markdown reader deliberately implements a small escaped subset; the original
is downloadable. Browser drafts and submission retries are handled independently.

Notebooks have a readable browser preview. An optional installed JupyterLab opens
an editable copy and can use C/C++/shell helpers. `--ai` supports a private optional
Jupyter AI/Codex profile using the preserved integration from the earlier harness.
See [notebook and AI setup](docs/jupyter-ai.md). No optional dependencies are
installed by starting the dashboard.

## Fictional demonstration and checks

```sh
python3 learn.py demo --output /tmp/fieldnotes-demo
python3 learn.py --courses /tmp/fieldnotes-demo/courses serve --port 8781
python3 -m unittest discover -s tests -v
node --check web/app.js
node --check web/activity.js
node --check web/bridge.js
```

The demonstration refuses a nonempty destination, labels every course fictional,
and never writes into the default learner directory. It demonstrates mechanics,
not research quality or real learner progress. Tests use temporary fictional state.

See [architecture and boundaries](docs/architecture.md) and
[verification](docs/VALIDATION.md). Earlier experiments are preserved.
