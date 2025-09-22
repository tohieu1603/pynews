import logging
import time
from typing import Any, Dict

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("app")


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RequestLoggingMiddleware(MiddlewareMixin):
    """Capture incoming/outgoing HTTP requests for audit logging."""

    def process_request(self, request):
        request._log_start_ts = time.time()
        request._log_context: Dict[str, Any] = {
            "path": request.path,
            "method": request.method,
            "ip": _client_ip(request),
            "query_string": request.META.get("QUERY_STRING", ""),
            "user_id": getattr(request.user, "id", None) if hasattr(request, "user") and request.user.is_authenticated else None,
        }
        logger.info(
            "request_started",
            extra={
                "context": request._log_context,
                "channel": "web",
                "environment": getattr(settings, "APP_ENV", "local"),
            },
        )

    def process_response(self, request, response):
        if hasattr(request, "_log_context"):
            duration_ms = None
            if hasattr(request, "_log_start_ts"):
                duration_ms = round((time.time() - request._log_start_ts) * 1000, 2)
            context = request._log_context.copy()
            context.update(
                {
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "content_type": response.get("Content-Type"),
                }
            )
            logger.info(
                "request_finished",
                extra={
                    "context": context,
                    "channel": "web",
                    "environment": getattr(settings, "APP_ENV", "local"),
                },
            )
        return response

    def process_exception(self, request, exception):  # pragma: no cover - best effort logging
        context = getattr(request, "_log_context", {}).copy()
        context.update({"exception": repr(exception)})
        logger.error(
            "request_exception",
            extra={
                "context": context,
                "channel": "web",
                "environment": getattr(settings, "APP_ENV", "local"),
            },
        )
