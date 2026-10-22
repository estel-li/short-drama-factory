"""Shared locks for read/check/write operations in the single API process."""
from functools import wraps
from threading import RLock

_guard = RLock()
_locks = {}


def project_lock(database, pid):
    key = (str(database.path.resolve()), pid)
    with _guard:
        return _locks.setdefault(key, RLock())


def locked_project(method):
    @wraps(method)
    def wrapped(self, pid, *args, **kwargs):
        with project_lock(self.db, pid):
            return method(self, pid, *args, **kwargs)
    return wrapped
