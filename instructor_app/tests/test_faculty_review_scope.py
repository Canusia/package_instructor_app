"""The faculty review page and the application feeds are scoped to the
caller's own reviewer rows (package_instructor_app#7).

Holding the faculty role is not enough: a faculty user who reviews no course on
an application gets a 404 for it, cannot record a decision on a colleague's
reviewer row, and the list feeds only return applications they review.
"""
from unittest import mock

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from cis.models.course import Course, Cohort
from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.models.applicant_course_reviewer import (
    ApplicantCourseReviewer,
)
from instructor_app.instructor_app.models.applicant_school_course import (
    ApplicantSchoolCourse,
)
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.signals import teacher_applications as sig
from instructor_app.instructor_app.views.ce import viewsets
from instructor_app.instructor_app.views.faculty import home as faculty_views


def _course(catalog):
    return Course.objects.create(
        name=f'ENGL& {catalog}', status='active', title=f'T{catalog}',
        catalog_number=catalog,
        cohort=Cohort.objects.create(name=catalog, designator=f'C{catalog}&'))


def _user(name, group):
    user = CustomUser.objects.create(username=f'{name}@x.com', email=f'{name}@x.com')
    user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


class _Base(TestCase):
    def setUp(self):
        for receiver, sender in (
                (sig.create_new_application, TeacherApplication),
                (sig.selected_new_course, ApplicantSchoolCourse),
                (sig.assign_new_reviewer, ApplicantCourseReviewer)):
            post_save.disconnect(receiver, sender=sender)
            self.addCleanup(post_save.connect, receiver, sender=sender)

        Group.objects.get_or_create(name='applicant')
        self.reviewer_a = _user('ra', 'faculty')
        self.reviewer_b = _user('rb', 'faculty')
        self.stranger = _user('st', 'faculty')
        self.ce = _user('ce', 'ce')
        hs = HighSchool.objects.create(name='HS', status='Active')

        self.app = TeacherApplication.objects.create(
            user=CustomUser.objects.create(username='a@x.com', email='a@x.com'),
            createdon=timezone.localdate())
        self.rows = {}
        for course, reviewer in ((_course('101'), self.reviewer_a),
                                 (_course('201'), self.reviewer_b)):
            asc = ApplicantSchoolCourse.objects.create(
                teacherapplication=self.app, course=course, highschool=hs, misc_info={})
            self.rows[reviewer] = ApplicantCourseReviewer.objects.create(
                application_course=asc, reviewer=reviewer)

        # An application only reviewer_b reviews.
        self.other_app = TeacherApplication.objects.create(
            user=CustomUser.objects.create(username='b@x.com', email='b@x.com'),
            createdon=timezone.localdate())
        ApplicantCourseReviewer.objects.create(
            reviewer=self.reviewer_b,
            application_course=ApplicantSchoolCourse.objects.create(
                teacherapplication=self.other_app, course=_course('301'),
                highschool=hs, misc_info={}))


class ReviewPageScopeTests(_Base):
    def _call(self, user, method='get', data=None, app=None):
        factory = RequestFactory()
        app = app or self.app
        request = getattr(factory, method)(f'/faculty/instructor_apps/{app.id}', data or {})
        request.user = user
        request._messages = mock.MagicMock()
        with mock.patch.object(faculty_views, 'render', return_value=HttpResponse('ok')) as render, \
                mock.patch.object(faculty_views, 'draw_menu', return_value=''), \
                mock.patch.object(faculty_views, 'portal_lang'):
            response = faculty_views.review_application(request, app.id)
        return response, render

    def _decide(self, user, row, decision='Approved'):
        return self._call(user, 'post', {
            'application_course_id': str(row.id), 'decision': decision, 'comment': 'c'})

    def test_non_reviewer_gets_404(self):
        with self.assertRaises(Http404):
            self._call(self.stranger)

    def test_reviewer_of_another_application_gets_404(self):
        with self.assertRaises(Http404):
            self._call(self.reviewer_a, app=self.other_app)

    def test_reviewer_sees_only_their_own_courses(self):
        _response, render = self._call(self.reviewer_a)
        context = render.call_args.args[2]
        self.assertEqual(
            [cr.id for cr, _form in context['courses_with_forms']],
            [self.rows[self.reviewer_a].id])

    def test_reviewer_records_their_own_decision(self):
        self._decide(self.reviewer_a, self.rows[self.reviewer_a])
        self.rows[self.reviewer_a].refresh_from_db()
        self.assertEqual(self.rows[self.reviewer_a].status, 'Approved')

    def test_cannot_decide_a_colleagues_row(self):
        with self.assertRaises(Http404):
            self._decide(self.reviewer_a, self.rows[self.reviewer_b], 'Declined')
        self.rows[self.reviewer_b].refresh_from_db()
        self.assertEqual(self.rows[self.reviewer_b].status, '---')

    def test_malformed_row_id_is_404_not_500(self):
        with self.assertRaises(Http404):
            self._call(self.reviewer_a, 'post', {
                'application_course_id': 'not-a-uuid', 'decision': 'Approved'})


class FeedScopeTests(_Base):
    def _ids(self, viewset, user, params=''):
        request = APIRequestFactory().get(f'/x/?{params}')
        force_authenticate(request, user=user)
        view = viewset.as_view({'get': 'list'})
        response = view(request)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        rows = data.get('results', data) if isinstance(data, dict) else data
        return {str(row['id']) for row in rows}

    def test_faculty_application_feed_ignores_the_reviewer_param(self):
        self.assertEqual(
            self._ids(viewsets.TeacherApplicationViewSet, self.reviewer_a),
            {str(self.app.id)})
        # Asking for a colleague's reviews does not widen the result: the
        # application only reviewer_b reviews stays out.
        self.assertEqual(
            self._ids(viewsets.TeacherApplicationViewSet, self.reviewer_a,
                      f'reviewer={self.reviewer_b.id}'),
            {str(self.app.id)})

    def test_non_reviewing_faculty_sees_no_applications(self):
        self.assertEqual(
            self._ids(viewsets.TeacherApplicationViewSet, self.stranger), set())

    def test_ce_sees_every_application(self):
        self.assertTrue({str(self.app.id), str(self.other_app.id)}
                        <= self._ids(viewsets.TeacherApplicationViewSet, self.ce))

    def test_faculty_reviewer_feed_is_their_own_rows(self):
        self.assertEqual(
            self._ids(viewsets.TeacherApplicationReviewerViewSet, self.reviewer_a),
            {str(self.rows[self.reviewer_a].id)})

    def test_faculty_applicant_feed_is_their_reviewed_applicants(self):
        self.assertEqual(
            self._ids(viewsets.TeacherApplicantViewSet, self.stranger), set())
