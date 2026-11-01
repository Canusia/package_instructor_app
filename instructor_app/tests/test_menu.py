"""instructor_app's sidebar items, registered in menu.py from ready(), for
every role whose menu links to a url this package serves. Ids are the
legacy menu names: `<id>_blurb` portal-text fields and `active_menu` /
`active_submenu` values depend on them.
"""
import importlib.util
import unittest

from django.test import SimpleTestCase

HAS_REGISTRY = importlib.util.find_spec('cis.menu_registry') is not None


def _ours(role):
    """{path: (label, url, order)} for this package's items in `role`."""
    from cis.menu_registry import menu
    out = {}
    for item in menu.items(role):
        if item['source'] == 'instructor_app':
            out[item['name']] = (item['label'], item['url'], item['order'])
        for sub in item['sub_menu']:
            if sub.get('source') == 'instructor_app':
                out[f"{item['name']}/{sub['name']}"] = (
                    sub['label'], sub['url'], sub['order'])
    return out


@unittest.skipUnless(HAS_REGISTRY, 'cis has no menu registry')
class InstructorAppMenuItems(SimpleTestCase):

    def test_applicant_items(self):
        self.assertEqual(_ours('applicant'), {
            'home': ('Home', 'applicant_app:dashboard', 10),
            'manage_app': ('Manage Application', None, 20),   # placeholder
            'profile': ('My Profile', 'applicant_app:profile', 30),
            'manage_password': ('Manage Password', 'applicant_app:manage_password', 40),
        })

    def test_ce_items_under_cis_instructors(self):
        self.assertEqual(_ours('ce'), {
            'instructors/incomplete_notifications': (
                'Incomplete App Notifs', 'ce_instructor_app:incomplete_notifications', 22),
            'instructors/pending_review_notifications': (
                'Pending Review Notifs', 'ce_instructor_app:pending_review_notifications', 24),
        })

    def test_faculty_and_instructor_items(self):
        self.assertEqual(_ours('faculty'), {
            'applications': ('Teacher Applications', 'faculty_app:instructor_apps', 50)})
        self.assertEqual(_ours('instructor'), {
            'instructor_apps': ('New Course Applications',
                                'instructor_app:instructor_apps', 52)})

    def test_no_registry_errors(self):
        from cis.menu_registry import check_menu_registry, menu
        self.assertEqual(
            [m for m in check_menu_registry(menu) if '(instructor_app)' in m.msg], [])
