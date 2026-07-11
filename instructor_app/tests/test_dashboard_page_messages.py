from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from cis.page_messages import get_page_messages
import instructor_app.instructor_app.page_messages  # noqa: F401


class InstructorAppProviderTests(SimpleTestCase):
    @patch('instructor_app.instructor_app.page_messages._has_no_application', return_value=True)
    def test_start_application_prompt(self, _flag):
        msgs = get_page_messages('applicant', 'dashboard', request=MagicMock())
        self.assertTrue(any('application' in m.text.lower() for m in msgs))

    @patch('instructor_app.instructor_app.page_messages._has_no_application', return_value=False)
    def test_no_prompt_when_application_exists(self, _flag):
        msgs = get_page_messages('applicant', 'dashboard', request=MagicMock())
        self.assertFalse(msgs)
