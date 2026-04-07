# tb-loki-central-logger — developer reference

Quickstart: [README.md](README.md). Code: [`app/`](app/) → import **`tb_loki_central_logger`**.

**HTTP is async only** (`httpx.AsyncClient`). Names `AsyncLokiClient`, `configure_async`, `push_log_async`, `push_logs_async` are aliases for `LokiClient`, `configure`, `push_log`, `push_logs`.

---

## Smoke test (Grafana Cloud)

1. Copy [`env.example`](env.example) to `.env` with **`GRAFANA_CLOUD_URL`**, **`GRAFANA_CLOUD_USER`**, **`GRAFANA_CLOUD_API_KEY`** (legacy: `GRAFANA_CLOUD_WRITE_API_KEY`).
2. `python test.py`
3. Grafana **Explore → Loki**, e.g. `{service="my-app"}`.

---

## Environment

See README. No baked-in stack URL/user in code.

---

## API

### `LokiClient(url=None, labels=None, timeout=5, basic_auth=None)`

Async client. Defaults from `GRAFANA_CLOUD_*` / `.env` when args omitted.

```python
async with LokiClient(labels={"service": "worker"}) as c:
    await c.push("Job started")
    await c.push_batch([("Step 1", "info"), ("Step 2", "info")])
```

### `await configure(...)`

Sets module default client for **`push_log`** / **`push_logs`**. Close/replace by calling `configure` again (previous client is closed).

### `await push_log(message, level="info", labels=None)` · `await push_logs(entries)`

Uses default client from **`configure`**, or lazily creates one.

### `LokiHandler(...)`

`logging.Handler`: queue + daemon thread running **`asyncio.run`** and **`LokiClient`**. **`handler.close()`** drains the queue with **`asyncio.run`** on remaining records.

### `JsonLogFormatter` · `setup_central_logging` · `shutdown_central_logging`

See README. Loki attaches when **`GRAFANA_CLOUD_API_KEY`** (or legacy write key) + user are set—unless `loki=False`.

`setup_central_logging(..., formatter=my_formatter)` attaches the same **`logging.Formatter`** instance to stderr and **`LokiHandler`**; **`timezone`** and **`extra_json_fields`** are only used when **`formatter`** is omitted (default **`JsonLogFormatter`**).

---

## Log levels

**LokiHandler** maps `LogRecord.levelname` → Loki label. For **`push`**, pass the level string (e.g. `info`, `error`).

---

## Publish / install

See README and [`.github/workflows/publish.yml`](.github/workflows/publish.yml). Bump **`version`** in `pyproject.toml` / `__init__.py` before release.

```bash
pip install -e .
python test.py
```
