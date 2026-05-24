import json

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from instructor_app.instructor_app.settings.teacher_applicant_profile import (
    CONFIGURABLE_FIELDS,
    DEFAULT_REQUIRED_FIELDS,
    teacher_applicant_profile,
)


class TeacherApplicantProfileSettingRegistrationTests(SimpleTestCase):
    def test_setting_appears_in_configurators(self):
        config = apps.get_app_config('instructor_app')
        names = [c['name'] for c in config.CONFIGURATORS]
        self.assertIn('teacher_applicant_profile', names)
