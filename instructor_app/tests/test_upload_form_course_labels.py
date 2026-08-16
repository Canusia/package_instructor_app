"""The "For" checkboxes on the material-upload form must name their course.

Two courses can each define a requirement called "Transcript"; without the
course prefix the applicant sees two identical checkboxes and cannot tell
which upload belongs to which course.
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from cis.models.course import Course, Cohort, CourseAppRequirement
from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import AppUploadForm
from instructor_app.instructor_app.models.teacher_applicant import (
    ApplicantSchoolCourse, TeacherApplication,
)


def _course(catalog, title):
    return Course.objects.create(
        name=f'ENGL& {catalog}', status='active', title=title,
        catalog_number=catalog,
        cohort=Cohort.objects.create(name=catalog, designator=f'C{catalog}&'),
        meta={'available_for_si': '1'},
    )


class UploadFormCourseLabelTests(TestCase):
    def setUp(self):
        # create_new_application (post_save) reads this setting unguarded.
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': {
                'new_applicant_email_subject': 'Started',
                'new_applicant_email': '<p>Welcome</p>',
                'internal_notify_on': [],
                'course_selected_email_recipient': '',
            }})
        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=user, createdon=timezone.localdate())

        self.first = _course('101', 'English Composition')
        self.second = _course('201', 'Technical Writing')
        for course in (self.first, self.second):
            ApplicantSchoolCourse.objects.create(
                teacherapplication=self.app, course=course, misc_info={})
            CourseAppRequirement.objects.create(course=course, name='Transcript')

        self.orphan = CourseAppRequirement.objects.create(
            course=None, name='Photo ID')

    def _choices(self):
        return AppUploadForm(self.app).fields['associated_with'].choices

    def test_each_label_names_its_course(self):
        labels = [label for _value, label in self._choices()]
        self.assertIn('English Composition ENGL& 101 — Transcript', labels)
        self.assertIn('Technical Writing ENGL& 201 — Transcript', labels)

    def test_identically_named_requirements_are_distinguishable(self):
        labels = [label for _value, label in self._choices()]
        self.assertEqual(len(labels), len(set(labels)))

    def test_values_are_still_requirement_ids(self):
        values = {value for value, _label in self._choices()}
        expected = {
            str(req.id) for req in CourseAppRequirement.objects.filter(
                course__in=[self.first, self.second])
        }
        self.assertEqual(values, expected)

    def test_requirement_without_a_course_is_not_offered(self):
        # The queryset filters on the applicant's selected courses, so an
        # unattached requirement never appears — assert that stays true.
        values = {value for value, _label in self._choices()}
        self.assertNotIn(str(self.orphan.id), values)

    def test_choices_are_grouped_by_course(self):
        labels = [label for _value, label in self._choices()]
        self.assertEqual(labels, sorted(labels))
