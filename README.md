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
