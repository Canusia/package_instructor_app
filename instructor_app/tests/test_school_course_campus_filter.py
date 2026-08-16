"""
Tests for the campus dropdown on SchoolCourseForm (applicant manage-courses).

The campus field is a client-side filter over the course list: selecting a
campus shows only that campus's courses plus courses with no campus. Server
side, the field is optional and does not affect course validation/save — these
tests cover the field's presence/ordering, its choices, and the
course->campus map the template's JS consumes.
"""
from django.contrib.auth.models import Group
from django.test import TestCase

from cis.models.course import Course, Campus, Cohort
from instructor_app.instructor_app.forms.teacher_applicant import SchoolCourseForm
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplicant, TeacherApplication,
)
from cis.models.customuser import CustomUser


def _cohort(name='Eng', designator='ENGL&'):
    return Cohort.objects.create(name=name, designator=designator)


def _course(catalog, campus=None, cohort=None, si=True):
    return Course.objects.create(
        name=f'ENGL& {catalog}', status='active', title=f'Course {catalog}',
        catalog_number=catalog, campus=campus,
        cohort=cohort or _cohort(name=catalog, designator=f'C{catalog}&'),
        meta={'available_for_si': '1' if si else '2'},
    )


class SchoolCourseCampusFilterTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        TeacherApplicant.objects.create(user=user)
        from django.utils import timezone
        # Unsaved instance: the form only reads .highschool and filters
        # ApplicantSchoolCourse by its (already-assigned) UUID pk, so it needs
        # no DB row — and this avoids the post_save welcome-email signal.
        self.app = TeacherApplication(user=user, createdon=timezone.localdate())

        self.campus_a = Campus.objects.create(name='Campus A', code='A')
        self.campus_b = Campus.objects.create(name='Campus B', code='B')
        self.empty_campus = Campus.objects.create(name='Campus Empty', code='E')

        self.course_a = _course('101', campus=self.campus_a)
        self.course_b = _course('102', campus=self.campus_b)
        self.course_null = _course('103', campus=None)

        from cis.models.settings import Setting
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': {
                'new_applicant_email_subject': 'Started',
                'new_applicant_email': '<p>Welcome</p>',
                'internal_notify_on': [],
                'course_selected_email_recipient': '',
            }})

    def _form(self):
        return SchoolCourseForm(teacher_application=self.app, initial={'id': '-1'})

    def test_campus_field_present_and_before_course(self):
        fields = list(self._form().fields.keys())
        self.assertIn('campus', fields)
        self.assertLess(fields.index('campus'), fields.index('course'))

    def test_campus_field_is_optional(self):
        self.assertFalse(self._form().fields['campus'].required)

    def test_choices_only_include_campuses_with_selectable_courses(self):
        values = [c[0] for c in self._form().fields['campus'].choices]
        self.assertIn('', values)                          # "All Campuses"
        self.assertIn(str(self.campus_a.id), values)
        self.assertIn(str(self.campus_b.id), values)
        # A campus with no course at all must not appear.
        self.assertNotIn(str(self.empty_campus.id), values)

    def test_campus_remains_listed_after_applicant_adds_its_only_course(self):
        """The list describes the catalogue, not the applicant's progress."""
        from instructor_app.instructor_app.models.teacher_applicant import (
            ApplicantSchoolCourse,
        )
        self.app.save()
        ApplicantSchoolCourse.objects.create(
            teacherapplication=self.app, course=self.course_a, misc_info={})
        values = [c[0] for c in self._form().fields['campus'].choices]
        self.assertIn(str(self.campus_a.id), values)

    def test_course_campus_map_reflects_campus_or_empty(self):
        m = self._form().course_campus_map
        self.assertEqual(m[str(self.course_a.id)], str(self.campus_a.id))
        self.assertEqual(m[str(self.course_b.id)], str(self.campus_b.id))
        self.assertEqual(m[str(self.course_null.id)], '')  # no campus
