# tb-loki-central-logger

Push application logs to **Grafana Loki** using **`httpx`** (async only). Provides **`LokiClient`**, **`await push_log` / `await push_logs`**, and a non-blocking **`LokiHandler`** for the standard library **`logging`** module.

| | |
|---|---|
| **Python** | 3.10+ |
| **Dependency** | `httpx>=0.27,<1` |
| **Layout** | Source in [`app/`](app/), import package **`tb_loki_central_logger`** |

**v0.2+** — There is no synchronous HTTP client. Use **`await`** (or **`asyncio.run`**) for **`configure`**, **`push_log`**, and **`push_logs`**. The names **`AsyncLokiClient`**, **`configure_async`**, **`push_log_async`**, **`push_logs_async`** are aliases and behave the same.

---

## Install

```bash
pip install tb-loki-central-logger
```

From TestPyPI:

```bash
pip install -i https://test.pypi.org/simple/ tb-loki-central-logger
```

Local checkout:

```bash
pip install -e .
```

---

## Configuration

The first time you **`import tb_loki_central_logger`**, it loads **`.env` from the process current working directory** (`Path.cwd() / ".env"`) and merges keys into **`os.environ`** without overwriting keys that are already set.

So if you run the app from your **project root** (where `.env` usually lives), you **do not** need **`from pathlib import Path`**, **`load_dotenv(Path(".env"))`**, or **`load_dotenv_path=...`** in the examples below — credentials are already available after import.

Only call **`load_dotenv(some_path)`** when `.env` lives somewhere else (or you need a second file). **`setup_central_logging(..., load_dotenv_path=...)`** is optional for the same reason.

| Variable | Purpose |
|----------|---------|
| `GRAFANA_CLOUD_URL` | Loki host (e.g. `https://logs-prod-….grafana.net`) or full `…/loki/api/v1/push` (**required** for env-based clients) |
| `GRAFANA_CLOUD_USER` | HTTP Basic **username** (Grafana stack / tenant id) |
| `GRAFANA_CLOUD_API_KEY` | HTTP Basic **password** (Loki write-capable token) |
| `GRAFANA_CLOUD_WRITE_API_KEY` | Legacy fallback if `GRAFANA_CLOUD_API_KEY` is unset |

