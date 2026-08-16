"""Which courses an applicant may select, and which campuses to offer.

One rule, in one place: a course is selectable when it is active, is not
explicitly marked unavailable to new instructors, and either sits on the
selected campus or has no campus at all (an unset campus means "all
campuses").
"""
from django.db.models import Q

from cis.models.course import Campus, Course

# CE forms write cis.utils.YES_NO_SELECT_OPTIONS ('' / '1' / '2'). The SIS
# importer writes cis/management/commands/import_courses.py's raw `isopen`
# value instead — a CSV string or a bool — and Course.add_or_update replaces
# meta wholesale, so both vocabularies occur in the wild. Treat every "no"
# spelling as No; anything unset stays available.
AVAILABLE_FOR_SI_NO = ('2', '0', False, 'false', 'False')


def _not_explicitly_unavailable():
    """Match every course except those explicitly marked No.

    The isnull clause is load-bearing and must not be "simplified" away:
    `available_for_si` is absent on most rows, so a bare
    `exclude(meta__available_for_si__in=AVAILABLE_FOR_SI_NO)` compares
    against SQL NULL and silently drops those rows instead of keeping them.
    Measured on live data that exclusion returned 11 of 101 active courses.
    `~Q(...__in=...)` gets the same negation/NULL-guard treatment from Django
    as `~Q(...=...)`, so this NULL rescue still applies — confirmed against
    live data (101 active courses both before and after this rule).
    """
    return (
        ~Q(meta__available_for_si__in=AVAILABLE_FOR_SI_NO)
        | Q(meta__available_for_si__isnull=True)
    )


def selectable_courses(campus=None):
    """Active, not-refused courses, optionally scoped to a campus.

    Passing a campus also keeps courses with no campus, which are offered
    everywhere. Passing None applies no campus filter at all.
    """
    qs = Course.objects.filter(status__iexact='active').filter(
        _not_explicitly_unavailable()
    )
    if campus is not None:
        qs = qs.filter(Q(campus=campus) | Q(campus__isnull=True))
    return qs


def campuses_with_selectable_courses():
    """Campuses holding at least one selectable course, ordered by name.

    Deliberately independent of any one applicant's progress, so a campus does
    not disappear from the dropdown once its last course has been added.
    """
    campus_ids = (
        selectable_courses()
        .exclude(campus__isnull=True)
        .values_list('campus', flat=True)
        .distinct()
    )
    return Campus.objects.filter(id__in=campus_ids).order_by('name')
