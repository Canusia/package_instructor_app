"""Application notes name the staff user who acted, not the assignee.

Status changes and reviewer assignments write a private note. The actor is
passed as a transient ``_changed_by`` on the instance; without one the note
has no author and renders as "System" (package_instructor_app#5).
"""
from unittest import mock

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.test import TestCase
from django.utils import timezone

from cis.models.course import Course, Cohort
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    EditTeacherApplicationForm,
)
from instructor_app.instructor_app.models.applicant_course_reviewer import (
    ApplicantCourseReviewer,
)
from instructor_app.instructor_app.models.applicant_school_course import (
    ApplicantSchoolCourse,
)
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.models.teacher_application_note import (
    TeacherApplicationNote,
)
from instructor_app.instructor_app.signals import teacher_applications as sig


class NoteActorTests(TestCase):
    def setUp(self):
        post_save.disconnect(sig.create_new_application, sender=TeacherApplication)
        post_save.disconnect(sig.selected_new_course, sender=ApplicantSchoolCourse)
        self.addCleanup(post_save.connect, sig.create_new_application, sender=TeacherApplication)
        self.addCleanup(post_save.connect, sig.selected_new_course, sender=ApplicantSchoolCourse)
        for target in ('notify_status_change',):
            patcher = mock.patch.object(TeacherApplication, target)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(ApplicantCourseReviewer, 'notify_status_change')
        patcher.start()
        self.addCleanup(patcher.stop)

        Group.objects.get_or_create(name='applicant')
        self.assignee = CustomUser.objects.create(
            username='assignee@x.com', email='assignee@x.com', is_staff=True)
        self.staff = CustomUser.objects.create(
            username='staff@x.com', email='staff@x.com', is_staff=True)
        self.faculty = CustomUser.objects.create(
            username='fac@x.com', email='fac@x.com')
        applicant = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=applicant, createdon=timezone.localdate(),
            assigned_to=self.assignee, status='Submitted', misc_info={})
        hs = HighSchool.objects.create(name='HS', status='Active')
        course = Course.objects.create(
            name='CMST 203', status='active', title='Comm', catalog_number='203',
            cohort=Cohort.objects.create(name='Comm', designator='CMST&'))
        self.asc = ApplicantSchoolCourse.objects.create(
            teacherapplication=self.app, course=course, highschool=hs, misc_info={})

    def _note(self, startswith):
        return TeacherApplicationNote.objects.get(
            teacher_application=self.app, note__startswith=startswith)

    def test_status_change_note_is_by_the_actor(self):
        self.app.status = 'Closed'
        self.app._changed_by = self.staff
        self.app.save()
        self.assertEqual(self._note('Status changed').createdby, self.staff)

    def test_status_change_without_actor_is_system(self):
        self.app.status = 'Closed'
        self.app.save()
        self.assertIsNone(self._note('Status changed').createdby)

    def test_edit_form_records_the_actor(self):
        form = EditTeacherApplicationForm({'status': 'Closed'})
        self.assertTrue(form.is_valid(), form.errors)
        form.save(self.app, changed_by=self.staff)
        self.assertEqual(self._note('Status changed').createdby, self.staff)

    def test_reviewer_added_note_is_by_the_actor(self):
        reviewer = ApplicantCourseReviewer(
            application_course=self.asc, reviewer=self.faculty)
        reviewer._changed_by = self.staff
        reviewer.save()
        self.assertEqual(self._note('Reviewer').createdby, self.staff)

    def test_reviewer_added_without_actor_is_system(self):
        ApplicantCourseReviewer.objects.create(
            application_course=self.asc, reviewer=self.faculty)
        self.assertIsNone(self._note('Reviewer').createdby)

    def test_staff_recorded_decision_is_by_the_staff_user(self):
        reviewer = ApplicantCourseReviewer.objects.create(
            application_course=self.asc, reviewer=self.faculty)
        reviewer.status = 'Approved'
        reviewer._changed_by = self.staff
        reviewer.save()
        note = TeacherApplicationNote.objects.get(
            teacher_application=self.app, note__contains='submitted decision')
        self.assertEqual(note.createdby, self.staff)

    def test_reviewer_decision_defaults_to_the_reviewer(self):
        reviewer = ApplicantCourseReviewer.objects.create(
            application_course=self.asc, reviewer=self.faculty)
        reviewer.status = 'Approved'
        reviewer.save()
        note = TeacherApplicationNote.objects.get(
            teacher_application=self.app, note__contains='submitted decision')
        self.assertEqual(note.createdby, self.faculty)


class AutoAssignedReviewerActorTests(TestCase):
    """Reviewers auto-added by a status change inherit that change's actor."""

    def test_add_reviewers_passes_the_actor_through(self):
        app = TeacherApplication(user=CustomUser(username='a'))
        app._changed_by = 'actor'
        captured = []

        class FakeReviewer:
            def __init__(self, **kwargs):
                pass

            def save(self_inner):
                captured.append(getattr(self_inner, '_changed_by', None))

        course = mock.Mock()
        course.get_faculty_coordinators.return_value = [mock.Mock(role='Faculty')]
        applied = mock.Mock(course=course)
        with mock.patch.object(
                TeacherApplication, 'selected_courses',
                new_callable=mock.PropertyMock, return_value=[applied]), \
                mock.patch(
                    'instructor_app.instructor_app.models.applicant_course_reviewer'
                    '.ApplicantCourseReviewer', FakeReviewer), \
                mock.patch(
                    'instructor_app.instructor_app.settings.inst_app_language'
                    '.inst_app_language.from_db', return_value={}):
            app.add_reviewers()
        self.assertEqual(captured, ['actor'])
