"""Disposable staging folders that retain normal workspace access on Windows."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import uuid


@contextmanager
def staging_directory(parent, prefix):
    # Windows mkdtemp uses an owner-only ACL. Renaming its children into a
    # workspace carries that ACL with them and can exclude sandboxed commands.
    parent = Path(parent).resolve()
    directory = parent / (prefix + uuid.uuid4().hex)
    directory.mkdir(mode=0o755 if os.name == "nt" else 0o700)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)
