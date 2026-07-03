from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the service.",
    ["method", "path", "status_code"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_ms",
    "HTTP request duration in milliseconds.",
    ["method", "path"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
