"""The /ce/courses/ Course Administrators table comes from the tenant's shared
faculty_coords_table service when it can supply it (#2), and from the
package's own fallback partial otherwise.
"""
import types
from unittest import mock

from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from instructor_app.instructor_app.services import table_configs
from instructor_app.instructor_app.templatetags import instructor_app_tags as tags

CONTEXT = {
    'course_administrator_url': '/ce/api/course_administrator?format=datatables',
    'course_requirements_url': '/ce/instructor_apps/api/course-requirements?format=datatables',
    'urls': {'details_prefix': '/ce/course/'},
}


def _tag(context=CONTEXT):
    return tags.course_administrators_table(Context(context))


class CourseAdministratorsTableTagTests(SimpleTestCase):
    def test_uses_the_shared_service_variant(self):
        config = _tag()
        if config is None:
            self.skipTest('tenant faculty_coords_table has no faculty_coords_by_course')
        self.assertEqual(config['table_id'], 'table_course_administrator')
        self.assertIn('/ce/course/', config['opts_json'])
        self.assertIn('course_administrator?format=datatables', config['opts_json'])

    @override_settings(TABLE_CONFIGS_APP=None)
    def test_none_without_table_configs_app(self):
        self.assertIsNone(_tag())

    def test_none_when_the_tenant_service_lacks_the_variant(self):
        def build_config(*, variant, **kwargs):
            raise KeyError(variant)
        service = types.SimpleNamespace(build_config=build_config)
        with mock.patch.object(table_configs, 'get_table_config', return_value=service), \
                mock.patch.object(table_configs, 'available', return_value=True):
            self.assertIsNone(_tag())


class CourseRequirementsTabRenderTests(SimpleTestCase):
    def _render(self, **extra):
        return render_to_string(
            'instructor_app/ce/course_requirements_tab.html', {**CONTEXT, **extra})

    def test_shared_table_when_available(self):
        if _tag() is None:
            self.skipTest('tenant faculty_coords_table has no faculty_coords_by_course')
        html = self._render()
        self.assertIn('initFacultyCoordsTable', html)
        self.assertIn('id="table_course_administrator"', html)
        self.assertEqual(html.count('id="table_course_administrator"'), 1)

    def test_fallback_partial_when_unavailable(self):
        with mock.patch.object(tags, 'course_administrators_table', return_value=None):
            html = Template(
                '{% include "instructor_app/ce/partials/_course_administrators_table.html" '
                'with table_id="table_course_administrator" api_url=course_administrator_url '
                'details_prefix=urls.details_prefix %}').render(Context(CONTEXT))
        self.assertIn('id="table_course_administrator"', html)
        # escapejs writes '=' as \u003D -- the same string to JavaScript.
        self.assertIn("ajax: '/ce/api/course_administrator?format\\u003Ddatatables'", html)
        self.assertNotIn('initFacultyCoordsTable', html)

    def test_panes_still_follow_the_show_flags(self):
        html = self._render(show_course_requirements=False, show_course_administrators=False)
        self.assertNotIn('id="course_requirements"', html)
        self.assertNotIn('id="course_administrators"', html)

    def test_requirements_partial_is_parameterised(self):
        html = render_to_string(
            'instructor_app/ce/partials/_course_requirements_table.html',
            {'table_id': 'tbl_x', 'api_url': '/api/x', 'bulk_actions_url': '/bulk/x',
             'details_prefix': '/ce/course/'})
        self.assertIn('id="tbl_x"', html)
        self.assertIn("ajax: '/api/x'", html)
        self.assertIn('url = "/bulk/x"', html)
        self.assertNotIn('table_course_requirements', html)
