import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def import_as_teacher(application):
    """
    Convert an approved TeacherApplication into a Teacher record.

    Creates or retrieves the Teacher, links to the high school,
    copies uploads, and creates course certificates based on
    accepted course statuses.

    Returns the Teacher instance.
    """
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
            new_file = TeacherUpload(
                teacher=teacher,
                media_type='Other',
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
