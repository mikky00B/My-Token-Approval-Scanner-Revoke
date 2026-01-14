"""
Management command to seed blacklist with known malicious addresses.
Save this as: apps/blacklists/management/commands/seed_blacklist.py
"""

from django.core.management.base import BaseCommand
from apps.blacklists.models import BlacklistEntry, BlacklistCategory


class Command(BaseCommand):
    help = "Seeds blacklist with known malicious addresses"

    def handle(self, *args, **options):
        # Known drainer addresses (examples - add more as discovered)
        entries = [
            {
                "address": "0x0000000000000000000000000000000000000001",
                "category": BlacklistCategory.DRAINER,
                "severity": 50,
                "name": "Test Drainer 1",
                "source": "Manual",
                "notes": "Test entry for development",
            },
            # Add real drainer addresses here as you discover them
        ]

        created_count = 0
        for entry_data in entries:
            entry, created = BlacklistEntry.objects.get_or_create(
                address=entry_data["address"], defaults=entry_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {entry.address}"))

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new blacklist entries")
        )
