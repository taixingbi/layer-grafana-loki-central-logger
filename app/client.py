"""Async Loki client (httpx only): :class:`LokiClient`, :func:`configure`, :func:`push_log`, :func:`push_logs`."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from ._common import (
    as_loki_runtime_error,
    basic_auth_headers,
    build_batch_push_body,
    build_single_push_body,
)
from .config import resolve_push_target


class LokiClient:
    """Async Loki push — ``async with`` or ``await aclose()``."""

    def __init__(
        self,
        url: Optional[str] = None,
        labels: Optional[dict[str, Any]] = None,
        timeout: int = 5,
        basic_auth: Optional[tuple[str, str]] = None,
    ):
        self.endpoint, self.default_labels, auth = resolve_push_target(
            url, labels, basic_auth
        )
        self.timeout = timeout
        self._headers = {
            "Content-Type": "application/json",
            **basic_auth_headers(auth),
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout, headers=self._headers
            )
        return self._client

    async def _send(self, body: bytes) -> None:
        client = await self._http()
        try:
            r = await client.post(self.endpoint, content=body)
            r.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            raise as_loki_runtime_error(e) from e

    async def push(
        self,
        message: str,
        level: str = "info",
        labels: Optional[dict[str, Any]] = None,
    ) -> None:
        await self._send(
            build_single_push_body(self.default_labels, message, level, labels)
        )

    async def push_batch(self, entries: list[tuple[str, str]]) -> None:
        await self._send(build_batch_push_body(self.default_labels, entries))

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> LokiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


_default: Optional[LokiClient] = None


async def configure(
    url: Optional[str] = None,
    labels: Optional[dict[str, Any]] = None,
    timeout: int = 5,
    basic_auth: Optional[tuple[str, str]] = None,
) -> None:
    global _default
    if _default is not None:
        await _default.aclose()
    _default = LokiClient(
        url=url, labels=labels, timeout=timeout, basic_auth=basic_auth
    )


async def _get() -> LokiClient:
    global _default
    if _default is None:
        _default = LokiClient()
    return _default


async def push_log(
    message: str,
    level: str = "info",
    labels: Optional[dict[str, Any]] = None,
) -> None:
    c = await _get()
    await c.push(message, level=level, labels=labels)


async def push_logs(entries: list[tuple[str, str]]) -> None:
    c = await _get()
    await c.push_batch(entries)
