"""The applicant forms use the tenant's captcha when it has one (#8, #9).

A tenant with ``cis/captcha.py`` (ALTCHA) gets its ``CaptchaField``; every
other tenant keeps django-recaptcha's ``ReCaptchaField``.
"""
import importlib
import sys
import types
from unittest import mock

from django import forms
from django.test import SimpleTestCase
from django_recaptcha.fields import ReCaptchaField

from instructor_app.instructor_app import captcha
from instructor_app.instructor_app.forms import teacher_applicant


class _TenantCaptcha(forms.CharField):
    pass


class CaptchaProviderTests(SimpleTestCase):
    def tearDown(self):
        importlib.reload(captcha)

    def test_falls_back_to_recaptcha_without_cis_captcha(self):
        with mock.patch.object(captcha.importlib.util, 'find_spec', return_value=None):
            importlib.reload(captcha)
        self.assertIs(captcha.CaptchaField, ReCaptchaField)

    def test_uses_the_tenant_field_when_cis_captcha_exists(self):
        module = types.ModuleType('cis.captcha')
        module.CaptchaField = _TenantCaptcha
        with mock.patch.dict(sys.modules, {'cis.captcha': module}), \
                mock.patch.object(captcha.importlib.util, 'find_spec',
                                  return_value=object()):
            importlib.reload(captcha)
        self.assertIs(captcha.CaptchaField, _TenantCaptcha)

    def test_both_public_forms_use_the_resolved_field(self):
        expected = captcha.CaptchaField
        for form in (teacher_applicant.TeacherApplicantVerifyEmailForm,
                     teacher_applicant.NoteReplyForm):
            self.assertIsInstance(form.base_fields['captcha'], expected, form.__name__)

    def test_no_module_imports_django_recaptcha_directly(self):
        import pathlib
        root = pathlib.Path(captcha.__file__).parent
        offenders = [
            str(path.relative_to(root)) for path in root.rglob('*.py')
            if 'tests' not in path.parts and path.name != 'captcha.py'
            and 'django_recaptcha' in path.read_text()]
        self.assertEqual(offenders, [])
