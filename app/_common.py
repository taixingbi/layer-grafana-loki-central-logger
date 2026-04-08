"""Shared Loki push helpers (auth, payloads, httpx errors, log levels)."""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Optional

import httpx

LOKI_LEVEL_FOR_RECORD: dict[str, str] = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warn",
    "ERROR": "error",
    "CRITICAL": "critical",
}


def loki_level_for_record(levelname: str) -> str:
    return LOKI_LEVEL_FOR_RECORD.get(levelname, "info")


def _ns_now() -> str:
    return str(int(time.time() * 1e9))


def basic_auth_headers(basic_auth: Optional[tuple[str, str]]) -> dict[str, str]:
    if not basic_auth:
        return {}
    user, token = basic_auth
    b = base64.b64encode(f"{user}:{token}".encode()).decode("ascii")
    return {"Authorization": f"Basic {b}"}


def httpx_error_body(exc: httpx.HTTPStatusError) -> str:
    try:
        return exc.response.text
    except Exception:
        return exc.response.reason_phrase


def as_loki_runtime_error(exc: BaseException) -> RuntimeError:
    if isinstance(exc, httpx.HTTPStatusError):
        return RuntimeError(
            f"Loki push failed: HTTP {exc.response.status_code} {httpx_error_body(exc)}"
        )
    if isinstance(exc, httpx.RequestError):
        return RuntimeError(f"Loki push failed: {exc}")
    return RuntimeError(f"Loki push failed: {exc}")


def build_single_push_body(
    default_labels: dict[str, Any],
    message: str,
    level: str,
    labels: Optional[dict[str, Any]] = None,
) -> bytes:
    merged = {**default_labels, "level": level}
    if labels:
        merged.update(labels)
    return json.dumps(
        {
            "streams": [
                {"stream": merged, "values": [[_ns_now(), message]]},
            ]
        }
    ).encode("utf-8")


def build_batch_push_body(
    default_labels: dict[str, Any],
    entries: list[tuple[str, str]],
) -> bytes:
    streams: dict[str, dict[str, Any]] = {}
    for message, level in entries:
        label = {**default_labels, "level": level}
        key = json.dumps(label, sort_keys=True)
        if key not in streams:
            streams[key] = {"stream": label, "values": []}
        streams[key]["values"].append([_ns_now(), message])
    return json.dumps({"streams": list(streams.values())}).encode("utf-8")
