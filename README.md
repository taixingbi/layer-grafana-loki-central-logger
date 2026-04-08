# tb-loki-central-logger

Send logs to **Grafana Loki** with **httpx** (async API for direct pushes; **`LokiHandler`** uses a background thread so `logging.info` stays synchronous).

**Python 3.10+** · dependency: `httpx` · import: **`tb_loki_central_logger`** (source in [`app/`](app/))

---

## Install

```bash
pip install tb-loki-central-logger
# TestPyPI: pip install -i https://test.pypi.org/simple/ tb-loki-central-logger
# From this repo: pip install -e .
```

---

## Environment

Copy [`env.example`](env.example) to **`.env`** in the process working directory (loaded on first `import tb_loki_central_logger`).

| Variable | Purpose |
|----------|---------|
| `GRAFANA_CLOUD_URL` | Loki / stack URL |
| `GRAFANA_CLOUD_USER` | Basic auth user (stack id) |
| `GRAFANA_CLOUD_API_KEY` | Basic auth password (write token) |

Legacy: `GRAFANA_CLOUD_WRITE_API_KEY` if `GRAFANA_CLOUD_API_KEY` is unset.

---

## Quick start (`setup_central_logging`)

JSON on stderr and Loki when credentials exist. Use the **same logger name** you pass to `setup_central_logging`. Optional tail fields via `extra_json_fields`. `request_id`, `session_id`, `method`, `path`, and `status` are always present on each line (`"-"` if unset); see [`app/log_config.py`](app/log_config.py).

```python
import logging

from tb_loki_central_logger import setup_central_logging, shutdown_central_logging

LOGGER_NAME = "layer-gateway-llm-inference-v1"

loki_handler = setup_central_logging(
    logger_name=LOGGER_NAME,
    extra_json_fields=(
        "retrieval_latency_s",
        "rerank_latency_s",
        "llm_latency_s",
    ),
    service="my-app-test",
    component="api",
    env="dev",
    version="1.3.0",
    loki_labels={"team": "platform"},
)

_payload = {
    "request_id": "request_id_1",
    "session_id": "session_id_1",
    "method": "POST",
    "path": "/v1/rag/query",
    "status": "200",
    "retrieval_latency_s": None,
    "rerank_latency_s": None,
    "llm_latency_s": None,
}

log = logging.LoggerAdapter(logging.getLogger(LOGGER_NAME), _payload)

try:
    log.info("hello info")
    log.warning("hello warning")
    log.error("hello error")

    log.extra["retrieval_latency_s"] = 1.234
    log.extra["rerank_latency_s"] = 2.345
    log.extra["llm_latency_s"] = 4.567
    log.info("hello info with timing")

finally:
    shutdown_central_logging(LOGGER_NAME, loki_handler)

```

**Async** pushes: `await configure(...)`, `await push_log(...)`, or `async with LokiClient(...) as c`. Details: [`instruction.md`](instruction.md).
=======
```

Latest builds from TestPyPI:

```bash
pip install -i https://test.pypi.org/simple/ tb-loki-central-logger
```

## Configuration

Use **environment variables** or a **`.env`** file in the process working directory. When you `import tb_loki_central_logger`, `config` loads `.env` and **does not override** variables already set in the environment.

| Variable | Role |
|----------|------|
| `GRAFANA_CLOUD_URL` | Loki host or full `.../loki/api/v1/push` (optional; defaults match Grafana Cloud) |
| `GRAFANA_CLOUD_USER` | Basic-auth **username**: numeric tenant / stack / “Loki user” id (not your email) |
| `GRAFANA_CLOUD_WRITE_API_KEY` | Basic-auth password: Loki **write** API token |
| `GRAFANA_CLOUD_API_KEY` | Legacy alias for the write token |

**Where to find `GRAFANA_CLOUD_URL` and `GRAFANA_CLOUD_USER`**

1. Sign in to [Grafana Cloud](https://grafana.com/), pick your stack in the **GRAFANA CLOUD** sidebar.
2. On **Manage stack**, open the **Loki** card → **Details** or **Send logs**. That page shows the Loki **URL** (often `https://logs-prod-…grafana.net` with push path `/loki/api/v1/push`) — use the host or full URL for `GRAFANA_CLOUD_URL`.
3. The same screen (or the “Send logs” / client setup snippet) shows the **User** value for HTTP Basic auth — put that number/string in `GRAFANA_CLOUD_USER`.

You can also open the stack’s **hosted logs** page in the browser:  
`https://grafana.com/orgs/<your-org>/hosted-logs/<id>` — the `<id>` in the path is usually the **same** value as `GRAFANA_CLOUD_USER`. Example: [`…/hosted-logs/1529533`](https://grafana.com/orgs/taixingbi/hosted-logs/1529533) → user `1529533`.

Copy [`env.example`](env.example) and replace placeholders:

```env
GRAFANA_CLOUD_URL=https://logs-prod-XXX.grafana.net
GRAFANA_CLOUD_USER=your-stack-user-id
GRAFANA_CLOUD_WRITE_API_KEY=your-loki-write-token
```

Create a write token under **Grafana Cloud** → your stack → **Security** / **Access policies** (scopes must allow Loki ingestion). See also [Grafana Cloud Loki](https://grafana.com/docs/grafana-cloud/send-data/logs/).

## Logging example

```python
import logging
from pathlib import Path

from tb_loki_central_logger import LokiHandler, basic_auth_from_env, load_dotenv

load_dotenv(Path(".env"))

auth = basic_auth_from_env()
if auth is None:
    raise SystemExit(
        "Set GRAFANA_CLOUD_WRITE_API_KEY (or GRAFANA_CLOUD_API_KEY) in the environment or .env; "
        "optionally GRAFANA_CLOUD_USER for Basic auth."
    )

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = LokiHandler(labels={"service": "my-app", "env": "dev"}, basic_auth=auth)
handler.setLevel(logging.INFO)
root_logger.addHandler(handler)

logging.info("Hello, info")
logging.warning("Hello, warning")
logging.error("Hello, error")

handler.close()
```