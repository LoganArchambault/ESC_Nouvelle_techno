"""Appels directs : aucun HTTP, service distant, fichier ou authentification réseau."""

from .memory import MemoryStore
from .model import PROTOCOL
from .sessions import SessionService, unwrap


class LocalClient:
    def __init__(self, limits, *, seed=None):
        self._service = SessionService(MemoryStore(), limits, seed=seed)

    def create_session(self, config_ref, model_ref, request_id):
        return self._command("create", None, request_id,
                             config_ref=config_ref, model_ref=model_ref)

    def observe(self, session_id):
        return unwrap(self._service.observe("local", session_id))

    def start_hand(self, session_id, expected_revision, request_id):
        return self._command("start", session_id, request_id,
                             expected_revision=expected_revision)

    def act(self, session_id, action, expected_revision, request_id):
        return self._command("act", session_id, request_id,
                             action=action, expected_revision=expected_revision)

    def close_session(self, session_id, expected_revision, request_id):
        return self._command("close", session_id, request_id,
                             expected_revision=expected_revision)

    def _command(self, command, session_id, request_id, **fields):
        return unwrap(self._service.command("local", command,
                      {"protocol_version": PROTOCOL, "request_id": request_id, **fields},
                      session_id))
