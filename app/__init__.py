from .config import (
    ENV_GRAFANA_CLOUD_API_KEY,
    basic_auth_from_env,
    load_dotenv,
    loki_token_from_env,
    loki_url_from_env,
    loki_user_from_env,
    push_endpoint,
)
from .handler import LokiHandler
from .client import LokiClient, configure, push_log, push_logs
from .log_config import (
    JsonLogFormatter,
    setup_central_logging,
    shutdown_central_logging,
)

# Backward-compatible names (async-only API)
AsyncLokiClient = LokiClient
configure_async = configure
push_log_async = push_log
push_logs_async = push_logs

__all__ = [
    "LokiHandler",
    "LokiClient",
    "AsyncLokiClient",
    "configure",
    "configure_async",
    "push_log",
    "push_log_async",
    "push_logs",
    "push_logs_async",
    "JsonLogFormatter",
    "setup_central_logging",
    "shutdown_central_logging",
    "load_dotenv",
    "loki_url_from_env",
    "loki_user_from_env",
    "loki_token_from_env",
    "basic_auth_from_env",
    "push_endpoint",
    "ENV_GRAFANA_CLOUD_API_KEY",
]
__version__ = "0.2.0"
