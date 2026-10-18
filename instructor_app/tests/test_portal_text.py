"""portal_text helper (package-cis#81/#82)."""
from unittest import mock

from django.test import TestCase

from cis.models.settings import Setting

from .. import portal_text


class PortalTextTests(TestCase):
    """portal_text: page text from the portal package when installed, else cis
    (package-cis#81/#82). Patching ``has_module`` stands in for a tenant without
    the package, or a cis that no longer ships its copy."""

    def _only(self, *present):
        sources = {m for role in portal_text.PORTAL_TEXT_SOURCES.values() for m, _ in role}
        real = portal_text.has_module
        return mock.patch.object(
            portal_text, 'has_module',
            side_effect=lambda name: name in present if name in sources else real(name))

    def setUp(self):
        Setting.objects.update_or_create(
            key='cis.settings.instructor_portal', defaults={'value': {'x_blurb': 'inst'}})
        Setting.objects.update_or_create(
            key='cis.settings.faculty_portal', defaults={'value': {'x_blurb': 'fac old', 'y_blurb': 'fac y'}})

    def test_instructor_text(self):
        self.assertEqual(portal_text.portal_text('instructor')['x_blurb'], 'inst')
        with self._only('cis.settings.instructor_portal'):
            self.assertEqual(portal_text.portal_text('instructor')['x_blurb'], 'inst')

    def test_faculty_cis_copy_without_the_package(self):
        Setting.objects.update_or_create(
            key='faculty.settings.faculty_portal', defaults={'value': {'x_blurb': 'fac new'}})
        with self._only('cis.settings.faculty_portal'):
            self.assertEqual(portal_text.portal_text('faculty')['x_blurb'], 'fac old')

    def test_faculty_package_copy_wins_per_key(self):
        if not any(portal_text.has_module(m) for m, _ in portal_text.PORTAL_TEXT_SOURCES['faculty'][:2]):
            self.skipTest('faculty package not installed')
        Setting.objects.update_or_create(
            key='faculty.settings.faculty_portal', defaults={'value': {'x_blurb': 'fac new'}})
        text = portal_text.portal_text('faculty')
        self.assertEqual((text['x_blurb'], text['y_blurb']), ('fac new', 'fac y'))

    def test_empty_when_nothing_owns_it(self):
        with self._only():
            self.assertEqual(portal_text.portal_text('instructor'), {})
            self.assertEqual(portal_text.portal_text('faculty'), {})
