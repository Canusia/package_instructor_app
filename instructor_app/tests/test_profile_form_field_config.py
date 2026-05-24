from django.test import TestCase

from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    TeacherApplicantProfileForm,
)
from instructor_app.instructor_app.settings.teacher_applicant_profile import (
    CONFIGURABLE_FIELD_NAMES,
)


def set_field_config(**kwargs):
    """Helper: write a config row, defaulting unspecified keys to the
    'all visible, declared required, no labels/weights' baseline."""
    value = {
        'visible':  list(CONFIGURABLE_FIELD_NAMES),
        'required': [],
        'labels':   {},
        'weights':  {},
    }
    value.update(kwargs)
    Setting.objects.update_or_create(
        key='instructor_app.teacher_applicant_profile',
        defaults={'value': value},
    )


class HiddenFieldsTests(TestCase):
    def test_fields_absent_from_visible_are_removed(self):
        visible = [n for n in CONFIGURABLE_FIELD_NAMES if n not in {'ssn', 'alt_phone'}]
        set_field_config(visible=visible)

        form = TeacherApplicantProfileForm()
        self.assertNotIn('ssn', form.fields)
        self.assertNotIn('alt_phone', form.fields)
        self.assertIn('first_name', form.fields)

    def test_mandatory_flow_fields_are_never_hidden(self):
        # Visible omits everything; mandatory fields should still be on form.
        set_field_config(visible=[])

        form = TeacherApplicantProfileForm()
        self.assertIn('email', form.fields)
        self.assertIn('password', form.fields)
        self.assertIn('confirm_password', form.fields)


class RequiredFieldsTests(TestCase):
    def test_listed_fields_become_required(self):
        set_field_config(required=['middle_name', 'alt_phone'])

        form = TeacherApplicantProfileForm()
        self.assertTrue(form.fields['middle_name'].required)
        self.assertTrue(form.fields['alt_phone'].required)
        self.assertEqual(
            form.fields['middle_name'].widget.attrs.get('data-validate-required'),
            'true',
        )

    def test_unlisted_fields_become_optional(self):
        # first_name normally required — flip it off via the setting.
        set_field_config(required=['last_name'])

        form = TeacherApplicantProfileForm()
        self.assertFalse(form.fields['first_name'].required)
        self.assertNotIn(
            'data-validate-required',
            form.fields['first_name'].widget.attrs,
        )
        self.assertTrue(form.fields['last_name'].required)

    def test_email_and_password_required_state_is_untouched(self):
        # email/password aren't configurable; listing them is a no-op.
        set_field_config(required=['email', 'password'])

        form = TeacherApplicantProfileForm()
        self.assertTrue(form.fields['email'].required)
        self.assertTrue(form.fields['password'].required)


class LabelOverrideTests(TestCase):
    def test_custom_label_applied_to_configured_field(self):
        set_field_config(labels={'first_name': 'Given Name'})

        form = TeacherApplicantProfileForm()
        self.assertEqual(form.fields['first_name'].label, 'Given Name')

    def test_unlabelled_field_keeps_declarative_label(self):
        set_field_config(labels={})

        form = TeacherApplicantProfileForm()
        # Declared label in the form is 'First Name'.
        self.assertEqual(form.fields['first_name'].label, 'First Name')


class WeightOrderingTests(TestCase):
    def test_lower_weight_appears_earlier(self):
        # Give last_name a lighter weight than first_name; expect it
        # before first_name in the field iteration order.
        set_field_config(weights={'last_name': 1, 'first_name': 5})

        form = TeacherApplicantProfileForm()
        names = list(form.fields.keys())
        configurable_in_order = [n for n in names if n in CONFIGURABLE_FIELD_NAMES]
        self.assertLess(
            configurable_in_order.index('last_name'),
            configurable_in_order.index('first_name'),
        )

    def test_unweighted_field_appears_after_weighted(self):
        # ssn has no weight; first_name does. first_name should precede ssn.
        set_field_config(weights={'first_name': 0})

        form = TeacherApplicantProfileForm()
        names = list(form.fields.keys())
        configurable_in_order = [n for n in names if n in CONFIGURABLE_FIELD_NAMES]
        self.assertLess(
            configurable_in_order.index('first_name'),
            configurable_in_order.index('ssn'),
        )


class MissingSettingFallbackTests(TestCase):
    """When no Setting row exists, the form must keep its declarative
    DEFAULT_REQUIRED_FIELDS in effect — silently making everything
    optional would let blank submissions through."""

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
        self.assertIn('ssn', form.fields)  # default visible includes all
