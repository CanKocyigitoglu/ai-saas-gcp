import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


HTTP_REQUESTS_TOTAL = Counter(
    "ai_saas_http_requests_total",
    "Total number of HTTP requests handled by the AI SaaS API.",
    ["method", "endpoint", "http_status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "ai_saas_http_request_duration_seconds",
    "HTTP request duration in seconds for the AI SaaS API.",
    ["method", "endpoint"],
)

HTTP_EXCEPTIONS_TOTAL = Counter(
    "ai_saas_http_exceptions_total",
    "Total number of unhandled HTTP exceptions in the AI SaaS API.",
    ["method", "endpoint"],
)


def _get_endpoint_name(request: Request) -> str:
    route = request.scope.get("route")

    if route is not None and getattr(route, "path", None):
        return route.path

    return request.url.path


def setup_metrics(app: FastAPI) -> None:
    """
    Adds Prometheus-compatible metrics middleware and /metrics endpoint.
    /metrics is intentionally left public for Prometheus scraping.
    """

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception:
            endpoint = _get_endpoint_name(request)
            HTTP_EXCEPTIONS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
            ).inc()
            raise

        finally:
            endpoint = _get_endpoint_name(request)
            duration = time.perf_counter() - start_time

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                http_status=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
