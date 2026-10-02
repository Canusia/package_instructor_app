"""Campus-scoped school pickers on the applicant forms (cis HighSchoolCampus)."""
import uuid

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.utils import timezone

from cis.campus_context import campus_context
from cis.models.course import Campus
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool, HighSchoolCampus
from instructor_app.instructor_app.forms.teacher_applicant import (
    EditSchoolCourseForm, SchoolCourseForm)
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplicant, TeacherApplication)


def _sfx():
    return uuid.uuid4().hex[:8]


def _campus():
    return Campus.objects.create(
        name=f'C-{_sfx()}', code=f'{settings.CAMPUS_CODE_PREFIX}_{_sfx()[:6]}')


def _hs(name, campus=None, status='Active'):
    hs = HighSchool.objects.create(name=name, code=_sfx())
    HighSchoolCampus.objects.filter(highschool=hs).delete()
    if campus is not None:
        HighSchoolCampus.objects.create(
            highschool=hs, campus=campus, status=status)
    return hs


class _Base(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(
            username=f'{_sfx()}@x.com', email=f'{_sfx()}@x.com')
        TeacherApplicant.objects.create(user=user)
        self.user = user
        self.a, self.b = _campus(), _campus()
        self.mine = _hs('Mine', self.a)
        self.foreign = _hs('Foreign', self.b)
        self.dormant = _hs('Dormant', self.a, 'Inactive')

    def _app(self, highschool=None):
        # Unsaved: the forms only read .highschool, and this avoids the
        # post_save welcome-email signal.
        return TeacherApplication(
            user=self.user, createdon=timezone.localdate(),
            highschool=highschool)

    def _edit(self, highschool=None, data=None):
        return EditSchoolCourseForm(self._app(highschool), data)

    def _add(self, highschool=None, data=None):
        form = SchoolCourseForm(self._app(highschool), data)
        return form

    @staticmethod
    def _ids(form):
        return {str(v) for v, _ in form.fields['highschool'].choices if v not in ('', '-1')}


@override_settings(MULTI_CAMPUS=True)
class MultiCampusTests(_Base):
    def test_edit_form_excludes_other_campus_and_inactive(self):
        with campus_context(self.a):
            self.assertEqual(self._ids(self._edit()), {str(self.mine.pk)})

    def test_edit_form_keeps_existing_school(self):
        for existing in (self.foreign, self.dormant):
            with campus_context(self.a):
                form = self._edit(existing)
                self.assertEqual(
                    self._ids(form), {str(self.mine.pk), str(existing.pk)})
                self.assertEqual(
                    form.fields['highschool'].initial, existing.pk)

    def test_edit_form_foreign_post_rejected(self):
        with campus_context(self.a):
            form = self._edit(data={
                'id': str(uuid.uuid4()), 'highschool': str(self.foreign.pk),
                'action': 'edit_teacher_application_highschool'})
            self.assertFalse(form.is_valid())
            self.assertIn('highschool', form.errors)

    def test_edit_form_own_school_post_accepted(self):
        with campus_context(self.a):
            form = self._edit(data={
                'id': str(uuid.uuid4()), 'highschool': str(self.mine.pk),
                'action': 'edit_teacher_application_highschool'})
            self.assertTrue(form.is_valid(), form.errors)

    def test_add_form_excludes_other_campus_and_inactive(self):
        with campus_context(self.a):
            self.assertEqual(self._ids(self._add()), {str(self.mine.pk)})

    def test_add_form_foreign_post_rejected(self):
        with campus_context(self.a):
            form = self._add(data={
                'id': '-1', 'highschool': str(self.foreign.pk)})
            form.is_valid()
            self.assertIn('highschool', form.errors)

    def test_choices_follow_the_request_campus(self):
        with campus_context(self.b):
            self.assertEqual(self._ids(self._edit()), {str(self.foreign.pk)})
            self.assertEqual(self._ids(self._add()), {str(self.foreign.pk)})


@override_settings(MULTI_CAMPUS=False)
class SingleCampusTests(_Base):
    def test_options_are_campus_linked_active_schools(self):
        with campus_context(self.a):
            self.assertEqual(self._ids(self._edit()), {str(self.mine.pk)})
            self.assertEqual(self._ids(self._add()), {str(self.mine.pk)})
