"""
Who may start an instructor application against an account that already exists.

The public start page used to dead-end on any known email. It now lets some
existing users through, creating a TeacherApplicant against their account
instead of a new CustomUser.

Rules:
  * student / instructor / highschool_admin may apply.
  * ce (staff) and faculty may not.
  * A user holding an eligible role AND a denied one may apply — allow-wins.
    Holding an eligible role is what counts; a denied role only blocks when
    the user has no eligible role at all.
  * A user with no groups at all may apply. These should not exist, and
    letting them through leaves them with the applicant role, which is the
    outcome we want anyway.
  * Someone who already holds the applicant role is not eligible via this
    path — they are an applicant already and get routed to login / password
    reset instead.

The allowlist lives here rather than inline at the call site because the
CE-side create-on-behalf flow needs the same rule.
"""
import logging

logger = logging.getLogger(__name__)

ELIGIBLE_ROLES = frozenset({'student', 'instructor', 'highschool_admin'})

APPLICANT_ROLE = 'applicant'


def role_names(user):
    """The user's group names as a set."""
    return set(user.groups.values_list('name', flat=True))


def is_existing_applicant(user):
    """True when the user already holds the applicant role."""
    return APPLICANT_ROLE in role_names(user)


def existing_user_may_apply(user):
    """
    True when this already-registered user is allowed to start an application.

    See the module docstring for the rules.
    """
    names = role_names(user)

    if APPLICANT_ROLE in names:
        return False

    if not names:
        return True

    return bool(names & ELIGIBLE_ROLES)
