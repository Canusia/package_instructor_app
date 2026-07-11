"""
Tests for ApplicantCourseReviewer status-history tracking.

The faculty review page renders `get_status_history`, which reads
`status_changed_on`. The `course_reviewer_status_updated` pre_save signal is
what populates that field on each decision change — without it the
"Recommendation History" panel is always blank.

The other TeacherApplication / reviewer signals fire notification emails on
save, so we disconnect them here to isolate the history behaviour.
"""
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_save
from django.test import TestCase
from django.utils import timezone

from cis.models.customuser import CustomUser
from cis.models.course import Course, Cohort
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.models.applicant_school_course import ApplicantSchoolCourse
from instructor_app.instructor_app.models.applicant_course_reviewer import ApplicantCourseReviewer
from instructor_app.instructor_app.signals import teacher_applications as sig


# Email-sending signals to silence for these tests.
_NOISY = [
    (post_save, sig.assign_new_reviewer, ApplicantCourseReviewer),
    (post_save, sig.create_new_application, TeacherApplication),
    (pre_save, sig.teacher_app_status_updated, TeacherApplication),
    (post_save, sig.selected_new_course, ApplicantSchoolCourse),
]


class CourseReviewerStatusHistoryTests(TestCase):
    def setUp(self):
        for signal, receiver, sender in _NOISY:
            signal.disconnect(receiver, sender=sender)
        self.addCleanup(self._reconnect)

        Group.objects.get_or_create(name='applicant')
        applicant = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        reviewer = CustomUser.objects.create(username='r@x.com', email='r@x.com')
        app = TeacherApplication.objects.create(
            user=applicant, createdon=timezone.localdate())
        hs = HighSchool.objects.create(name='HS', status='Active')
        course = Course.objects.create(
            name='CMST 203', status='active', title='Comm', catalog_number='203',
            cohort=Cohort.objects.create(name='Comm', designator='CMST&'))
        asc = ApplicantSchoolCourse.objects.create(
            teacherapplication=app, course=course, highschool=hs, misc_info={})
        self.reviewer = ApplicantCourseReviewer.objects.create(
            application_course=asc, reviewer=reviewer)  # status defaults to '---'

    def _reconnect(self):
        for signal, receiver, sender in _NOISY:
            signal.connect(receiver, sender=sender)

    def test_placeholder_status_records_no_history(self):
        # Freshly created (status '---') — nothing logged, history stays blank.
        self.reviewer.refresh_from_db()
        self.assertFalse(self.reviewer.status_changed_on)
        self.assertEqual(self.reviewer.get_status_history, '-')

    def test_decision_records_history_entry(self):
        self.reviewer.status = 'Approved'
        self.reviewer.save()
        self.reviewer.refresh_from_db()
        self.assertTrue(self.reviewer.status_changed_on)
        self.assertIn('Approved', self.reviewer.status_changed_on.values())
        self.assertIn('Approved', self.reviewer.get_status_history)

    def test_new_decision_appends_without_dropping_prior_history(self):
        # Seed an earlier decision (distinct timestamp key), then record a new
        # one — the signal must append, not replace.
        self.reviewer.status_changed_on = {
            '01/01/2026 09:00:00 AM': 'Need more information'}
        self.reviewer.status = 'Approved'
        self.reviewer.save()
        self.reviewer.refresh_from_db()
        values = list(self.reviewer.status_changed_on.values())
        self.assertIn('Need more information', values)   # prior entry preserved
        self.assertIn('Approved', values)                # new entry appended
