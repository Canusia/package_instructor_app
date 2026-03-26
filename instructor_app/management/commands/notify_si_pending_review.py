"""
Management command: notify_si_pending_review
=============================================

Sends reminder emails to faculty reviewers who have been assigned to a course
application but have not yet submitted a review (status '---').

Core logic lives in:
    instructor_app/services/pending_review_notifications.py

Usage
-----
Normal run (scheduled via cron):
    python manage.py notify_si_pending_review -t "2026-03-26 08:00:00"

Dry run (prints who would be notified, sends nothing):
    python manage.py notify_si_pending_review --dry-run
    python manage.py notify_si_pending_review -t "2026-03-26 08:00:00" --dry-run

The -t / --time argument is required for cron signal logging. When omitted
it defaults to the current time.
"""

import json
from datetime import datetime

from django.core.management.base import BaseCommand

from cis.signals.crontab import cron_task_done, cron_task_started

from ...services.pending_review_notifications import (
    get_pending_review_notifications,
    send_pending_review_notifications,
)


class Command(BaseCommand):

    help = 'Remind faculty reviewers with outstanding course application reviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '-t', '--time',
            type=str,
            default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            help='Scheduled time of run (default: now). Format: "YYYY-MM-DD HH:MM:SS"',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print who would be notified without sending emails or saving notes.',
        )

    def handle(self, *args, **kwargs):
        time = kwargs['time']
        dry_run = kwargs['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no emails will be sent.\n'))

        cron_task_started.send(
            sender=self.__class__,
            task=self.__class__,
            scheduled_time=time,
        )

        pending = get_pending_review_notifications()

        if not pending:
            summary = 'No pending reviewer notifications'
            self.stdout.write(summary)
            cron_task_done.send(
                sender=self.__class__,
                task=self.__class__,
                scheduled_time=time,
                summary=summary,
                detailed_log=json.dumps({}),
            )
            return

        if dry_run:
            for entry in pending:
                self.stdout.write(
                    f'  Would notify: {entry["reviewer_name"]} <{entry["reviewer_email"]}>\n'
                    f'  Course: {entry["course"]}  |  Applicant: {entry["teacher_name"]}\n'
                    f'  Assigned on: {entry["assigned_on"]}\n'
                )
            summary = f'[DRY RUN] {len(pending)} notification(s) would be sent'
            self.stdout.write(self.style.SUCCESS(summary))
            cron_task_done.send(
                sender=self.__class__,
                task=self.__class__,
                scheduled_time=time,
                summary=summary,
                detailed_log=json.dumps({}),
            )
            return

        result = send_pending_review_notifications(pending)

        summary = f'{result["sent"]} notification(s) sent'
        self.stdout.write(self.style.SUCCESS(summary))

        cron_task_done.send(
            sender=self.__class__,
            task=self.__class__,
            scheduled_time=time,
            summary=summary,
            detailed_log=json.dumps(result['detail']),
        )
