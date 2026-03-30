# tb-loki-central-logger — developer reference

User-facing quickstart lives in [README.md](README.md). This page is **setup details**, **API tables**, and **release** notes.

---

## Smoke test (Grafana Cloud)

1. Copy [`env.example`](env.example) to `.env` and set `GRAFANA_CLOUD_WRITE_API_KEY` (and user/URL if needed).
2. Run:

```bash
python test.py
```

3. In **Grafana Cloud → Explore → Loki**, query by label, for example:

```logql
{service="my-app"}
```

Adjust labels to match what you pass into `LokiHandler` / `configure`.

## Environment variables

Loaded from `.env` in the **current working directory** on import when keys are not already set in the process environment. See [README.md](README.md#configuration) and `config.py` for names and defaults.

---

## API reference

### `configure(url=None, labels=None, timeout=5, basic_auth=None)`

Sets the module-level client used by `push_log` / `push_logs`. Call once at startup.

Omit `url` and `basic_auth` to use `GRAFANA_CLOUD_*` (or `.env`).  
`labels` become defaults on every line.

### `push_log(message, level="info", labels=None)`

Single line through the default client.

```python
from tb_loki_central_logger import push_log

push_log("Hello", level="info", labels={"request_id": "abc123"})
```

### `push_logs(entries)`

One HTTP request with many lines. `entries` is a list of `(message, level)` strings.

```python
from tb_loki_central_logger import push_logs

push_logs([
    ("Started", "info"),
    ("Config loaded", "info"),
    ("Cache miss", "warn"),
])
```

### `LokiClient(url=None, labels=None, timeout=5, basic_auth=None)`

Reusable client. Defaults for `url` / `basic_auth` match `configure`. Host may be a Loki base URL or full `…/loki/api/v1/push`.

```python
from tb_loki_central_logger import LokiClient

client = LokiClient(labels={"service": "worker"})
client.push("Job started")
client.push_batch([("Step 1", "info"), ("Step 2", "info")])
```

### `LokiHandler(url=None, labels=None, timeout=5, queue_size=1000, basic_auth=None)`

`logging.Handler` that enqueues records and sends them on a **daemon thread** (non-blocking `emit`). Call `handler.close()` before exit to flush and stop the worker.

| Parameter     | Default / source | Description |
|---------------|------------------|-------------|
| `url`         | `GRAFANA_CLOUD_URL` / package default | Loki host or push URL |
| `labels`      | `{}` | Static labels on every record |
| `timeout`     | `5` | HTTP timeout (seconds) |
| `queue_size`  | `1000` | Queue capacity; new records dropped when full |
| `basic_auth`  | `GRAFANA_CLOUD_USER` + write token from env | `(username, token)` tuple |

---

## Log levels

**`LokiHandler`** maps Python’s `LogRecord.levelname` to Loki label values: `DEBUG`→`debug`, `INFO`→`info`, `WARNING`→`warn`, `ERROR`→`error`, `CRITICAL`→`critical`.

For **`push` / `push_log` / `push_logs`**, you pass the string yourself; common choices: `debug`, `info`, `warn`, `error`, `critical`.

---

## Publish to PyPI

### CI (this repo)

[`.github/workflows/publish.yml`](.github/workflows/publish.yml): pushes to **TestPyPI** on `feature/**` and **PyPI** on `main`, using repository secrets `TEST_PYPI_API_TOKEN` and `PYPI_API_TOKEN` (user `__token__`). Bump **`version`** in `pyproject.toml` (and `__version__` in `__init__.py` if you keep them aligned) before each release — indexes reject re-uploading the same file.

### Manual release

1. Bump **`version`** in `pyproject.toml`.
2. Clean and build:

```bash
rm -rf dist/ build/ *.egg-info
python -m build
twine check dist/*
```

3. Upload:

```bash
twine upload --repository testpypi dist/*    # optional dry-run on Test PyPI
twine upload dist/*                          # production PyPI
```

Keep `dist/` and `*.egg-info/` out of git (see `.gitignore`). For OIDC instead of tokens, configure [trusted publishing](https://docs.pypi.org/trusted-publishers/) and drop password-based auth from the workflow.

---

## Editable local install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python test.py
```
