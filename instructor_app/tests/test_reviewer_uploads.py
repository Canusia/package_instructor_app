"""Faculty reviewers see only uploads for the courses they review.

An applicant applying to several courses uploads documents per course
requirement; course A's reviewer must not see course B's material. Uploads not
tied to any requirement are shown separately as general material
(package_instructor_app#6).
"""
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.test import TestCase
from django.utils import timezone

from cis.models.course import Course, Cohort, CourseAppRequirement
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.models.applicant_course_reviewer import (
    ApplicantCourseReviewer,
)
from instructor_app.instructor_app.models.applicant_school_course import (
    ApplicantSchoolCourse,
)
from instructor_app.instructor_app.models.application_upload import ApplicationUpload
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.signals import teacher_applications as sig


def _course(catalog):
    return Course.objects.create(
        name=f'ENGL& {catalog}', status='active', title=f'T{catalog}',
        catalog_number=catalog,
        cohort=Cohort.objects.create(name=catalog, designator=f'C{catalog}&'))


class ReviewerUploadsTests(TestCase):
    def setUp(self):
        for receiver, sender in (
                (sig.create_new_application, TeacherApplication),
                (sig.selected_new_course, ApplicantSchoolCourse),
                (sig.assign_new_reviewer, ApplicantCourseReviewer)):
            post_save.disconnect(receiver, sender=sender)
            self.addCleanup(post_save.connect, receiver, sender=sender)

        Group.objects.get_or_create(name='applicant')
        applicant = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.reviewer_a = CustomUser.objects.create(username='ra@x.com', email='ra@x.com')
        self.reviewer_b = CustomUser.objects.create(username='rb@x.com', email='rb@x.com')
        self.app = TeacherApplication.objects.create(
            user=applicant, createdon=timezone.localdate())
        hs = HighSchool.objects.create(name='HS', status='Active')

        course_a, course_b = _course('101'), _course('201')
        req_a = CourseAppRequirement.objects.create(course=course_a, name='Transcript')
        req_b = CourseAppRequirement.objects.create(course=course_b, name='Portfolio')
        for course, reviewer in ((course_a, self.reviewer_a), (course_b, self.reviewer_b)):
            asc = ApplicantSchoolCourse.objects.create(
                teacherapplication=self.app, course=course, highschool=hs, misc_info={})
            ApplicantCourseReviewer.objects.create(application_course=asc, reviewer=reviewer)

        self.for_a = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[str(req_a.id)])
        self.for_b = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[str(req_b.id)])
        self.for_both = ApplicationUpload.objects.create(
            teacher_application=self.app,
            associated_with=[str(req_a.id), str(req_b.id)])
        self.general = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=None)
        self.general_empty = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[])

    def test_reviewer_sees_only_their_courses_uploads(self):
        course_uploads, _general = self.app.uploads_for_reviewer(self.reviewer_a)
        self.assertEqual(
            {u.id for u in course_uploads}, {self.for_a.id, self.for_both.id})

    def test_other_reviewer_sees_theirs(self):
        course_uploads, _general = self.app.uploads_for_reviewer(self.reviewer_b)
        self.assertEqual(
            {u.id for u in course_uploads}, {self.for_b.id, self.for_both.id})

    def test_unassociated_uploads_are_general(self):
        _course_uploads, general = self.app.uploads_for_reviewer(self.reviewer_a)
        self.assertEqual(
            {u.id for u in general}, {self.general.id, self.general_empty.id})

    def test_non_reviewer_sees_no_course_uploads(self):
        stranger = CustomUser.objects.create(username='s@x.com', email='s@x.com')
        course_uploads, _general = self.app.uploads_for_reviewer(stranger)
        self.assertEqual(list(course_uploads), [])
