"""Optional existing Jupyter environment; no automatic package installation."""
from __future__ import annotations

import importlib.util
import fcntl
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler, Request

from .store import Invalid, atomic_json, read_json, safe_path
from .engine import require


def alive(info):
    try:
        req = Request(info["base_url"] + "/api/status", headers={"Authorization": "token " + info["token"]})
        with build_opener(ProxyHandler({})).open(req, timeout=1) as response:
            return response.status == 200
    except (OSError, KeyError, ValueError):
        return False


def open_notebook(harness, course, activity, runtime, *, python=None, ai=False):
    directory = Path(runtime) / harness.store.config(course)["instance_id"] / ("ai" if ai else "standard")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    with (directory / "launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _open_notebook(harness, course, activity, runtime, python=python, ai=ai)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _open_notebook(harness, course, activity, runtime, *, python=None, ai=False):
    # A venv's python is usually a symlink. Resolving it loses that environment.
    python = str(Path(python).expanduser().absolute()) if python else sys.executable
    record = harness.state(course)["activities"].get(activity)
    require(record is not None and record["surface"] == "notebook", "Select a notebook activity")
    # Verify original notebook bytes before handing it to an editable workbench.
    from .activities import read_asset
    read_asset(harness, course, activity, record["entrypoint"])
    profile = "ai" if ai else "standard"
    directory = Path(runtime) / harness.store.config(course)["instance_id"] / profile
    directory.mkdir(parents=True, exist_ok=True)
    info_path = directory / "jupyter.json"
    info = read_json(info_path) if info_path.exists() else None
    if not info or not alive(info):
        probe = subprocess.run([python, "-c", "import jupyterlab"], capture_output=True, timeout=15)
        require(probe.returncode == 0, "JupyterLab is not installed in the selected Python. Install it yourself or select an existing environment with --jupyter-python.")
        env = dict(os.environ)
        if ai:
            from .tutor import REQUIRED_MODULES, ensure_adapter, environment, prerequisites
            prerequisites(directory)
            probe = subprocess.run([python, "-c", ";".join("import " + module for module in REQUIRED_MODULES)],
                                   capture_output=True, timeout=20)
            require(probe.returncode == 0, "Selected Python needs Jupyter AI and its ACP dependencies. See docs/jupyter-ai.md; no Python environment was modified.")
            ensure_adapter(directory)
            state = harness.state(course)
            env = environment({"title": state["goal"]["title"], "goal": state["goal"]["goal"]}, directory, env)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
        env["HARNESS_COURSES"] = str(harness.store.courses)
        for variable, folder in [("JUPYTER_CONFIG_DIR", "config"), ("JUPYTER_DATA_DIR", "data"),
                                 ("JUPYTER_RUNTIME_DIR", "run"), ("IPYTHONDIR", "ipython")]:
            path = directory / folder
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            env[variable] = str(path)
        env["JUPYTER_PATH"] = str(directory / "data")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
        token = secrets.token_urlsafe(32)
        config = directory / "jupyter_config.py"
        root = harness.store.root(course)
        config.write_text("c.ServerApp.ip='127.0.0.1'\n" + f"c.ServerApp.root_dir={str(root)!r}\n"
            + f"c.ServerApp.port={port}\nc.ServerApp.port_retries=0\nc.ServerApp.open_browser=False\n"
            + f"c.IdentityProvider.token={token!r}\n", encoding="utf-8")
        if ai:
            from .tutor import jupyter_configuration
            with config.open("a", encoding="utf-8") as stream:
                stream.write(jupyter_configuration())
        config.chmod(0o600)
        with (directory / "jupyter.log").open("ab") as logfile:
            (directory / "jupyter.log").chmod(0o600)
            process = subprocess.Popen([python, "-m", "jupyterlab", "--config=" + str(config)],
                cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=logfile, stderr=logfile, start_new_session=True)
        info = {"pid": process.pid, "base_url": f"http://127.0.0.1:{port}", "token": token, "course_root": str(root)}
        for _ in range(80):
            if alive(info):
                atomic_json(info_path, info); info_path.chmod(0o600)
                break
            if process.poll() is not None:
                raise Invalid("Jupyter failed to start. Inspect the private runtime jupyter.log.")
            time.sleep(.15)
        else:
            process.terminate()
            raise Invalid("Jupyter startup timed out; inspect its runtime log")
    require(info.get("course_root") == str(harness.store.root(course)), "This runtime belongs to another course location")
    # Published artifacts stay immutable. Jupyter opens an editable copy under drafts/.
    draft_name = f"drafts/{record['id']}-{record['version']}/{record['entrypoint']}"
    draft = safe_path(harness.store.root(course), draft_name)
    if not draft.exists():
        import shutil
        source = safe_path(harness.store.root(course), record["path"])
        shutil.copytree(source, draft.parents[len(Path(record["entrypoint"]).parts) - 1], dirs_exist_ok=False)
    from urllib.parse import quote
    return {"url": info["base_url"] + "/lab/tree/" + quote(draft_name, safe="/") + "?token=" + info["token"],
            "draft": str(draft), "note": "Editable copy. Submit your work explicitly; running cells creates no assessment."}


def stop_all(runtime):
    """Stop only servers whose private runtime records this harness owns."""
    for path in Path(runtime).glob("*/*/jupyter.json"):
        info = read_json(path)
        if alive(info):
            request = Request(info["base_url"] + "/api/shutdown", data=b"", method="POST",
                              headers={"Authorization": "token " + info["token"]})
            with build_opener(ProxyHandler({})).open(request, timeout=5):
                pass
