"""install() is seed-only (package-cis #51)."""
from unittest import mock

from django.http import HttpRequest
from django.test import TestCase

from cis.models.settings import Setting
from ..settings.incomplete_si_application import incomplete_si_application
from ..settings.teacher_applicant_profile import teacher_applicant_profile
from ..settings.teacher_application_email import teacher_application_email
from ..settings.inst_app_language import inst_app_language


class InstallIsSeedOnlyTests(TestCase):
    """install() must never overwrite a customised setting (package-cis #51).

    The old tail assigned `setting.value = defaults` on the existing row as
    well as a new one, so any re-run of install() replaced a tenant's
    configuration with shipped placeholders.
    """
    settings_classes = [incomplete_si_application, teacher_applicant_profile,
                        teacher_application_email, inst_app_language]

    def _install(self, cls):
        cls(HttpRequest()).install()

    def test_creates_the_setting_when_absent(self):
        for cls in self.settings_classes:
            with self.subTest(cls.__name__):
                Setting.objects.filter(key=cls.key).delete()
                self._install(cls)
                self.assertTrue(Setting.objects.filter(key=cls.key).exists())

    def test_customised_values_survive_install(self):
        for cls in self.settings_classes:
            with self.subTest(cls.__name__):
                Setting.objects.filter(key=cls.key).delete()
                self._install(cls)
                defaults = Setting.objects.get(key=cls.key).value
                custom = {k: f'custom-{k}' for k in defaults} or {'custom': 'value'}
                Setting.objects.filter(key=cls.key).update(value=custom)

                self._install(cls)

                self.assertEqual(Setting.objects.get(key=cls.key).value, custom)

    def test_fallback_without_the_cis_helper_merges_missing_keys(self):
        """Tenants on a cis older than v0.0.39 have no Setting.install_defaults."""
        for cls in self.settings_classes:
            with self.subTest(cls.__name__):
                Setting.objects.filter(key=cls.key).delete()
                self._install(cls)
                defaults = Setting.objects.get(key=cls.key).value
                if not defaults:
                    continue
                dropped = next(iter(defaults))
                custom = {k: f'custom-{k}' for k in defaults if k != dropped}
                Setting.objects.filter(key=cls.key).update(value=custom)

                with mock.patch.object(Setting, 'install_defaults', None, create=True):
                    self._install(cls)

                value = Setting.objects.get(key=cls.key).value
                self.assertEqual(value[dropped], defaults[dropped])
                for key, expected in custom.items():
                    self.assertEqual(value[key], expected, msg=key)
