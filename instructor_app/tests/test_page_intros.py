"""Page intros instructor_app shows on other portals are settable (#18).

instructor_app owns the text in inst_app_language. A value saved there wins;
otherwise the portal package's own key (if a tenant set it) is used; otherwise
nothing. The 'Change me' placeholder is never shown.
"""
import pathlib
import re

from django.test import TestCase

from cis.models.settings import Setting

from .. import portal_text
from ..settings.inst_app_language import SettingForm, inst_app_language

PACKAGE = pathlib.Path(__file__).resolve().parents[1]


def _store(key, value):
    Setting.objects.update_or_create(key=key, defaults={'value': value})


class PageIntroTests(TestCase):
    def test_own_setting_wins(self):
        _store('inst_app_language', {'instructor_apps_blurb': 'Ours'})
        _store('cis.settings.instructor_portal', {'instructor_apps_blurb': 'Theirs'})
        self.assertEqual(
            portal_text.page_intro('instructor_apps_blurb', 'instructor', 'instructor_apps_blurb'),
            'Ours')

    def test_falls_back_to_the_portal_setting(self):
        _store('inst_app_language', {'instructor_apps_blurb': '  '})
        _store('cis.settings.instructor_portal', {'instructor_apps_blurb': 'Theirs'})
        self.assertEqual(
            portal_text.page_intro('instructor_apps_blurb', 'instructor', 'instructor_apps_blurb'),
            'Theirs')

    def test_empty_when_nothing_is_set(self):
        self.assertEqual(
            portal_text.page_intro('instructor_apps_blurb', 'instructor', 'instructor_apps_blurb'),
            '')

    def test_hs_admin_portal_is_a_source(self):
        _store('cis.settings.highschool_admin_portal', {'instructor_apps_blurb': 'HS text'})
        self.assertEqual(
            portal_text.page_intro(
                'hs_admin_instructor_apps_blurb', 'highschool_admin', 'instructor_apps_blurb'),
            'HS text')

    def test_new_keys_are_on_the_settings_form_and_saved(self):
        keys = ['instructor_apps_blurb', 'hs_admin_instructor_apps_blurb',
                'faculty_applications_blurb', 'faculty_manage_app_blurb',
                'profile_blurb', 'manage_password_blurb']
        for key in keys:
            self.assertIn(key, SettingForm.base_fields)
            self.assertFalse(SettingForm.base_fields[key].required, key)
        form = inst_app_language.__new__(inst_app_language)
        form.cleaned_data = {key: f'v-{key}' for key in keys}
        saved = form._to_python()
        for key in keys:
            self.assertEqual(saved[key], f'v-{key}')

    def test_no_change_me_placeholder_in_views(self):
        offenders = [
            str(path.relative_to(PACKAGE))
            for path in (PACKAGE / 'views').rglob('*.py')
            if re.search(r"['\"]Change me['\"]", path.read_text())
        ]
        self.assertEqual(offenders, [])
