"""
Finding 3: models/teacher_application.py's `submitted` branch built its
internal-notification context dict with `self.highschool.name` unguarded,
while `highschool` is `null=True`. Ordering made this applicant-visible: the
new applicant confirmation send happens first, then the unguarded
AttributeError propagates out of the pre_save signal handler and the status
is never persisted.

Covers both the null-highschool path (must not raise, applicant email must
still go out) and the populated-highschool path (school name must reach the
rendered internal notification body) -- the existing suite only ever left
highschool as None, so that path was unexercised.
"""
from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from mailer.models import Message

from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from cis.models.settings import Setting
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplication,
)

LANGUAGE_SETTINGS = {
    'applicant_submitted_email_active': 'Yes',
    'applicant_submitted_email_subject': 'We received your application',
    'applicant_submitted_email': (
        '<p>Dear {{teacher_first_name}}, school: {{highschool}}.</p>'
    ),
}

APPLICATION_EMAIL_SETTINGS = {
    'new_applicant_email_subject': 'Application started',
    'new_applicant_email': '<p>Welcome</p>',
    'internal_notify_on': ['app_submitted'],
    'course_selected_email_recipient': 'staff@example.com',
    'app_submitted_email_subject': 'Internal: submitted',
    'app_submitted_email': '<p>School: {{highschool}}</p>',
}


class SubmittedNotificationHighschoolGuardTests(TestCase):
    def setUp(self):
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': dict(APPLICATION_EMAIL_SETTINGS)})
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': dict(LANGUAGE_SETTINGS)})
        Group.objects.get_or_create(name='applicant')

    def _user(self, email):
        return CustomUser.objects.create(
            username=email, email=email, first_name='Ada', last_name='Lovelace')

    def applicant_messages(self, user):
        return [m for m in Message.objects.all() if user.email in m.to_addresses]

    def internal_messages(self, user):
        return [m for m in Message.objects.all() if user.email not in m.to_addresses]

    def test_null_highschool_does_not_raise_and_applicant_email_still_sent(self):
        user = self._user('null-hs@example.com')
        application = TeacherApplication.objects.create(
            user=user, createdon=date.today(), highschool=None)
        Message.objects.all().delete()

        # Must not raise (regression: AttributeError propagated out of
        # pre_save, so the status was never persisted).
        application.status = 'Submitted'
        application.save()

        application.refresh_from_db()
        self.assertEqual(application.status, 'Submitted')
        self.assertEqual(len(self.applicant_messages(user)), 1)

    def test_populated_highschool_reaches_the_internal_notification_body(self):
        school = HighSchool.objects.create(name='Central High')
        user = self._user('has-hs@example.com')
        application = TeacherApplication.objects.create(
            user=user, createdon=date.today(), highschool=school)
        Message.objects.all().delete()

        application.status = 'Submitted'
        application.save()

        internal = self.internal_messages(user)
        self.assertEqual(len(internal), 1)
        self.assertIn('Central High', internal[0].email.body)

        applicant = self.applicant_messages(user)
        self.assertEqual(len(applicant), 1)
        self.assertIn('Central High', applicant[0].email.body)
