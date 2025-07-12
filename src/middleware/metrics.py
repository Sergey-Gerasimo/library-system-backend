from fastapi.responses import PlainTextResponse
from fastapi import Request
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
)
import time
import re
from config.settings import app_settings

app_name = app_settings.APP_NAME

REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Number of requests currently being processed",
    ["app_name", "path", "method"],
)

REQUEST_COUNTER = Counter(
    "fastapi_requests_total", "Total count of requests", ["method", "path", "app_name"]
)

REQUEST_LATENCY = Histogram(
    "fastapi_request_latency_seconds", "Request latency in seconds", ["method", "path"]
)

RESPONSES_TOTAL = Counter(
    "fastapi_responses_total",
    "Total HTTP responses by status code and path",
    ["app_name", "status_code", "path", "method"],
)

REQUEST_TIME = Histogram(
    "fastapi_request_duration_seconds",
    "Request duration in seconds by method and path",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],  # Кастомизируем бакеты (опционально)
)

EXCEPTIONS_COUNTER = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised",
    ["app_name", "exception_type", "path"],
    registry=CollectorRegistry(),
)

REQUEST_DURATION = Histogram(
    "fastapi_requests_duration_seconds",
    "Request duration distribution in seconds",
    ["app_name", "path", "method"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
    ],  # Стандартные бакеты
)


def normalize_path(path: str) -> str:
    """Нормализует пути с динамическими параметрами для метрик"""
    # Обрабатываем пути для книг
    path = re.sub(r"/book/[^/]+/pdf", "/book/{book_id}/pdf", path)
    path = re.sub(r"/book/[^/]+/cover", "/book/{book_id}/cover", path)

    # Общие случаи (можно добавить другие шаблоны)
    path = re.sub(r"/\d+", "/{id}", path)  # Числовые ID
    path = re.sub(r"/[a-f0-9]{24}", "/{hex_id}", path)  # MongoDB-like ID
    return path


async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = normalize_path(request.url.path)

    REQUEST_COUNTER.labels(method=method, path=path, app_name=app_name).inc()
    REQUESTS_IN_PROGRESS.labels(app_name=app_name, path=path, method=method).inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        elapsed_time = time.time() - start_time

        EXCEPTIONS_COUNTER.labels(
            app_name=app_name, exception_type=type(e).__name__, path=path
        ).inc()
        REQUEST_TIME.labels(method=method, path=path).observe(elapsed_time)

        raise e

    elapsed_time = time.time() - start_time
    REQUESTS_IN_PROGRESS.labels(app_name=app_name, path=path, method=method).dec()
    RESPONSES_TOTAL.labels(
        app_name=app_name,
        status_code=response.status_code,
        path=path,
        method=request.method,
    ).inc()
    REQUEST_LATENCY.labels(method, path).observe(elapsed_time)
    REQUEST_TIME.labels(method=method, path=path).observe(elapsed_time)
    REQUEST_DURATION.labels(
        app_name=app_name, path=path, method=request.method
    ).observe(elapsed_time)

    return response
