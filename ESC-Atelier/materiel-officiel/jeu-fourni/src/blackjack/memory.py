"""Dépôt local sans base; transaction réversible et verrou partagé."""

from contextlib import contextmanager
from copy import deepcopy
from threading import RLock


class MemoryStore:
    def __init__(self):
        self._sessions = {}
        self._requests = {}
        self._gone = {}
        self._lock = RLock()

    @contextmanager
    def transaction(self):
        with self._lock:
            transaction = MemoryTransaction(self)
            yield transaction
            transaction.commit()


class MemoryTransaction:
    def __init__(self, store):
        self._store = store
        self._sessions = {}
        self._requests = {}
        self._gone = {}

    def get_session(self, session_id):
        return deepcopy(self._sessions.get(session_id, self._store._sessions.get(session_id)))

    def put_session(self, session):
        self._sessions[session.session_id] = deepcopy(session)

    def get_request(self, owner, request_id):
        key = (owner, request_id)
        return deepcopy(self._requests.get(key, self._store._requests.get(key)))

    def put_request(self, owner, request_id, record):
        self._requests[owner, request_id] = deepcopy(record)

    def gone_owner(self, session_id):
        return self._gone.get(session_id, self._store._gone.get(session_id))

    def purge(self, session):
        self._sessions[session.session_id] = None
        self._gone[session.session_id] = session.owner
        for key, record in {**self._store._requests, **self._requests}.items():
            if record["session_id"] == session.session_id:
                self._requests[key] = {"session_id": session.session_id}

    def commit(self):
        for session_id, session in self._sessions.items():
            if session is None:
                self._store._sessions.pop(session_id, None)
            else:
                self._store._sessions[session_id] = session
        self._store._requests.update(self._requests)
        self._store._gone.update(self._gone)
