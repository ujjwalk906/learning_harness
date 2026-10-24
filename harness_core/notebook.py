"""Optional notebook helpers: real C/C++/shell execution and explicit evidence."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile

from .engine import Harness


def run(command, *, input=None, timeout=10, cwd=None):
    if isinstance(command, str) or timeout <= 0:
        raise ValueError("Use a command argument list and a positive timeout")
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                   cwd=cwd, start_new_session=True)
        try:
            process.communicate(input.encode() if isinstance(input, str) else input, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        out.seek(0); err.seek(0)
        stdout, stderr = out.read(1024 * 1024).decode(errors="replace"), err.read(1024 * 1024).decode(errors="replace")
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n")
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _compile(source, cpp=False, *, args=(), input=None, flags=(), timeout=10):
    compiler = (os.environ.get("CXX") or shutil.which("clang++") or shutil.which("g++")) if cpp else (
        os.environ.get("CC") or shutil.which("clang") or shutil.which("cc"))
    if not compiler:
        raise RuntimeError("This activity requires an installed C/C++ compiler")
    with tempfile.TemporaryDirectory(prefix="learning-code-") as directory:
        path = Path(directory)
        source_path = path / ("experiment.cpp" if cpp else "experiment.c")
        source_path.write_text(source, encoding="utf-8")
        executable = path / "experiment"
        built = run([compiler, "-std=c++17" if cpp else "-std=c17", "-Wall", "-Wextra", *flags,
                     str(source_path), "-o", str(executable)], timeout=max(30, timeout))
        built.check_returncode()
        return run([str(executable), *map(str, args)], input=input, timeout=timeout)


def c(source, **kwargs):
    return _compile(source, **kwargs)


def cpp(source, **kwargs):
    return _compile(source, cpp=True, **kwargs)


def load_ipython_extension(ipython):
    def c_magic(line, cell):
        return c(cell, flags=shlex.split(line))
    def cpp_magic(line, cell):
        return cpp(cell, flags=shlex.split(line))
    def sh_magic(line, cell):
        return run(["sh", "-c", cell, "experiment", *shlex.split(line)])
    for name, function in [("c", c_magic), ("cpp", cpp_magic), ("sh", sh_magic)]:
        ipython.register_magic_function(function, "cell", name)


class Session:
    """Explicit activity identity prevents attribution to a different open notebook."""
    def __init__(self, course, activity, *, courses=None):
        self.harness = Harness(courses or os.environ["HARNESS_COURSES"])
        self.course, self.activity = course, activity
        if activity not in self.harness.state(course)["activities"]:
            raise ValueError("Unknown activity version")

    def submit(self, answer, *, assistance, artifacts=()):
        if os.environ.get("COURSE_AUTHOR_QA") == "1":
            raise RuntimeError("Author QA cannot submit learner evidence")
        return self.harness.submit(self.course, self.activity, answer, assistance, artifacts=artifacts)

    def observe(self, literal_text, *, kind="execution"):
        if os.environ.get("COURSE_AUTHOR_QA") == "1":
            raise RuntimeError("Author QA cannot write learner observations")
        return self.harness.record(self.course, "observation", {"text": literal_text,
            "role": "observer", "kind": kind, "activity": self.activity})
