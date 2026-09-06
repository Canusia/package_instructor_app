"""post_save receivers must not raise on an unregistered email setting.

Canusia/ewu#74 recorded this shape in `cis.signals.teacher_applications`, but
the receivers that actually fire for the applicant portal are these ones: the
`instructor_app` models are separate concrete models with their own tables, and
`cis`'s copies are unused.

`from_db()` returns `{}` when the setting was never registered -- a fresh
environment, or a tenant stood up before `register_settings` runs. Each of
these is a `post_save` receiver, so the `KeyError` escapes the caller's
`save()` *after* the row is written: the application exists and the request
500s.
"""
from datetime import date
from unittest import mock

from django.contrib.auth.models import Group
from django.test import TestCase

from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.models.teacher_applicant import (
    ApplicantRecommendation,
    TeacherApplication,
)

TAPP_KEY = 'tapp_email'
LANGUAGE_KEY = 'inst_app_language'

CONFIGURED_TAPP = {
    'new_applicant_email': '<p>Welcome {{first_name}}</p>',
    'new_applicant_email_subject': 'Application started',
    'internal_notify_on': [],
}


class TeacherApplicationEmailGuardTests(TestCase):
    """create_new_application -- email_settings['new_applicant_email']."""

    def setUp(self):
        Group.objects.get_or_create(name='applicant')
        self.user = CustomUser.objects.create(
            username='ada@example.com', email='ada@example.com',
            first_name='Ada', last_name='Lovelace')

    def _application(self):
        return TeacherApplication.objects.create(
            user=self.user, createdon=date.today())

    def test_application_saves_when_the_setting_is_unregistered(self):
        Setting.objects.filter(key=TAPP_KEY).delete()

        application = self._application()

        self.assertTrue(
            TeacherApplication.objects.filter(pk=application.pk).exists())

    def test_no_mail_is_sent_when_the_template_is_unconfigured(self):
        Setting.objects.filter(key=TAPP_KEY).delete()

        with mock.patch(
                'instructor_app.instructor_app.signals.teacher_applications'
                '.send_html_mail') as send:
            self._application()

        send.assert_not_called()

    def test_mail_is_still_sent_when_the_template_is_configured(self):
        """The guard must not cost the notification it guards."""
        Setting.objects.update_or_create(
            key=TAPP_KEY, defaults={'value': dict(CONFIGURED_TAPP)})

        with mock.patch(
                'instructor_app.instructor_app.signals.teacher_applications'
                '.send_html_mail') as send:
            self._application()

        send.assert_called_once()


class RecommendationEmailGuardTests(TestCase):
    """create_new_recommendation -- ['rec_received_email_message']."""

    def setUp(self):
        Group.objects.get_or_create(name='applicant')
        self.user = CustomUser.objects.create(
            username='rae@example.com', email='rae@example.com',
            first_name='Rae', last_name='Applicant')
        # The application's own receiver reads a different setting, so keep
        # that one configured: these tests must turn on the recommendation
        # template alone.
        Setting.objects.update_or_create(
            key=TAPP_KEY, defaults={'value': dict(CONFIGURED_TAPP)})
        self.application = TeacherApplication.objects.create(
            user=self.user, createdon=date.today())

    def _recommendation(self):
        return ApplicantRecommendation.objects.create(
            teacher_application=self.application,
            submitter={'name': 'Ray Referee', 'email': 'ray@example.com'})

    def test_recommendation_saves_when_the_setting_is_unregistered(self):
        Setting.objects.filter(key=LANGUAGE_KEY).delete()

        recommendation = self._recommendation()

        self.assertTrue(
            ApplicantRecommendation.objects.filter(
                pk=recommendation.pk).exists())

    def test_mail_is_still_sent_when_the_template_is_configured(self):
        Setting.objects.update_or_create(
            key=LANGUAGE_KEY,
            defaults={'value': {
                'rec_received_email_message':
                    'Thanks {{recommender_name}}.',
                'rec_received_email_subject': 'Recommendation received',
            }})

        with mock.patch(
                'instructor_app.instructor_app.signals.teacher_applications'
                '.send_html_mail') as send:
            self._recommendation()

        send.assert_called_once()
