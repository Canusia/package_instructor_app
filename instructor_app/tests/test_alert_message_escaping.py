"""User text is escaped in the alert HTML (package-cis#122 port)."""
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.test import TestCase
from django.utils import timezone

from alerts.models import Alert
from cis.models.course import Course, Cohort
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.models import applicant_course_reviewer as acr_mod
from instructor_app.instructor_app.models import teacher_application as ta_mod
from instructor_app.instructor_app.models.applicant_course_reviewer import (
    ApplicantCourseReviewer,
)
from instructor_app.instructor_app.models.applicant_school_course import (
    ApplicantSchoolCourse,
)
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.models.teacher_application_note import (
    TeacherApplicationNote,
)
from instructor_app.instructor_app.signals import teacher_applications as sig

XSS = '<script>alert(1)</script>'


class AlertEscapingTests(TestCase):
    def setUp(self):
        for receiver, sender in (
                (sig.create_new_application, TeacherApplication),
                (sig.selected_new_course, ApplicantSchoolCourse),
                (sig.assign_new_reviewer, ApplicantCourseReviewer)):
            post_save.disconnect(receiver, sender=sender)
            self.addCleanup(post_save.connect, receiver, sender=sender)
        Group.objects.get_or_create(name='applicant')
        self.admin = CustomUser.objects.create(username='adm@x.com', email='adm@x.com')
        self.reviewer = CustomUser.objects.create(
            username='rev@x.com', email='rev@x.com', first_name=XSS)
        self.hs = HighSchool.objects.create(name='HS', status='Active')
        self.app = TeacherApplication.objects.create(
            user=CustomUser.objects.create(
                username='a@x.com', email='a@x.com', first_name=XSS),
            createdon=timezone.localdate(), misc_info={}, highschool=self.hs)
        course = Course.objects.create(
            name='ENGL& 101', status='active', title='T101', catalog_number='101',
            cohort=Cohort.objects.create(name='c', designator='C&'))
        self.asc = ApplicantSchoolCourse.objects.create(
            teacherapplication=self.app, course=course,
            highschool=self.hs,
            misc_info={})
        self.admins = mock.patch.object(
            Course, 'get_administrators',
            return_value=[SimpleNamespace(user=self.admin)])
        self.admins.start()
        self.addCleanup(self.admins.stop)

    def _assert_escaped(self, alert_type):
        message = Alert.objects.get(alert_type=alert_type).message
        self.assertNotIn('<script>', message)
        self.assertIn('&lt;script&gt;', message)

    def test_submitted_alert_escapes_applicant_name(self):
        settings_obj = mock.Mock()
        settings_obj.from_db.return_value = {'internal_notify_on': ['app_submitted'], 'app_submitted_email': 't'}
        lang = mock.Mock()
        lang.from_db.return_value = {}
        with mock.patch(
                'instructor_app.instructor_app.settings.teacher_application_email.'
                'teacher_application_email', settings_obj), \
                mock.patch(
                    'instructor_app.instructor_app.settings.inst_app_language.'
                    'inst_app_language', lang), \
                mock.patch.object(ta_mod, 'send_notification'):
            self.app.notify_status_change('Submitted')
        self._assert_escaped('new_si_application_submitted')

    def test_reviewed_alert_escapes_names(self):
        row = ApplicantCourseReviewer.objects.create(
            application_course=self.asc, reviewer=self.reviewer)
        settings_obj = mock.Mock()
        settings_obj.from_db.return_value = {'course_reviewed_email': 't'}
        with mock.patch(
                'instructor_app.instructor_app.settings.teacher_application_email.'
                'teacher_application_email', settings_obj), \
                mock.patch.object(acr_mod, 'send_notification'):
            row.misc_info = {}
            row.notify_status_change('Approved')
        self._assert_escaped('si_application_reviewed')

    def test_note_response_alert_escapes_author_and_closes_anchor(self):
        author = CustomUser.objects.create(
            username='au@x.com', email='au@x.com', first_name=XSS)
        parent = TeacherApplicationNote.objects.create(
            teacher_application=self.app, note='p', createdby=self.admin,
            meta={'type': 'to_instructor'})
        TeacherApplicationNote.objects.create(
            teacher_application=self.app, note='r', createdby=author,
            parent=str(parent.id), meta={'type': 'response'})
        self._assert_escaped('si_app_note_response')
        self.assertTrue(Alert.objects.get(
            alert_type='si_app_note_response').message.endswith('</a>'))
