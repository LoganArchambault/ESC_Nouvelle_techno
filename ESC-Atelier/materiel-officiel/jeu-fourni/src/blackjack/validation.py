"""Validation à la frontière commune, sans coercition de type JSON."""

import json
import re
from math import isfinite

from .errors import GameError
from .model import PROTOCOL

FIELDS = {
    "create": {"protocol_version", "config_ref", "model_ref", "request_id"},
    "start": {"protocol_version", "expected_revision", "request_id"},
    "act": {"protocol_version", "action", "expected_revision", "request_id"},
    "close": {"protocol_version", "expected_revision", "request_id"},
}


def validate(command, payload):
    if command not in FIELDS or type(payload) is not dict or set(payload) != FIELDS[command]:
        raise GameError("invalid_payload")
    if not all(type(payload[k]) is str and 1 <= len(payload[k]) <= 128
               for k in FIELDS[command] - {"expected_revision"}):
        raise GameError("invalid_payload")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", payload["request_id"]):
        raise GameError("invalid_payload")
    if payload["protocol_version"] != PROTOCOL:
        raise GameError("unsupported_version", request_id=payload["request_id"])
    if command != "create" and (type(payload["expected_revision"]) is not int
                                or payload["expected_revision"] < 0):
        raise GameError("invalid_payload", request_id=payload["request_id"])
    if command == "act" and payload["action"] not in ("hit", "hold"):
        raise GameError("invalid_payload", request_id=payload["request_id"])


def parse_json(raw):
    def reject_constant(value):
        raise ValueError("non-finite")

    def finite_float(value):
        number = float(value)
        if not isfinite(number):
            raise ValueError("non-finite")
        return number

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        return json.loads(raw, parse_constant=reject_constant, parse_float=finite_float,
                          object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise GameError("invalid_request") from None
