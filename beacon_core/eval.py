"""Pure feature-flag evaluation.

A caller's bucket is a number from 0 to 9999 derived from the flag, a salt, and
the user key. The same inputs always land in the same bucket, so a 5% rollout
keeps the same people inside it.
"""

from __future__ import annotations

import hashlib
from typing import Any


def bucket(flag_key: str, salt: str, user_key: str) -> int:
    raw = hashlib.sha256(f"{flag_key}\0{salt}\0{user_key}".encode()).digest()
    return int.from_bytes(raw[:8], "big") % 10000


def _attribute(user: dict, name: str) -> Any:
    if name == "key":
        return user.get("key")
    return (user.get("attributes") or {}).get(name)


def _clause_matches(clause: dict, user: dict) -> bool:
    value = _attribute(user, clause["attribute"])
    op = clause["op"]
    values = clause.get("values") or []
    if op in {"eq", "in"}:
        return value in values
    if not isinstance(value, str):
        if op in {"gt", "lt"} and value is not None and values:
            if op == "gt":
                return value > values[0]
            return value < values[0]
        return False
    if op == "contains":
        return any(item in value for item in values)
    if op == "starts_with":
        return any(value.startswith(item) for item in values)
    if op == "ends_with":
        return any(value.endswith(item) for item in values)
    if op == "gt" and values:
        return value > values[0]
    if op == "lt" and values:
        return value < values[0]
    return False


def _in_segment(segment: dict, user: dict) -> bool:
    return all(_clause_matches(clause, user) for clause in segment.get("clauses") or [])


def _clause_holds(clause: dict, user: dict, segments: dict) -> bool:
    if clause.get("attribute") == "segment":
        for key in clause.get("values") or []:
            segment = segments.get(key)
            if segment is None or not _in_segment(segment, user):
                return False
        return bool(clause.get("values"))
    return _clause_matches(clause, user)


def _in_rollout(flag_key: str, salt: str, user_key: str, basis_points: int | None) -> bool:
    if basis_points is None:
        return True
    return bucket(flag_key, salt, user_key) < basis_points


def _result(flag: dict, variation: str, reason: str) -> dict:
    variations = flag.get("variations") or {}
    return {
        "flag": flag["key"],
        "variation": variation,
        "value": variations.get(variation),
        "reason": reason,
    }


def evaluate_flag(flag: dict, user: dict, segments: dict | None = None) -> dict:
    segments = segments or {}
    if not flag.get("enabled"):
        return _result(flag, flag["off"], "off")
    user_key = str(user.get("key") or "")
    for index, rule in enumerate(flag.get("rules") or []):
        clauses = rule.get("clauses") or []
        if clauses and all(_clause_holds(clause, user, segments) for clause in clauses):
            salt = f"{flag.get('salt') or ''}:rule:{rule.get('id', index)}"
            if _in_rollout(flag["key"], salt, user_key, rule.get("rollout")):
                return _result(flag, rule["variation"], "rule")
    rollout = flag.get("rollout")
    if rollout is not None:
        if _in_rollout(flag["key"], flag.get("salt") or "", user_key, rollout):
            return _result(flag, flag["fallthrough"], "rollout")
        return _result(flag, flag["off"], "rollout")
    return _result(flag, flag["fallthrough"], "fallthrough")


def evaluate_all(snapshot: dict, user: dict) -> list[dict]:
    segments = snapshot.get("segments") or {}
    return [evaluate_flag(flag, user, segments) for flag in snapshot.get("flags") or []]
