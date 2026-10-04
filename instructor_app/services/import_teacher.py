import logging
import re
from datetime import datetime

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def media_type_for_requirements(requirement_names):
    """Pick the TeacherUpload media type for an upload's requirement names.

    A media type matches a name when it appears in it as a whole word,
    ignoring case and a trailing "s" ("Official Transcripts" -> Transcript).
    Returns "Other" when nothing matches or the names point at different types.
    """
    from cis.models.teacher import TeacherUpload

    media_types = [
        value for value, _label in TeacherUpload._meta.get_field('media_type').choices
        if value != 'Other'
    ]

    matched = set()
    for name in requirement_names:
        for media_type in media_types:
            if re.search(rf'\b{re.escape(media_type)}s?\b', name, re.IGNORECASE):
                matched.add(media_type)

    return matched.pop() if len(matched) == 1 else 'Other'


def upload_description(requirements):
    """Describe a copied upload by the requirement(s) and course(s) it was for."""
    if not requirements:
        return 'Application upload'
    parts = [
        f'{req.name} ({req.course.name})' if req.course else req.name
        for req in requirements
    ]
    return 'Application upload for: ' + '; '.join(parts)


def import_as_teacher(application):
    """
    Convert an approved TeacherApplication into a Teacher record.

    Creates or retrieves the Teacher, links to the high school,
    copies uploads, and creates course certificates based on
    accepted course statuses.

    Returns the Teacher instance.
    """
    from cis.models.course import CourseAppRequirement
    from cis.models.teacher import (
        Teacher, TeacherHighSchool, TeacherCourseCertificate, TeacherUpload
    )
    from ..models.applicant_school_course import ApplicantSchoolCourse
    from ..models.application_upload import ApplicationUpload

    user = application.user

    try:
        letter_sent_on = datetime.strptime(
            application.misc_info['decision_letter_sent_on'],
            '%m/%d/%Y'
        )
    except:
        letter_sent_on = datetime.now()

    try:
        teacher = Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        user.secondary_email = user.email
        user.save()

        teacher = Teacher(user=user)
        teacher.save()

    # add teacher to high school
    try:
        ht_hs = TeacherHighSchool(
            teacher=teacher,
            highschool=application.highschool
        )
        ht_hs.save()
    except Exception as e:
        ht_hs = TeacherHighSchool.objects.get(
            teacher=teacher,
            highschool=application.highschool
        )

    # copy uploads
    try:
        uploads = ApplicationUpload.objects.filter(
            teacher_application=application
        )

        for upload in uploads:
            try:
                requirements = list(CourseAppRequirement.objects.filter(
                    id__in=upload.associated_with or []
                ).select_related('course').order_by('course__name', 'name'))
            except (ValidationError, TypeError):
                # A malformed id must not stop the remaining uploads copying.
                requirements = []
            new_file = TeacherUpload(
                teacher=teacher,
                media_type=media_type_for_requirements(
                    [req.name for req in requirements]),
                description=upload_description(requirements),
                media=upload.upload
            )
            new_file.save()
    except Exception as e:
        print(e)

    # add course to teacher
    courses = ApplicantSchoolCourse.objects.filter(
        teacherapplication=application
    )

    for course in courses:
        ht_course = TeacherCourseCertificate(
            teacher_highschool=ht_hs,
            course=course.course
        )

        letter_sent_on = datetime.strptime(
            application.misc_info['decision_letter_sent_on'],
            '%m/%d/%Y'
        )

        if course.status == 'Accepted':
            cert_status = 'Teaching'
            ht_course.approved_to_teach = letter_sent_on
        elif course.status == 'Accepted Provisional':
            cert_status = 'Teaching Provisional'
            ht_course.approved_to_provisionally_teach = letter_sent_on
        elif course.status == 'Accepted Substitute':
            cert_status = 'Teaching Substitute'
            ht_course.approved_to_provisionally_teach = letter_sent_on
        else:
            continue

        ht_course.status = cert_status
        ht_course.since = datetime.now()
        try:
            ht_course.save()
        except Exception as e:
            print(e)
            pass

    return teacher
