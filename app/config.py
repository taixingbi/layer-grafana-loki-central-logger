"""
Grafana Cloud Loki env vars and ``.env`` loading.

Uses ``GRAFANA_CLOUD_API_KEY`` for the Loki write token; ``GRAFANA_CLOUD_WRITE_API_KEY``
is still read if the former is unset. Auto-loads ``.env`` from the cwd on import.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final, Optional

ENV_GRAFANA_CLOUD_URL: Final = "GRAFANA_CLOUD_URL"
ENV_GRAFANA_CLOUD_USER: Final = "GRAFANA_CLOUD_USER"
ENV_GRAFANA_CLOUD_API_KEY: Final = "GRAFANA_CLOUD_API_KEY"
_ENV_WRITE_LEGACY: Final = "GRAFANA_CLOUD_WRITE_API_KEY"


def load_dotenv(path: Path) -> None:
    """Merge ``path`` into ``os.environ``; never overrides existing keys."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip("'").strip('"')
        if key not in os.environ:
            os.environ[key] = value


def load_dotenv_cwd(filename: str = ".env") -> None:
    load_dotenv(Path.cwd() / filename)


def loki_url_from_env() -> str:
    return os.environ.get(ENV_GRAFANA_CLOUD_URL, "").strip()


def loki_user_from_env() -> str:
    return os.environ.get(ENV_GRAFANA_CLOUD_USER, "").strip()


def loki_token_from_env() -> Optional[str]:
    for key in (ENV_GRAFANA_CLOUD_API_KEY, _ENV_WRITE_LEGACY):
        t = os.environ.get(key, "").strip()
        if t:
            return t
    return None


def basic_auth_from_env() -> Optional[tuple[str, str]]:
    token = loki_token_from_env()
    user = loki_user_from_env()
    if not token or not user:
        return None
    return (user, token)


def push_endpoint(url: str) -> str:
    if not url.strip():
        raise ValueError("Loki URL is empty — set GRAFANA_CLOUD_URL")
    base = url.rstrip("/")
    if base.endswith("/loki/api/v1/push"):
        return base
    return f"{base}/loki/api/v1/push"


def resolve_push_target(
    url: Optional[str],
    labels: Optional[dict[str, Any]],
    basic_auth: Optional[tuple[str, str]],
) -> tuple[str, dict[str, Any], Optional[tuple[str, str]]]:
    """Normalize url/labels/auth for Loki clients (raises if URL missing)."""
    resolved = loki_url_from_env() if url is None else url
    if not str(resolved).strip():
        raise ValueError("Loki URL missing — set GRAFANA_CLOUD_URL or pass url=")
    auth = basic_auth_from_env() if basic_auth is None else basic_auth
    return (
        push_endpoint(str(resolved)),
        dict(labels) if labels else {},
        auth,
    )


load_dotenv_cwd()
