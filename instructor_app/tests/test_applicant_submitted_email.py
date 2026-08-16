from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from mailer.models import Message

from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplication,
)

LANGUAGE_SETTINGS = {
    'applicant_submitted_email_active': 'Yes',
    'applicant_submitted_email_subject': 'We received your application',
    'applicant_submitted_email': '<p>Dear {{teacher_first_name}} {{teacher_last_name}}, status is {{application_status}}.</p>',
}

# create_new_application (post_save on TeacherApplication) reads this setting
# unguarded, so it must exist or object creation raises KeyError.
APPLICATION_EMAIL_SETTINGS = {
    'new_applicant_email_subject': 'Application started',
    'new_applicant_email': '<p>Welcome</p>',
    'internal_notify_on': [],
    'course_selected_email_recipient': '',
    'app_submitted_email_subject': 'Internal: submitted',
    'app_submitted_email': '<p>Internal</p>',
}


class ApplicantSubmittedEmailTests(TestCase):
    def setUp(self):
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': dict(APPLICATION_EMAIL_SETTINGS)})
        self.set_language(LANGUAGE_SETTINGS)
        Group.objects.get_or_create(name='applicant')
        self.user = CustomUser.objects.create(
            username='ada@example.com', email='ada@example.com',
            first_name='Ada', last_name='Lovelace')
        self.application = TeacherApplication.objects.create(
            user=self.user, createdon=date.today())
        # Discard the "application started" mail queued on creation.
        Message.objects.all().delete()

    def set_language(self, value):
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': dict(value)})

    def set_internal_notify(self, notify_on):
        value = dict(APPLICATION_EMAIL_SETTINGS)
        value['internal_notify_on'] = notify_on
        Setting.objects.update_or_create(
            key='tapp_email', defaults={'value': value})

    def submit(self):
        self.application.status = 'Submitted'
        self.application.save()

    def applicant_messages(self):
        return [m for m in Message.objects.all()
                if self.user.email in m.to_addresses]

    def test_applicant_receives_one_confirmation(self):
        self.submit()
        self.assertEqual(len(self.applicant_messages()), 1)

    def test_subject_comes_from_settings(self):
        self.submit()
        self.assertEqual(self.applicant_messages()[0].subject,
                         'We received your application')

    def test_body_renders_the_placeholders(self):
        self.submit()
        body = self.applicant_messages()[0].email.body
        self.assertIn('Ada', body)
        self.assertIn('Lovelace', body)
        self.assertIn('Submitted', body)

    def test_no_email_when_toggle_is_no(self):
        self.set_language({**LANGUAGE_SETTINGS,
                           'applicant_submitted_email_active': 'No'})
        self.submit()
        self.assertEqual(self.applicant_messages(), [])

    def test_no_email_when_toggle_is_unset(self):
        self.set_language({})
        self.submit()
        self.assertEqual(self.applicant_messages(), [])

    def test_sent_even_when_internal_notification_is_off(self):
        """The internal_notify_on gate must not suppress the applicant email."""
        self.set_internal_notify([])
        self.submit()
        self.assertEqual(len(self.applicant_messages()), 1)

    def test_not_sent_on_unrelated_status_change(self):
        self.application.status = 'Withdrawn'
        self.application.save()
        self.assertEqual(self.applicant_messages(), [])
