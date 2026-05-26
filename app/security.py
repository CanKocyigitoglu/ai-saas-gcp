import os
import time
from collections import defaultdict, deque
from typing import Iterable

from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


PUBLIC_PATHS = {
    "/health",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def _split_csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def get_max_request_bytes() -> int:
    return int(os.getenv("MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))


def get_rate_limit_requests() -> int:
    return int(os.getenv("RATE_LIMIT_REQUESTS", "120"))


def get_rate_limit_window_seconds() -> int:
    return int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def get_allowed_image_content_types() -> set[str]:
    values = _split_csv_env(
        "ALLOWED_IMAGE_CONTENT_TYPES",
        "image/jpeg,image/png,image/webp",
    )
    return set(values)


def validate_image_content_type(content_type: str | None) -> None:
    allowed_types = get_allowed_image_content_types()

    if content_type is None or content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file must be one of: {', '.join(sorted(allowed_types))}.",
        )


def validate_upload_size(size_bytes: int) -> None:
    max_bytes = get_max_request_bytes()

    if size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Uploaded file is too large. Maximum allowed size is {max_bytes} bytes.",
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )

        return response


class RequestSizeAndRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests_by_client: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                request_size = int(content_length)
            except ValueError:
                request_size = 0

            max_bytes = get_max_request_bytes()

            if request_size > max_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={
                        "detail": f"Request body is too large. Maximum allowed size is {max_bytes} bytes."
                    },
                )

        if request.url.path not in PUBLIC_PATHS:
            limit = get_rate_limit_requests()

            if limit > 0:
                window_seconds = get_rate_limit_window_seconds()
                client_host = request.client.host if request.client else "unknown"
                key = f"{client_host}:{request.url.path}"
                now = time.time()

                request_times = self.requests_by_client[key]

                while request_times and now - request_times[0] > window_seconds:
                    request_times.popleft()

                if len(request_times) >= limit:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded. Please try again later."
                        },
                    )

                request_times.append(now)

        return await call_next(request)


def setup_security(app) -> None:
    allowed_hosts = _split_csv_env(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,api,testserver",
    )

    allowed_origins = _split_csv_env(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeAndRateLimitMiddleware)
