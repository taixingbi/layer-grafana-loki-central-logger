"""Non-blocking ``logging.Handler`` → Loki (worker thread + async httpx)."""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import Optional

from ._common import loki_level_for_record
from .client import LokiClient


class LokiHandler(logging.Handler):
    def __init__(
        self,
        url: Optional[str] = None,
        labels: Optional[dict] = None,
        timeout: int = 5,
        queue_size: int = 1000,
        basic_auth: Optional[tuple[str, str]] = None,
    ):
        super().__init__()
        self._url = url
        self._labels = labels
        self._timeout = timeout
        self._basic_auth = basic_auth
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run_async_worker,
            daemon=True,
            name="loki-handler",
        )
        self._thread.start()

    def _run_async_worker(self) -> None:
        asyncio.run(self._worker())

    async def _worker(self) -> None:
        async with LokiClient(
            url=self._url,
            labels=self._labels,
            timeout=self._timeout,
            basic_auth=self._basic_auth,
        ) as client:
            while True:
                if self._stop.is_set() and self._queue.empty():
                    break
                try:
                    rec = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                await self._ship(client, rec)

    async def _ship(
        self, client: LokiClient, record: logging.LogRecord
    ) -> None:
        await client.push(
            self.format(record),
            level=loki_level_for_record(record.levelname),
            labels={"logger": record.name},
        )

    def emit(self, record: logging.LogRecord):
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            pass

    def close(self):
        self._stop.set()
        self._thread.join(timeout=5)
        tail: list[logging.LogRecord] = []
        while not self._queue.empty():
            try:
                tail.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if tail:
            try:
                asyncio.run(self._flush_tail(tail))
            except Exception:
                pass
        super().close()

    async def _flush_tail(self, tail: list[logging.LogRecord]) -> None:
        async with LokiClient(
            url=self._url,
            labels=self._labels,
            timeout=self._timeout,
            basic_auth=self._basic_auth,
        ) as c:
            for rec in tail:
                await c.push(
                    self.format(rec),
                    level=loki_level_for_record(rec.levelname),
                    labels={"logger": rec.name},
                )
