from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from cis.models.customuser import CustomUser
from cis.page_messages import get_page_messages
import instructor_app.instructor_app.page_messages as pm  # noqa: F401


class HasNoApplicationImportTests(TestCase):
    """Exercise _has_no_application for real.

    The provider's model import must resolve under both install layouts: flat
    (site-packages/instructor_app/) in production and nested
    (instructor_app/instructor_app/) in the editable-submodule dev checkout.
    The tests below patch _has_no_application, so they never run its import —
    an absolute nested path passed every test here and still
    ModuleNotFoundError'd on the dashboard in production.
    """

    def test_import_resolves_and_reports_no_application(self):
        user = CustomUser.objects.create(username='appl', email='appl@x.com')
        self.assertTrue(pm._has_no_application(user))


class InstructorAppProviderTests(SimpleTestCase):
    @patch('instructor_app.instructor_app.page_messages._has_no_application', return_value=True)
    def test_start_application_prompt(self, _flag):
        msgs = get_page_messages('applicant', 'dashboard', request=MagicMock())
        self.assertTrue(any('application' in m.text.lower() for m in msgs))

    @patch('instructor_app.instructor_app.page_messages._has_no_application', return_value=False)
    def test_no_prompt_when_application_exists(self, _flag):
        msgs = get_page_messages('applicant', 'dashboard', request=MagicMock())
        self.assertFalse(msgs)
