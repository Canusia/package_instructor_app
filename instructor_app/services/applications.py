"""
Creating (or resuming) the TeacherApplication that a signup lands on.

This used to live inline at the end of complete_signup. Both onboarding tails
need it now — the brand-new-user tail and the existing-user tail — so it lives
here.
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)

# An application in one of these states is finished. The main way a user ends
# up with a retained application and no applicant role is Import as Instructor
# (views/ce/detail.py -> TeacherApplication.remove_role()), which deliberately
# keeps the application as the record of how they became an instructor. Resuming
# that would hand a returning applicant their old, already-decided application,
# so a terminal application means start fresh.
TERMINAL_STATUSES = frozenset({'Decision Made', 'Withdrawn', 'Closed'})


def start_or_resume_application(user):
    """
    Return the TeacherApplication the user should be working on.

    Resumes their most recent application when it is still live; otherwise
    creates a new one.
    """
    from ..models.teacher_applicant import TeacherApplication

    existing = TeacherApplication.objects.filter(
        user=user
    ).order_by('-createdon').first()

    if existing is not None and existing.status not in TERMINAL_STATUSES:
        logger.info(
            'Resuming application %s for user %s', existing.pk, user.pk
        )
        return existing

    return TeacherApplication.objects.create(
        user=user,
        createdon=date.today(),
        misc_info={},
    )
