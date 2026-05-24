from django.test import TestCase

from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    TeacherApplicantProfileForm,
)


class HiddenFieldsTests(TestCase):
    def setUp(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                'hidden_fields': ['ssn', 'alt_phone'],
                'required_fields': [],
            }},
        )

    def test_hidden_fields_are_removed_from_form(self):
        form = TeacherApplicantProfileForm()
        self.assertNotIn('ssn', form.fields)
        self.assertNotIn('alt_phone', form.fields)
        # Non-hidden configurable field is still present
        self.assertIn('first_name', form.fields)

    def test_mandatory_flow_fields_are_never_hidden(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                # Attempt to hide mandatory fields — should be ignored
                'hidden_fields': ['email', 'password', 'confirm_password'],
                'required_fields': [],
            }},
        )
        form = TeacherApplicantProfileForm()
        self.assertIn('email', form.fields)
        self.assertIn('password', form.fields)
        self.assertIn('confirm_password', form.fields)


class RequiredFieldsTests(TestCase):
    def test_listed_fields_become_required(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                'hidden_fields': [],
                'required_fields': ['middle_name', 'alt_phone'],
            }},
        )
        form = TeacherApplicantProfileForm()
        self.assertTrue(form.fields['middle_name'].required)
        self.assertTrue(form.fields['alt_phone'].required)
        self.assertEqual(
            form.fields['middle_name'].widget.attrs.get('data-validate-required'),
            'true',
        )

    def test_unlisted_fields_become_optional(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                'hidden_fields': [],
                # first_name normally required — flip it off
                'required_fields': ['last_name'],
            }},
        )
        form = TeacherApplicantProfileForm()
        self.assertFalse(form.fields['first_name'].required)
        self.assertNotIn(
            'data-validate-required',
            form.fields['first_name'].widget.attrs,
        )
        self.assertTrue(form.fields['last_name'].required)

    def test_email_and_password_required_state_is_untouched(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                'hidden_fields': [],
                # Note: these field names are not in CONFIGURABLE_FIELDS,
                # so listing them should have no effect.
                'required_fields': ['email', 'password'],
            }},
        )
        form = TeacherApplicantProfileForm()
        # email is declared with validate={'required': 'true'} and is not
        # configurable — its required state stays True regardless of setting.
        self.assertTrue(form.fields['email'].required)
        self.assertTrue(form.fields['password'].required)


class MissingSettingFallbackTests(TestCase):
    """When no Setting row exists (fresh deploy, or row deleted), the form
    must keep its declarative DEFAULT_REQUIRED_FIELDS in effect — silently
    making everything optional would let blank submissions through."""

    def test_defaults_apply_when_setting_row_missing(self):
        Setting.objects.filter(
            key='instructor_app.teacher_applicant_profile',
        ).delete()
        form = TeacherApplicantProfileForm()
        for name in ['first_name', 'last_name', 'primary_phone',
                     'date_of_birth', 'home_address', 'city', 'state',
                     'zip_code']:
            self.assertTrue(
                form.fields[name].required,
                f'{name} should be required when setting row is missing',
            )

    def test_malformed_setting_value_falls_back_to_defaults(self):
        # Superuser might save a non-dict via raw JSON editor; form should
        # not crash and should keep declarative defaults.
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': []},
        )
        form = TeacherApplicantProfileForm()
        self.assertTrue(form.fields['first_name'].required)
        self.assertIn('ssn', form.fields)  # default hidden list is empty
