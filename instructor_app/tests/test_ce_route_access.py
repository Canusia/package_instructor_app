"""The /ce/instructor_apps/teacher_application/ routes are CE-only
(package-cis#120 port; cis v0.1.42a 53325bc / 5bc28ba).

download (PDF), download_files (zip), remind_reviewer, update_reviewer_status
and the per-application action route checked login only, so any logged-in
user holding a UUID could download an application with its private CE notes
and recommendation letters, email its reviewers, flip a reviewer's status or
edit its high school, courses, uploads, reviewers and notes. Their only
caller is the CE detail page (instructor_app/ce/details.html), so every other
role -- the applicant themself, faculty reviewers, HS admins -- is refused.
"""
from unittest import mock

from django.contrib.auth.models import AnonymousUser, Group
from django.db.models.signals import post_save
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from cis.models.course import Cohort, Course
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.models.applicant_course_reviewer import (
    ApplicantCourseReviewer,
)
from instructor_app.instructor_app.models.applicant_school_course import (
    ApplicantSchoolCourse,
)
from instructor_app.instructor_app.models.teacher_applicant import TeacherApplicant
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.signals import teacher_applications as sig

NS = 'ce_instructor_app'


def _user(name, *groups):
    user = CustomUser.objects.create(username=f'{name}@x.com', email=f'{name}@x.com')
    for g in groups:
        user.groups.add(Group.objects.get_or_create(name=g)[0])
    return user


class CeRouteAccessTests(TestCase):
    def setUp(self):
        for receiver, sender in (
                (sig.create_new_application, TeacherApplication),
                (sig.selected_new_course, ApplicantSchoolCourse),
                (sig.assign_new_reviewer, ApplicantCourseReviewer)):
            post_save.disconnect(receiver, sender=sender)
            self.addCleanup(post_save.connect, receiver, sender=sender)

        school = HighSchool.objects.create(name='HS Alpha', status='Active')
        course = Course.objects.create(
            name='ENGL& 101', status='active', title='English',
            catalog_number='101',
            cohort=Cohort.objects.create(name='101', designator='C101&'))

        self.ce = _user('ce', 'ce')
        self.reviewer = _user('rev', 'faculty')
        self.hsadmin = _user('hsadmin', 'highschool_admin')
        self.applicant = _user('applicant', 'applicant', 'instructor')
        TeacherApplicant.objects.get_or_create(user=self.applicant)
        self.app = TeacherApplication.objects.create(
            user=self.applicant, createdon=timezone.localdate(), highschool=school)
        asc = ApplicantSchoolCourse.objects.create(
            teacherapplication=self.app, course=course, highschool=school,
            misc_info={})
        self.row = ApplicantCourseReviewer.objects.create(
            application_course=asc, reviewer=self.reviewer)

        patcher = mock.patch.object(
            TeacherApplication, 'as_pdf', return_value=b'%PDF-1.4 stub')
        patcher.start()
        self.addCleanup(patcher.stop)
        notify = mock.patch.object(ApplicantCourseReviewer, 'notify_reviewer')
        self.notify = notify.start()
        self.addCleanup(notify.stop)

    def denied_users(self):
        return {
            'anonymous': AnonymousUser(),
            'applicant': self.applicant,
            'faculty reviewer': self.reviewer,
            'hs admin': self.hsadmin,
        }

    def _call(self, user, name, method='get', data=None, **kwargs):
        path = reverse(f'{NS}:{name}', kwargs=kwargs or None)
        request = getattr(RequestFactory(), method)(path, data or {})
        request.user = user
        match = resolve(path)
        return match.func(request, **match.kwargs)

    def _routes(self):
        app = {'record_id': self.app.id}
        return [
            ('download_tapp', 'get', None, app),
            ('download_tapp_files', 'get', None, app),
            ('remind_reviewer', 'get', {'reviewer_id': str(self.row.id)}, {}),
            ('update_reviewer_status', 'post',
             {'reviewer_id': str(self.row.id), 'status': 'Approved'}, {}),
            ('teacher_app_action', 'get', {'action': 'add_note'}, app),
        ]

    def test_non_ce_roles_are_refused(self):
        for who, user in self.denied_users().items():
            for name, method, data, kwargs in self._routes():
                with self.subTest(who=who, route=name):
                    response = self._call(user, name, method, data, **kwargs)
                    self.assertEqual(response.status_code, 302, response.content[:200])
                    self.assertNotIn('attachment', response.get('Content-Disposition', ''))
        self.notify.assert_not_called()
        self.row.refresh_from_db()
        self.assertNotEqual(self.row.status, 'Approved')

    def test_ce_downloads_pdf_and_zip(self):
        pdf = self._call(self.ce, 'download_tapp', record_id=self.app.id)
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        zipped = self._call(self.ce, 'download_tapp_files', record_id=self.app.id)
        self.assertEqual(zipped.status_code, 200)
        self.assertIn('attachment', zipped['Content-Disposition'])

    def test_ce_reminds_reviewer(self):
        response = self._call(self.ce, 'remind_reviewer', 'get',
                              {'reviewer_id': str(self.row.id)})
        self.assertEqual(response.status_code, 200)
        self.notify.assert_called_once()

    def test_ce_updates_reviewer_status(self):
        response = self._call(self.ce, 'update_reviewer_status', 'post',
                              {'reviewer_id': str(self.row.id), 'status': 'Approved'})
        self.assertEqual(response.status_code, 200)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, 'Approved')

    def test_ce_reaches_the_action_route(self):
        response = self._call(self.ce, 'teacher_app_action', 'get',
                              {'action': 'unknown'}, record_id=self.app.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'invalid action passed', response.content)
