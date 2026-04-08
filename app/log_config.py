"""JSON stderr logging + optional :class:`LokiHandler`."""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO
from zoneinfo import ZoneInfo

from .config import basic_auth_from_env, load_dotenv
from .handler import LokiHandler

# JSON key order: ts → level → logger → request_* / HTTP context → message → error → other extras
_JSON_CONTEXT_KEYS = ("request_id", "session_id", "method", "path", "status")
_JSON_FIXED_KEYS = frozenset(
    {"ts", "level", "logger", *_JSON_CONTEXT_KEYS, "message", "error"}
)


def _resolve_logger(
    logger: logging.Logger | str | None, logger_name: str
) -> logging.Logger:
    if logger is None:
        return logging.getLogger(logger_name)
    if isinstance(logger, str):
        return logging.getLogger(logger)
    return logger


def _default_loki_labels(
    service: str,
    component: str | None,
    env: str | None,
    version: str | None,
    pkg_version: str,
    extra: Optional[dict],
) -> dict[str, str]:
    labels: dict[str, str] = {"service": service}
    if component:
        labels["component"] = component
    labels["env"] = env if env is not None else os.environ.get("ENV", "dev")
    labels["version"] = version if version is not None else pkg_version
    if extra:
        labels.update({k: str(v) for k, v in extra.items()})
    return labels


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line."""

    def __init__(
        self,
        *,
        timezone: str = "EST",
        extra_fields: Sequence[str] = (),
    ):
        super().__init__()
        self._tz = ZoneInfo(timezone)
        self._extras = tuple(extra_fields)

    def format(self, record: logging.LogRecord) -> str:
        err = self.formatException(record.exc_info) if record.exc_info else None
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=self._tz).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        for key in _JSON_CONTEXT_KEYS:
            payload[key] = getattr(record, key, "-")
        payload["message"] = record.getMessage()
        payload["error"] = err
        for key in self._extras:
            if key in _JSON_FIXED_KEYS:
                continue
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_central_logging(
    logger: logging.Logger | str | None = None,
    *,
    logger_name: str = "app",
    load_dotenv_path: Path | None = None,
    timezone: str = "EST",
    extra_json_fields: Sequence[str] = (),
    formatter: Optional[logging.Formatter] = None,
    level: int = logging.INFO,
    filters: Sequence[logging.Filter] = (),
    stream: TextIO | None = None,
    use_stderr: bool = True,
    loki: bool | None = None,
    loki_labels: Optional[dict] = None,
    service: str = "app",
    component: str | None = None,
    env: str | None = None,
    version: str | None = None,
) -> LokiHandler | None:
    """Wire stderr and optional Loki with a shared formatter.

    If *formatter* is set, it is attached to both handlers; *timezone* and
    *extra_json_fields* are ignored. Otherwise a :class:`JsonLogFormatter` is
    built from those keyword arguments.
    """
    from . import __version__ as pkg_version

    log = _resolve_logger(logger, logger_name)
    if load_dotenv_path is not None:
        load_dotenv(load_dotenv_path)

    auth = basic_auth_from_env()
    use_loki = auth is not None if loki is None else bool(loki)
    if use_loki and auth is None:
        log.warning(
            "Loki requested but credentials missing — set GRAFANA_CLOUD_USER and GRAFANA_CLOUD_API_KEY"
        )
        use_loki = False

    log.setLevel(level)
    log.handlers.clear()
    log.filters.clear()
    log.propagate = False
    for f in filters:
        log.addFilter(f)

    fmt = formatter or JsonLogFormatter(
        timezone=timezone, extra_fields=extra_json_fields
    )
    if use_stderr:
        sh = logging.StreamHandler(stream or sys.stderr)
        sh.setLevel(level)
        sh.setFormatter(fmt)
        log.addHandler(sh)

    loki_h: LokiHandler | None = None
    if use_loki and auth:
        labels = _default_loki_labels(
            service, component, env, version, pkg_version, loki_labels
        )
        loki_h = LokiHandler(labels=labels, basic_auth=auth)
        loki_h.setLevel(level)
        loki_h.setFormatter(fmt)
        log.addHandler(loki_h)
        log.info("Loki logging enabled")
    elif loki is not False and auth is None:
        log.info("Loki disabled — set GRAFANA_CLOUD_USER and GRAFANA_CLOUD_API_KEY")

    return loki_h


def shutdown_central_logging(
    log: logging.Logger | str,
    loki_handler: LokiHandler | None,
) -> None:
    lg = logging.getLogger(log) if isinstance(log, str) else log
    if loki_handler is not None:
        lg.removeHandler(loki_handler)
        loki_handler.close()
