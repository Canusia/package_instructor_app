from unittest.mock import MagicMock

from django.test import TestCase

from cis.models.settings import Setting
from instructor_app.instructor_app.settings.inst_app_language import (
    APPLICANT_SUBMITTED_EMAIL_DEFAULT,
    SettingForm,
    inst_app_language,
)


class ApplicantSubmittedEmailFieldTests(TestCase):
    def test_fields_are_declared_on_the_form(self):
        fields = SettingForm().fields
        self.assertIn('applicant_submitted_email_active', fields)
        self.assertIn('applicant_submitted_email_subject', fields)
        self.assertIn('applicant_submitted_email', fields)

    def test_all_three_fields_are_optional(self):
        fields = SettingForm().fields
        for name in ('applicant_submitted_email_active',
                     'applicant_submitted_email_subject',
                     'applicant_submitted_email'):
            self.assertFalse(fields[name].required, name)

    def test_active_field_offers_yes_and_no(self):
        choices = [c[0] for c in SettingForm().fields['applicant_submitted_email_active'].choices]
        self.assertIn('Yes', choices)
        self.assertIn('No', choices)

    def test_help_text_documents_the_placeholders(self):
        help_text = SettingForm().fields['applicant_submitted_email'].help_text
        for token in ('{{teacher_first_name}}', '{{teacher_last_name}}',
                      '{{teacher_email}}', '{{highschool}}', '{{courses}}'):
            self.assertIn(token, help_text)


class ApplicantSubmittedEmailInstallTests(TestCase):
    def test_install_seeds_the_feature_switched_off(self):
        inst_app_language(request=MagicMock()).install()
        value = Setting.objects.get(key='inst_app_language').value
        self.assertEqual(value['applicant_submitted_email_active'], 'No')
        self.assertTrue(value['applicant_submitted_email_subject'])
        self.assertEqual(value['applicant_submitted_email'],
                         APPLICANT_SUBMITTED_EMAIL_DEFAULT)
