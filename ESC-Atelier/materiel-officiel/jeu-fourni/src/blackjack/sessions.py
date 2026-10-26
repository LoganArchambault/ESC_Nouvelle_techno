"""Transactions de séance communes aux transports; état privé derrière le dépôt."""

from copy import deepcopy
from random import Random
from time import time
from uuid import uuid4

from .engine import apply_command
from .errors import GameError
from .model import Session
from .projection import observe
from .validation import validate


class SessionService:
    def __init__(self, store, limits, *, clock=time, seed=None, new_id=lambda: uuid4().hex):
        self._store = store
        self._limits = limits
        self._clock = clock
        self._seed = seed
        self._new_id = new_id

    def command(self, owner, command, payload, session_id=None):
        validate(command, payload)
        request_id = payload["request_id"]
        fingerprint = {"command": command, "session_id": session_id, "payload": payload}
        # Le dépôt englobe lecture, tirage, écriture et réponse idempotente.
        with self._store.transaction() as tx:
            previous = tx.get_request(owner, request_id)
            if previous is not None:
                return self._repeat(tx, owner, fingerprint, previous)
            if command == "create":
                session = self._create(owner, payload)
            else:
                session = self._owned(tx, owner, session_id)
                if self._past_retention(session):
                    tx.purge(session)
                    # Retourner l'erreur hors transaction pour conserver le tombstone.
                    return GameError("session_gone", request_id=request_id)
                self._mutate(session, command, payload)
                if self._past_retention(session):
                    tx.purge(session)
                    return GameError("session_gone", request_id=request_id)
            tx.put_session(session)
            response = deepcopy(observe(session))
            tx.put_request(owner, request_id, {"fingerprint": fingerprint,
                                               "session_id": session.session_id,
                                               "response": response})
            return response

    def observe(self, owner, session_id):
        with self._store.transaction() as tx:
            session = self._owned(tx, owner, session_id)
            expired = self._expire(session)
            if self._past_retention(session):
                tx.purge(session)
                return GameError("session_gone")
            if expired:
                tx.put_session(session)
            response = deepcopy(observe(session))
            # Une lecture ne signale pas une nouvelle génération du paquet.
            response["shoe_reset"] = False
            return response

    def _create(self, owner, payload):
        now = self._clock()
        return Session(self._new_id(), owner, self._limits, now, now, Random(self._seed),
                       config_ref=payload["config_ref"], model_ref=payload["model_ref"])

    def _owned(self, tx, owner, session_id):
        session = tx.get_session(session_id)
        if session is not None and session.owner == owner:
            return session
        if tx.gone_owner(session_id) == owner:
            raise GameError("session_gone")
        raise GameError("session_not_found")

    def _past_retention(self, session):
        return (session.finished_at is not None
                and self._clock() >= session.finished_at + session.limits.retention_seconds)

    def _repeat(self, tx, owner, fingerprint, previous):
        session = self._owned(tx, owner, previous["session_id"])
        if self._expire(session):
            tx.put_session(session)
        if self._past_retention(session):
            tx.purge(session)
            return GameError("session_gone")
        if previous["fingerprint"] != fingerprint:
            raise GameError("idempotency_conflict", revision=session.revision,
                            request_id=fingerprint["payload"]["request_id"])
        return deepcopy(previous["response"])

    def _mutate(self, session, command, payload):
        if self._expire(session):
            return
        if payload["expected_revision"] != session.revision:
            raise GameError("revision_conflict", revision=session.revision,
                            request_id=payload["request_id"])
        try:
            changed = apply_command(session, command, payload.get("action"), self._new_id)
        except GameError as error:
            error.revision = session.revision
            error.request_id = payload["request_id"]
            raise
        if changed:
            session.revision += 1
            session.last_activity = self._clock()
        if session.session_status != "active" and session.finished_at is None:
            session.finished_at = self._clock()

    def _expire(self, session):
        if session.session_status != "active":
            return False
        time_deadline = session.created_at + session.limits.max_seconds
        idle_deadline = session.last_activity + session.limits.idle_seconds
        deadline = min(time_deadline, idle_deadline)
        if self._clock() < deadline:
            return False
        time_limit = time_deadline <= idle_deadline
        session.session_status = "truncated" if time_limit else "expired"
        session.end_reason = "time_limit" if time_limit else "idle_timeout"
        session.finished_at = deadline
        session.revision += 1
        session.shoe_reset = False
        session.visible_events = []
        return True


def unwrap(response):
    if isinstance(response, GameError):
        raise response
    return response
