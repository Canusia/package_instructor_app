from django.apps import apps
from django.test import SimpleTestCase


class TeacherApplicantProfileSettingRegistrationTests(SimpleTestCase):
    def test_setting_appears_in_configurators(self):
        config = apps.get_app_config('instructor_app')
        names = [c['name'] for c in config.CONFIGURATORS]
        self.assertIn('teacher_applicant_profile', names)
