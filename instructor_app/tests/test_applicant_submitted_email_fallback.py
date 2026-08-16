"""
Finding 2: APPLICANT_SUBMITTED_EMAIL_DEFAULT was wired only into install(),
which never runs against an already-configured tenant. On every upgraded
tenant the applicant_submitted_email* keys are absent until an admin saves
the settings form, which meant:

- preview(): Template(None) raised TypeError -> 500 when an admin clicked
  "See Preview".
- notify_status_change(): send_notification() silently no-op'd on an empty
  template if the toggle was flipped to Yes before a body was pasted.

get_applicant_submitted_email() mirrors get_app_submitted_message() and
supplies (subject, body) with built-in fallbacks for missing-or-blank
settings, used by both call sites.
"""
from unittest.mock import MagicMock

from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.settings.inst_app_language import (
    APPLICANT_SUBMITTED_EMAIL_DEFAULT,
    APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT,
    get_applicant_submitted_email,
    inst_app_language,
)


class ApplicantSubmittedEmailResolverTests(TestCase):
    def _write_setting(self, value):
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': value})

    def test_returns_builtin_defaults_when_setting_row_missing(self):
        Setting.objects.filter(key='inst_app_language').delete()
        subject, body = get_applicant_submitted_email()
        self.assertEqual(subject, APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT)
        self.assertEqual(body, APPLICANT_SUBMITTED_EMAIL_DEFAULT)

    def test_returns_builtin_defaults_when_keys_absent(self):
        self._write_setting({'is_accepting_new': 'Yes'})
        subject, body = get_applicant_submitted_email()
        self.assertEqual(subject, APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT)
        self.assertEqual(body, APPLICANT_SUBMITTED_EMAIL_DEFAULT)

    def test_returns_builtin_defaults_when_values_blank(self):
        self._write_setting({
            'applicant_submitted_email_subject': '   ',
            'applicant_submitted_email': '   ',
        })
        subject, body = get_applicant_submitted_email()
        self.assertEqual(subject, APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT)
        self.assertEqual(body, APPLICANT_SUBMITTED_EMAIL_DEFAULT)

    def test_returns_configured_values(self):
        self._write_setting({
            'applicant_submitted_email_subject': 'We got your application',
            'applicant_submitted_email': '<p>Custom body</p>',
        })
        subject, body = get_applicant_submitted_email()
        self.assertEqual(subject, 'We got your application')
        self.assertEqual(body, '<p>Custom body</p>')

    def test_install_seeds_the_subject_constant(self):
        """install()'s literal subject was promoted to the shared constant;
        guard against them drifting apart again."""
        inst_app_language(request=MagicMock()).install()
        value = Setting.objects.get(key='inst_app_language').value
        self.assertEqual(value['applicant_submitted_email_subject'],
                          APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT)


class ApplicantSubmittedEmailPreviewTests(TestCase):
    """Guard the regression itself: clicking "See Preview" on an
    upgraded tenant (no applicant_submitted_email* keys saved) must not 500.
    """

    def setUp(self):
        Group.objects.get_or_create(name='applicant')
        self.user = CustomUser.objects.create(
            username='ada@example.com', email='ada@example.com',
            first_name='Ada', last_name='Lovelace')

    def _request(self):
        request = RequestFactory().get('/', {'report_id': '1'})
        request.user = self.user
        return request

    def test_preview_does_not_raise_when_setting_row_missing(self):
        Setting.objects.filter(key='inst_app_language').delete()
        request = self._request()
        response = inst_app_language(request=request).preview(
            request, 'applicant_submitted_email')
        self.assertEqual(response.status_code, 200)

    def test_preview_renders_configured_body(self):
        Setting.objects.update_or_create(
            key='inst_app_language',
            defaults={'value': {
                'applicant_submitted_email_subject': 'Subj',
                'applicant_submitted_email': '<p>Hi {{teacher_first_name}}</p>',
            }})
        request = self._request()
        response = inst_app_language(request=request).preview(
            request, 'applicant_submitted_email')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hi Ada', response.content)
