# Optional notebook and Jupyter AI workbench

The dashboard and agent tools need only Python. Notebook execution uses an existing
JupyterLab environment selected explicitly; no dashboard launch installs packages.

```sh
python3 learn.py doctor
python3 learn.py serve --jupyter-python /path/to/notebook-environment/bin/python
python3 learn.py notebook COURSE ACTIVITY_ID@v001 --python /path/to/notebook-environment/bin/python
```

If needed, create your own private environment and install JupyterLab/IPython there.
The earlier experiment's pinned runtime requirements remain at
`../../andriod_tab_experiments/harness/template/requirements.txt`; those are its
tested versions, not a claim about current releases. The new launcher does not
modify an explicitly chosen Python environment.

Opening a notebook verifies the original and copies its asset bundle into
`drafts/ACTIVITY_ID-v001/`. Reopening preserves edits. The launched environment
adds the shared harness to PYTHONPATH. Use:

```python
%load_ext harness_core.notebook
```

Then `%%c`, `%%cpp` and `%%sh` run actual bounded local processes. C/C++ need an
installed compiler; each call is a new program and does not retain C/C++ variables
between cells. Python kernel state persists normally. Direct helper use:

```python
from harness_core.notebook import c, cpp, Session
c('#include <stdio.h>\nint main(void){puts("hello");return 0;}')
# Only for an actual learner-requested submission:
session = Session('COURSE', 'ACTIVITY_ID@v001')
# session.submit(actual_answer, assistance=['help actually used'], artifacts=['answer.c'])
```

Execution itself writes no learner assessment. COURSE_AUTHOR_QA=1 rejects explicit
learner writes through these tools. Use temporary fictional courses for author QA.

## Optional AI profile

```sh
python3 learn.py notebook COURSE ACTIVITY_ID@v001 --python /path/to/ai-environment/bin/python --ai
```

Use an environment with Jupyter AI and its ACP dependencies (`jupyter_ai`,
`jupyter_ai_acp_client`, `pycrdt`, `watchfiles`, `cryptography`). The earlier toolkit's
`requirements-ai.txt` pins its tested Jupyter AI version. The new integration reuses
its full Codex persona ID and private `@agentclientprotocol/codex-acp@2.2.2` adapter.
Node and Codex must already be installed; npm is needed for first adapter setup.
The explicit --ai request can install that adapter only in `.runtime/`, never globally.
Normal and AI servers use separate runtime directories. An eligible existing Codex
login supplies model access; credentials never belong in the course folder.

The tutor receives a small course/goal brief and retrieves attached or inspected
material as needed. It defaults to read-only mode and does not automatically write
submissions, assessments or review schedules. Attach relevant cells/readings rather
than assuming it sees every open notebook. Actual model availability, notebook MCP
execution and rendered chat require explicit integration checks on the target host.

Stop only servers started by this harness:

```sh
python3 learn.py stop-notebooks
```

Runtime configuration, tokens and logs are disposable and live outside course
records. Move course folders and select an appropriate environment on the new host.
