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
