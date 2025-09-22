import logging
from typing import Any, Dict
import json
import threading

from django.apps import apps
from django.conf import settings
from django.db import DatabaseError, connection
from django.utils import timezone


class DatabaseLogHandler(logging.Handler):
    """Logging handler that persists records to the `logs` table."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - side-effect only
        def _emit_sync():
            try:
                context: Dict[str, Any] = getattr(record, "context", {}) or {}
                extra_data: Dict[str, Any] = getattr(record, "extra_data", {}) or {}
                environment: str | None = getattr(record, "environment", None) or getattr(settings, "APP_ENV", "local")

                # Sử dụng raw SQL để tránh async issues
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO logs (level, channel, message, context, extra, environment, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [
                        record.levelname.lower(),
                        getattr(record, "channel", record.name),
                        self.format(record),
                        json.dumps(context),
                        json.dumps(extra_data),
                        environment,
                        timezone.now()
                    ])
            except DatabaseError:
                # Table không sẵn sàng, bỏ qua để tránh crash dev server
                return
            except Exception:  # pragma: no cover - never raise from logging
                self.handleError(record)
        
        # Chạy trong thread để tránh async context issues
        thread = threading.Thread(target=_emit_sync)
        thread.daemon = True
        thread.start()
