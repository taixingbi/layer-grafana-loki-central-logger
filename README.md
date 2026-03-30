# tb-loki-central-logger

Send Python logs to **Grafana Loki** with **no third-party dependencies** (stdlib only): an async `logging.Handler`, plus `push_log()` / `LokiClient` for direct pushes.

Requires **Python 3.10+**.

## Install

```bash
pip install tb-loki-central-logger
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
| `GRAFANA_CLOUD_USER` | Basic-auth username: stack / tenant id |
| `GRAFANA_CLOUD_WRITE_API_KEY` | Basic-auth password: Loki **write** API token |
| `GRAFANA_CLOUD_API_KEY` | Legacy alias for the write token |

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
