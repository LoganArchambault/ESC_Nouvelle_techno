"""Transport stdlib borné; aucune règle de jeu ou politique de décision."""

from copy import deepcopy
import json
from math import isfinite
import ssl
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .errors import GameError
from .model import PROTOCOL, RULESET
from .validation import parse_json


class TransportUncertain(Exception):
    """Réponse absente/invalide : conserver et réessayer la même commande."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPSClient:
    def __init__(self, base_url, token, *, timeout=5, max_attempts=2):
        self._configure(base_url, token, timeout, max_attempts, loopback=False)

    @classmethod
    def _for_loopback_tests(cls, base_url, token, *, timeout=5, max_attempts=2):
        client = cls.__new__(cls)
        client._configure(base_url, token, timeout, max_attempts, loopback=True)
        return client

    def _configure(self, base_url, token, timeout, max_attempts, *, loopback):
        url = urlsplit(base_url)
        allowed_http = loopback and url.scheme == "http" and url.hostname == "127.0.0.1"
        if (url.scheme != "https" and not allowed_http) or not url.hostname or url.username \
                or url.password or url.path not in ("", "/") or url.query or url.fragment:
            raise ValueError("Une origine HTTPS sans identifiant ni chemin est requise.")
        if type(token) is not str or not token or any(c.isspace() for c in token):
            raise ValueError("Jeton opaque requis.")
        if type(timeout) not in (int, float) or not isfinite(timeout) or timeout <= 0:
            raise ValueError("Délai positif et fini requis.")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError("Entre une et cinq tentatives sont permises.")
        self._base = base_url.rstrip("/") + "/api/v1/sessions"
        self._token = token
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._opener = build_opener(_NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        self._pending = None

    def create_session(self, config_ref, model_ref, request_id):
        return self._command("", {"config_ref": config_ref, "model_ref": model_ref,
                                  "request_id": request_id})

    def observe(self, session_id):
        return self._send("GET", "/" + quote(session_id, safe=""), None)

    def start_hand(self, session_id, expected_revision, request_id):
        return self._command("/" + quote(session_id, safe="") + "/hands",
                             {"expected_revision": expected_revision, "request_id": request_id})

    def act(self, session_id, action, expected_revision, request_id):
        return self._command("/" + quote(session_id, safe="") + "/actions",
                             {"action": action, "expected_revision": expected_revision,
                              "request_id": request_id})

    def close_session(self, session_id, expected_revision, request_id):
        return self._command("/" + quote(session_id, safe="") + "/close",
                             {"expected_revision": expected_revision, "request_id": request_id})

    def retry_pending(self):
        if self._pending is None:
            raise ValueError("Aucune commande incertaine.")
        suffix, payload = self._pending
        return self._command(suffix, payload)

    def _command(self, suffix, payload):
        payload = {"protocol_version": PROTOCOL, **payload}
        command = (suffix, deepcopy(payload))
        if self._pending is not None and self._pending != command:
            raise TransportUncertain("Résoudre la commande précédente avec retry_pending().")
        self._pending = command
        try:
            response = self._send("POST", suffix, payload)
        except GameError as error:
            if error.status not in (429, 503):
                self._pending = None
            raise
        self._pending = None
        return response

    def _send(self, method, suffix, payload):
        raw = json.dumps(payload, allow_nan=False).encode("utf-8") if payload else None
        for attempt in range(self._max_attempts):
            request = Request(self._base + suffix, data=raw, method=method,
                              headers={"Authorization": "Bearer " + self._token,
                                       "Content-Type": "application/json"})
            try:
                with self._opener.open(request, timeout=self._timeout) as response:
                    result = parse_json(response.read(1_000_001))
                if type(result) is not dict or result.get("protocol_version") != PROTOCOL \
                        or result.get("ruleset_id") != RULESET:
                    raise TransportUncertain("Réponse incompatible; état à vérifier.")
                return result
            except HTTPError as error:
                self._http_error(error, attempt)
            except (URLError, OSError, TimeoutError):
                if attempt + 1 == self._max_attempts:
                    raise TransportUncertain("Réponse absente; état à vérifier.") from None
            except GameError:
                raise TransportUncertain("Réponse JSON invalide; état à vérifier.") from None
        raise TransportUncertain("Réponse absente; état à vérifier.")

    def _http_error(self, error, attempt):
        with error:
            try:
                body = parse_json(error.read(1_000_001))
                code = body["error"]["code"]
                business = GameError(code, revision=body.get("revision"),
                                     request_id=body["error"].get("request_id"))
            except (GameError, KeyError, TypeError):
                raise TransportUncertain("Erreur distante non reconnue.") from None
        delay = 0
        if error.code == 429:
            try:
                delay = float(error.headers.get("Retry-After", "0"))
            except ValueError:
                delay = float("inf")
        retryable = error.code in (429, 503) and 0 <= delay <= 2
        if retryable and attempt + 1 < self._max_attempts:
            sleep(delay)
            return
        raise business
