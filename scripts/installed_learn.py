#!/usr/bin/env python3
"""Packaged entry point: keep learner records outside replaceable skill files."""
import json
import os
from pathlib import Path
import sys

from harness_core.cli import main


if __name__ == "__main__":
    config = json.loads(Path(__file__).with_name("fieldnotes.json").read_text(encoding="utf-8"))
    data = Path(os.environ.get("FIELDNOTES_HOME") or config.get("data_dir") or Path.home() / "Fieldnotes").expanduser().resolve()
    main(["--courses", str(data / "courses"), "--runtime", str(data / ".runtime"), *sys.argv[1:]])
