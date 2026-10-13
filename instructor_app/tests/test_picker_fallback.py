"""School pickers work without campus scoping (tenants with an in-repo cis).

An in-repo cis has no cis.highschool_scope, so the applicant forms fall back
to the pre-2026.1 picker: active schools, plus the application's current
school so an edit form never drops its value.
"""
import pathlib
import uuid

from django.test import TestCase

from cis.models.highschool import HighSchool

from ..forms import teacher_applicant as forms_mod

PKG = pathlib.Path(__file__).resolve().parents[2]


def _hs(name, status='Active'):
    return HighSchool.objects.create(
        name=name, code=uuid.uuid4().hex[:8], status=status)


class PickerFallbackTests(TestCase):
    def setUp(self):
        self.active = _hs('Active HS')
        self.inactive = _hs('Inactive HS', 'Inactive')

    def test_fallback_lists_active_schools_only(self):
        qs = forms_mod._active_schools_picker()
        self.assertIn(self.active, qs)
        self.assertNotIn(self.inactive, qs)

    def test_fallback_keeps_current_school(self):
        for keep in (self.inactive.pk, self.inactive):
            self.assertIn(
                self.inactive, forms_mod._active_schools_picker(keep=keep))

    def test_fallback_ignores_blank_keep(self):
        qs = forms_mod._active_schools_picker(keep='')
        self.assertNotIn(self.inactive, qs)


class PackagingTests(TestCase):
    def test_myce_cis_is_not_a_hard_requirement(self):
        for name in ('setup.py', 'setup.cfg'):
            src = (PKG / name).read_text()
            install = src.split('install_requires', 1)[1]
            install = install.split('extras_require', 1)[0]
            self.assertNotIn('myce_cis', install, name)
