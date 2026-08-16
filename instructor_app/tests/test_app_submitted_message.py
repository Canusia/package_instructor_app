import os

from django.test import TestCase

from cis.models.settings import Setting
from instructor_app.instructor_app.settings.inst_app_language import (
    APP_SUBMITTED_MESSAGE_DEFAULT,
    get_app_submitted_message,
)

import instructor_app.instructor_app as app_package

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(app_package.__file__)),
    'templates', 'instructor_app', 'review_application.html',
)


class AppSubmittedMessageResolverTests(TestCase):
    def _write_setting(self, value):
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': value})

    def test_returns_builtin_default_when_setting_row_missing(self):
        Setting.objects.filter(key='inst_app_language').delete()
        self.assertEqual(get_app_submitted_message(), APP_SUBMITTED_MESSAGE_DEFAULT)

    def test_returns_builtin_default_when_key_absent(self):
        self._write_setting({'is_accepting_new': 'Yes'})
        self.assertEqual(get_app_submitted_message(), APP_SUBMITTED_MESSAGE_DEFAULT)

    def test_returns_builtin_default_when_value_blank(self):
        self._write_setting({'app_submitted_message': '   '})
        self.assertEqual(get_app_submitted_message(), APP_SUBMITTED_MESSAGE_DEFAULT)

    def test_returns_configured_value(self):
        self._write_setting({'app_submitted_message': 'Thanks! We got it.'})
        self.assertEqual(get_app_submitted_message(), 'Thanks! We got it.')

    def test_default_matches_the_wording_the_template_used_to_hardcode(self):
        self.assertEqual(
            APP_SUBMITTED_MESSAGE_DEFAULT,
            'Your application has been submitted. '
            'Please contact our office to make any edits.',
        )


class ReviewTemplateTests(TestCase):
    """Guard: the wording must come from settings, not from the template."""

    def test_template_no_longer_hardcodes_the_message(self):
        with open(TEMPLATE_PATH) as handle:
            source = handle.read()
        self.assertNotIn('Please contact our office to make any edits', source)
        self.assertIn('{{ app_submitted_message', source)
