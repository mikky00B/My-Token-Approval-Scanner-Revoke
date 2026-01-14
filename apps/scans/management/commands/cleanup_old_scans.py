"""
Management command to cleanup old scan data.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.scans.models import WalletScan


class Command(BaseCommand):
    help = "Cleanup old scan data to save space"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete scans older than this many days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        cutoff_date = timezone.now() - timedelta(days=days)

        # Find old scans
        old_scans = WalletScan.objects.filter(started_at__lt=cutoff_date)
        count = old_scans.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"No scans older than {days} days found")
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} scans older than {days} days"
                )
            )
            return

        # Delete
        old_scans.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {count} scans older than {days} days"
            )
        )
