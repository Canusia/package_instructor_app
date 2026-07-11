"""
Data migration: backfill ApplicantCourseReviewer.status_changed_on for reviews
that already carry a decision but were saved before the status-history signal
existed (so the faculty "Recommendation History" panel rendered blank).

For each reviewer with a real decision (status != '---') and empty
status_changed_on, seed one history entry keyed by the review date
(misc_info['reviewed_on'] if present, else assigned_on) -> current status.

Forwards is idempotent (skips rows that already have history). Reverse is a
no-op — we cannot distinguish backfilled entries from genuine ones.
"""
from django.db import migrations


PLACEHOLDER_STATUS = "---"


def backfill_status_history(apps, schema_editor):
    ApplicantCourseReviewer = apps.get_model(
        "instructor_app", "ApplicantCourseReviewer")

    for reviewer in ApplicantCourseReviewer.objects.all():
        if reviewer.status in (None, "", PLACEHOLDER_STATUS):
            continue
        if reviewer.status_changed_on:
            continue

        misc = reviewer.misc_info or {}
        when = misc.get("reviewed_on")
        if not when and reviewer.assigned_on:
            when = reviewer.assigned_on.strftime("%m/%d/%Y")
        if not when:
            continue

        reviewer.status_changed_on = {when: reviewer.status}
        reviewer.save(update_fields=["status_changed_on"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("instructor_app", "0006_teacherapplicant_meta"),
    ]

    operations = [
        migrations.RunPython(backfill_status_history, noop_reverse),
    ]
