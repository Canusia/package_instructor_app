import logging

from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)


def has_remaining_applications(user):
    """
    True while the user still has at least one TeacherApplication.
    """
    from ..models.teacher_applicant import TeacherApplication

    return TeacherApplication.objects.filter(user=user).exists()


def revoke_applicant_access(user):
    """
    Drop the applicant role and record once the user's last application is gone.

    No-op while any TeacherApplication remains — this check is the guard against
    a stale browser tab or a hand-crafted request stripping the role from
    someone with an open application, so callers must not skip it.

    Never touches any other role, and never deletes the user account.

    Returns True if the role was revoked.
    """
    from ..models.teacher_applicant import TeacherApplicant

    if has_remaining_applications(user):
        return False

    try:
        user.groups.remove(Group.objects.get(name='applicant'))
    except Group.DoesNotExist:
        logger.warning('applicant group missing; run init_groups')

    TeacherApplicant.objects.filter(user=user).delete()

    logger.info('Revoked applicant role for user %s', user.pk)
    return True