Use [`env.example`](env.example) as a template. In Grafana Cloud: stack → **Loki** → **Details** / **Send logs** for URL and user; **Security** / **Access policies** for tokens. More context: [Send logs to Grafana Cloud](https://grafana.com/docs/grafana-cloud/send-data/logs/).

---

## `logging` + `LokiHandler`

The **stdlib `logging` API is not async** — you write `logging.info(...)` with no `await`. **`LokiHandler.emit()`** only enqueues the record; a **background thread** runs **`asyncio`** + **`LokiClient`** so your app thread never waits on Loki HTTP. (Direct pushes still use **`await push_log`** / **`async with LokiClient`** elsewhere in this package.)

The **root logger’s default level is `WARNING`** (Python stdlib), not `INFO`. Without **`root.setLevel(logging.INFO)`**, calls like **`logging.info(...)`** are filtered out before any handler runs—**`LokiHandler` never sees them.**

```python
import logging

from tb_loki_central_logger import LokiHandler, basic_auth_from_env

# .env in cwd is already loaded on import; run this script from project root.

auth = basic_auth_from_env()
if not auth:
    raise SystemExit("Set GRAFANA_CLOUD_URL, GRAFANA_CLOUD_USER, GRAFANA_CLOUD_API_KEY")

root = logging.getLogger()
root.setLevel(logging.INFO)  # required for logging.info(); root defaults to WARNING

h = LokiHandler(labels={"service": "my-app", "env": "dev"}, basic_auth=auth)
root.addHandler(h)

logging.info("Hello")
h.close()
```

---

## Async pushes: `LokiClient`, `configure`, `push_log`, `push_logs`

```python
import asyncio
from tb_loki_central_logger import LokiClient, configure, push_log, push_logs

async def main():
    # Default client for push_log / push_logs (reads GRAFANA_CLOUD_* / .env)
    await configure(labels={"service": "my-app"})
    await push_log("Hello", level="info")
    await push_logs([("Started", "info"), ("Ready", "info")])

    # Dedicated client
    async with LokiClient(labels={"worker": "1"}) as c:
        await c.push("done")

asyncio.run(main())
```

Pass **`basic_auth=(user, token)`** and/or **`url=...`** into **`LokiClient`** / **`configure`** when you do not rely on environment defaults.

---

## JSON logs on stderr + Loki: `setup_central_logging`

Structured JSON to stderr and a **`LokiHandler`** when credentials are present. The default **`JsonLogFormatter`** emits keys in this order: **`ts`**, **`level`**, **`logger`**, **`request_id`**, **`session_id`**, **`method`**, **`path`**, **`status`** (HTTP-style context, **`"-"`** when not set on the record), **`message`**, **`error`**, then any attributes listed in **`extra_json_fields`** that are not among those fixed keys. Use **`filters`** for shared context, or **`formatter=`** for a fully custom formatter (same instance is used for stderr and Loki).

```python
from tb_loki_central_logger import setup_central_logging, shutdown_central_logging

loki = setup_central_logging(
    "myapp.api",
    timezone="America/New_York",
    extra_json_fields=("latency_ms",),  # optional tail fields; context keys above are always present
    service="my-service",
    component="api",
)

shutdown_central_logging("myapp.api", loki)
```

### Custom formatter (fixed keys, `"-"` when missing)

Use this when you want an exact JSON shape (for example HTTP context) instead of the built-in **`level`** / **`logger`** fields. **`timezone`** and **`extra_json_fields`** are ignored when **`formatter`** is set.

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from tb_loki_central_logger import setup_central_logging

_EXTRA_JSON_FIELDS = ("latency_ms",)  # optional keys, only if present on the record


class MyJsonFormatter(logging.Formatter):
    """One JSON object per line for stderr and Loki."""

    def __init__(self, *, timezone: str = "America/New_York"):
        super().__init__()
        self._tz = ZoneInfo(timezone)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=self._tz).isoformat(),
            "request_id": getattr(record, "request_id", "-"),
            "session_id": getattr(record, "session_id", "-"),
            "method": getattr(record, "method", "-"),
            "path": getattr(record, "path", "-"),
            "status": getattr(record, "status", "-"),
            "message": record.getMessage(),
            "error": self.formatException(record.exc_info) if record.exc_info else None,
        }
        for key in _EXTRA_JSON_FIELDS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


setup_central_logging(
    logger_name="app",
    formatter=MyJsonFormatter(),
    loki=False,  # True when GRAFANA_CLOUD_* is set
)

logging.getLogger("app").info(
    "complete_rag_answer done k_used=5",
    extra={
        "request_id": "request_id_1",
        "session_id": "session_id_1",
        "method": "POST",
        "path": "/v1/rag/query",
        "status": "200",
    },
)
```

Example line on stderr (or Loki message body):

```json
{"ts": "2026-04-07T08:31:41.006403-04:00", "request_id": "request_id_1", "session_id": "session_id_1", "method": "POST", "path": "/v1/rag/query", "status": "200", "message": "complete_rag_answer done k_used=5", "error": null}
```

---

## Package surface

| Export | Role |
|--------|------|
| `LokiClient` | Async push client (`async with`, `push`, `push_batch`, `aclose`) |
| `configure` | **`await`** once to set the default client for `push_log` / `push_logs` |
| `push_log`, `push_logs` | **`await`** — use default client |
| `LokiHandler` | `logging.Handler` → Loki |
| `JsonLogFormatter`, `setup_central_logging`, `shutdown_central_logging` | Central JSON + optional Loki |
| `load_dotenv`, `basic_auth_from_env`, `loki_url_from_env`, … | Env / `.env` helpers (see `__all__` in the package) |

Full API notes: **[`instruction.md`](instruction.md)**.
