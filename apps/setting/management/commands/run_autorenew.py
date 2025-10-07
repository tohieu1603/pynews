"""
Django management command to process auto-renew subscriptions.

Usage:
    python manage.py run_autorenew [--limit 50] [--verbose]

Setup cronjob:
    */5 * * * * cd /path/to/project && python manage.py run_autorenew >> /var/log/autorenew.log 2>&1
"""

import logging
from django.core.management.base import BaseCommand
from apps.setting.services.subscription_service import SymbolAutoRenewService

logger = logging.getLogger("app.autorenew")


class Command(BaseCommand):
    help = "Process auto-renew subscriptions that are due for billing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum number of subscriptions to process in one run (default: 50)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        verbose = options["verbose"]

        if verbose:
            self.stdout.write(f"Starting auto-renew processing (limit={limit})...")

        service = SymbolAutoRenewService()

        try:
            result = service.run_due_subscriptions(limit=limit)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Processed: {result['processed']} | "
                    f"Success: {result['success']} | "
                    f"Failed: {result['failed']} | "
                    f"Skipped: {result['skipped']}"
                )
            )

            if verbose:
                logger.info(f"Auto-renew batch complete: {result}")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error processing auto-renew: {e}")
            )
            logger.exception("Auto-renew batch failed")
            raise
