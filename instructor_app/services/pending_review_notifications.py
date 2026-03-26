"""
Service: pending_review_notifications
======================================

Core logic for identifying and notifying faculty reviewers who have been
assigned to a course application but have not yet submitted a review
(status '---').

Public API
----------
get_pending_review_notifications() -> list[dict]
    Returns a list of pending-notification dicts, one per qualifying
    ApplicantCourseReviewer record (one per unique application_course,
    oldest assignment first):

        {
            'reviewer':            <ApplicantCourseReviewer>,
            'reviewer_name':       'First Last',
            'reviewer_email':      'reviewer@example.com',
            'course':              <Course>,
            'teacher_application': <TeacherApplication>,
            'teacher_name':        'First Last',
            'assigned_on':         <date>,
        }

    No side effects — safe to call for preview/report purposes.

send_pending_review_notifications(pending) -> dict
    Takes the list returned by get_pending_review_notifications(), sends
    reminder emails via notify_reviewer(), and saves a private note per
    application.  Returns a summary dict:

        {
            'sent': 3,
            'detail': { '<reviewer_id>': {'reviewer': '...', 'course': '...', 'teacher': '...'}, ... }
        }
"""

import logging

from cis.models.customuser import CustomUser
from cis.models.note import TeacherApplicationNote

from ..models.teacher_applicant import ApplicantCourseReviewer

logger = logging.getLogger(__name__)


def get_pending_review_notifications():
    """
    Return reviewers with an outstanding (status='---') course assignment.

    One record per unique application_course, ordered by oldest assignment.
    No side effects.
    """
    reviewers = (
        ApplicantCourseReviewer.objects
        .filter(status__iexact='---')
        .select_related(
            'reviewer',
            'application_course__course',
            'application_course__teacherapplication__user',
        )
        .order_by('application_course', 'assigned_on')
        .distinct('application_course')
    )

    pending = []
    for r in reviewers:
        ta = r.application_course.teacherapplication
        pending.append({
            'reviewer':            r,
            'reviewer_name':       f'{r.reviewer.first_name} {r.reviewer.last_name}',
            'reviewer_email':      r.reviewer.email,
            'course':              r.application_course.course,
            'teacher_application': ta,
            'teacher_name':        f'{ta.user.first_name} {ta.user.last_name}',
            'assigned_on':         r.assigned_on,
        })

    return pending


def send_pending_review_notifications(pending):
    """
    Send review reminder emails for the list returned by
    get_pending_review_notifications().

    Calls notify_reviewer() on each record and saves a private
    TeacherApplicationNote.  Returns a summary dict.
    """
    cron_user = CustomUser.objects.get(username='cron')

    sent = 0
    detail = {}

    for entry in pending:
        r = entry['reviewer']
        try:
            r.notify_reviewer()
        except Exception as e:
            logger.error('Failed to notify reviewer %s for application %s: %s', r.reviewer_id, r.application_course.teacherapplication_id, e)
            continue

        TeacherApplicationNote(
            teacher_application_id=r.application_course.teacherapplication_id,
            note=f'Sent {r.reviewer.first_name} {r.reviewer.last_name} reminder email',
            createdby=cron_user,
            meta={'type': 'Private'},
        ).save()

        detail[str(r.id)] = {
            'reviewer': entry['reviewer_name'],
            'reviewer_email': entry['reviewer_email'],
            'course': str(entry['course']),
            'teacher': entry['teacher_name'],
            'assigned_on': str(entry['assigned_on']),
        }
        sent += 1

    return {'sent': sent, 'detail': detail}
