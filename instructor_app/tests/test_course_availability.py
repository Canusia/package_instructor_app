"""The selectable-course rule: active, not explicitly No, campus match or unset.

The `available_for_si` flag lives in Course.meta (a JSONField) and is unset on
most rows. Two kinds of "unset" exist — meta NULL entirely, and meta a dict
without the key — and they behave OPPOSITELY under Django's exclude(), so both
are pinned here.
"""
from django.test import TestCase

from cis.models.course import Campus, Cohort, Course
from instructor_app.instructor_app.services.course_availability import (
    campuses_with_selectable_courses,
    selectable_courses,
)


def _course(catalog, campus=None, meta='unset', status='active'):
    """meta='unset' leaves the key absent; meta=None makes Course.meta NULL."""
    if meta == 'unset':
        meta_value = {'some_other_key': 'x'}
    elif meta is None:
        meta_value = None
    else:
        meta_value = {'available_for_si': meta}
    return Course.objects.create(
        name=f'ENGL& {catalog}', status=status, title=f'Course {catalog}',
        catalog_number=catalog, campus=campus,
        cohort=Cohort.objects.create(name=catalog, designator=f'C{catalog}&'),
        meta=meta_value,
    )


class SelectableCourseRuleTests(TestCase):
    def test_includes_course_whose_meta_dict_lacks_the_key(self):
        course = _course('101')
        self.assertIn(course, selectable_courses())

    def test_includes_course_whose_meta_is_null_entirely(self):
        course = _course('102', meta=None)
        self.assertIn(course, selectable_courses())

    def test_includes_course_with_blank_select_value(self):
        course = _course('103', meta='')
        self.assertIn(course, selectable_courses())

    def test_includes_course_explicitly_marked_yes(self):
        course = _course('104', meta='1')
        self.assertIn(course, selectable_courses())

    def test_excludes_course_explicitly_marked_no(self):
        course = _course('105', meta='2')
        self.assertNotIn(course, selectable_courses())

    def test_excludes_inactive_course(self):
        course = _course('106', status='inactive')
        self.assertNotIn(course, selectable_courses())


class SelectableCourseCampusScopingTests(TestCase):
    def setUp(self):
        self.campus_a = Campus.objects.create(name='Campus A', code='A')
        self.campus_b = Campus.objects.create(name='Campus B', code='B')
        self.on_a = _course('201', campus=self.campus_a)
        self.on_b = _course('202', campus=self.campus_b)
        self.no_campus = _course('203', campus=None)

    def test_no_campus_argument_returns_everything(self):
        result = selectable_courses()
        self.assertIn(self.on_a, result)
        self.assertIn(self.on_b, result)
        self.assertIn(self.no_campus, result)

    def test_campus_returns_its_own_courses_plus_campusless(self):
        result = selectable_courses(campus=self.campus_a)
        self.assertIn(self.on_a, result)
        self.assertIn(self.no_campus, result)
        self.assertNotIn(self.on_b, result)


class CampusListTests(TestCase):
    def test_lists_campuses_that_have_a_selectable_course(self):
        campus = Campus.objects.create(name='Has Courses', code='H')
        _course('301', campus=campus)
        self.assertIn(campus, campuses_with_selectable_courses())

    def test_omits_campus_whose_only_course_is_marked_no(self):
        campus = Campus.objects.create(name='All Refused', code='R')
        _course('302', campus=campus, meta='2')
        self.assertNotIn(campus, campuses_with_selectable_courses())

    def test_omits_campus_with_no_courses(self):
        campus = Campus.objects.create(name='Empty', code='E')
        self.assertNotIn(campus, campuses_with_selectable_courses())

    def test_ordered_by_name(self):
        later = Campus.objects.create(name='Zed', code='Z')
        earlier = Campus.objects.create(name='Alpha', code='AL')
        _course('303', campus=later)
        _course('304', campus=earlier)
        names = [c.name for c in campuses_with_selectable_courses()]
        self.assertEqual(names, sorted(names))


class SchoolCourseFormUsesTheRuleTests(TestCase):
    """The applicant's course dropdown must follow the shared rule.

    Before this change the form required available_for_si == '1' exactly, which
    hid 99 of 101 active courses at EWU.
    """

    def _form(self):
        from django.contrib.auth.models import Group
        from django.utils import timezone

        from cis.models.customuser import CustomUser
        from instructor_app.instructor_app.forms.teacher_applicant import (
            SchoolCourseForm,
        )
        from instructor_app.instructor_app.models.teacher_applicant import (
            TeacherApplication,
        )

        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        # Unsaved: the form only reads .highschool and filters by the assigned
        # UUID pk, so no DB row is needed — and this avoids the post_save email.
        app = TeacherApplication(user=user, createdon=timezone.localdate())
        return SchoolCourseForm(teacher_application=app, initial={'id': '-1'})

    def test_course_with_unset_flag_is_offered(self):
        course = _course('401')
        self.assertIn(course, self._form().fields['course'].queryset)

    def test_course_marked_no_is_not_offered(self):
        course = _course('402', meta='2')
        self.assertNotIn(course, self._form().fields['course'].queryset)
