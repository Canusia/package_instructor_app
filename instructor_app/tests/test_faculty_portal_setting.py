"""faculty_portal_setting() reads the faculty package's setting when it is
installed and falls back to cis.settings.faculty_portal (package-cis#81)."""
import importlib.util
from unittest import mock

from django.test import SimpleTestCase

from ..faculty_portal import faculty_portal_setting


class FacultyPortalSettingTests(SimpleTestCase):
    def test_uses_the_faculty_package_setting_when_installed(self):
        setting = faculty_portal_setting()
        if setting.__module__.startswith('cis.'):
            self.skipTest('host carries the in-tree faculty app without the setting')
        self.assertEqual(setting.key, 'faculty.settings.faculty_portal')

    def test_falls_back_to_the_cis_setting(self):
        real = importlib.util.find_spec

        def find_spec(name, *args, **kwargs):
            if name.endswith('settings.faculty_portal_text'):
                return None
            return real(name, *args, **kwargs)

        with mock.patch('importlib.util.find_spec', side_effect=find_spec):
            setting = faculty_portal_setting()

        from cis.settings.faculty_portal import faculty_portal
        self.assertIs(setting, faculty_portal)
