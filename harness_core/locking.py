"""Blocking advisory file locks for Windows and POSIX hosts."""
from contextlib import contextmanager
import errno
import os
import time

if os.name == "nt":
    import msvcrt
else:
    import fcntl


@contextmanager
def file_lock(path):
    with open(path, "a+b") as stream:
        if os.name == "nt":
            # Lock a fixed byte range, including when the file is empty.
            stream.seek(0)
            while True:
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    time.sleep(0.05)
        else:
            fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
