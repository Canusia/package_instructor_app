"""Copy application notes from the host's cis table into instructor_app's (#11).

    python manage.py copy_legacy_application_notes [--dry-run]

Safe to run more than once; does nothing on tenants whose cis note table does
not reference instructor_app applications.
"""
from django.core.management.base import BaseCommand

from ...services.legacy_notes import copy_legacy_notes, legacy_note_model


class Command(BaseCommand):
    help = "Copy cis.TeacherApplicationNote rows into instructor_app's note table."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be copied without writing.')

    def handle(self, *args, **options):
        if legacy_note_model() is None:
            self.stdout.write('No legacy application notes on this tenant; nothing to copy.')
            return
        copied, present, skipped = copy_legacy_notes(dry_run=options['dry_run'])
        verb = 'Would copy' if options['dry_run'] else 'Copied'
        self.stdout.write(
            f'{verb} {copied} note(s); {present} already present; '
            f'{skipped} skipped (no application).')
