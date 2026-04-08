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
