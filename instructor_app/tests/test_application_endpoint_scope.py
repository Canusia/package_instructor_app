"""HS admins and faculty+HS admins on the /ce/instructor_apps/ feeds
(package-cis#120 port).

These endpoints already scope every non-CE caller to the applications they are
an assigned reviewer on (package_instructor_app#7), which is stricter than the
cis rule (own-school applications for HS admins). Holding the highschool_admin
role, or both roles, must not widen that: no `course=` / `reviewer=` value
reaches another school's applications.
"""
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.test import TestCase
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
from instructor_app.instructor_app.models.teacher_applicant import TeacherApplicant
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.signals import teacher_applications as sig
from instructor_app.instructor_app.views.ce import viewsets


def _course(catalog):
    return Course.objects.create(
        name=f'ENGL& {catalog}', status='active', title=f'T{catalog}',
        catalog_number=catalog,
        cohort=Cohort.objects.create(name=catalog, designator=f'C{catalog}&'))


def _user(name, *groups):
    user = CustomUser.objects.create(username=f'{name}@x.com', email=f'{name}@x.com')
    for g in groups:
        user.groups.add(Group.objects.get_or_create(name=g)[0])
    return user


class EndpointScopeTests(TestCase):
    def setUp(self):
        for receiver, sender in (
                (sig.create_new_application, TeacherApplication),
                (sig.selected_new_course, ApplicantSchoolCourse),
                (sig.assign_new_reviewer, ApplicantCourseReviewer)):
            post_save.disconnect(receiver, sender=sender)
            self.addCleanup(post_save.connect, receiver, sender=sender)
        Group.objects.get_or_create(name='applicant')

        self.hs_a = HighSchool.objects.create(name='HS Alpha', status='Active')
        self.hs_b = HighSchool.objects.create(name='HS Beta', status='Active')
        self.eng = _course('101')
        self.hsadmin = _user('hsadmin', 'highschool_admin')
        self.both = _user('both', 'faculty', 'highschool_admin')
        self.ce = _user('ce', 'ce')
        self.rev = _user('rev', 'faculty')

        self.app_a, self.row_a = self._app('appa', self.hs_a, self.rev)
        self.app_b, self.row_b = self._app('appb', self.hs_b, self.rev)
        # The `both` user reviews only HS Beta's application.
        self.app_both, self.row_both = self._app('appboth', self.hs_b, self.both)

    def _app(self, tag, school, reviewer):
        applicant = CustomUser.objects.create(username=f'{tag}@x.com', email=f'{tag}@x.com')
        TeacherApplicant.objects.get_or_create(user=applicant)
        app = TeacherApplication.objects.create(
            user=applicant,
            createdon=timezone.localdate(), highschool=school)
        asc = ApplicantSchoolCourse.objects.create(
            teacherapplication=app, course=self.eng, highschool=school, misc_info={})
        return app, ApplicantCourseReviewer.objects.create(
            application_course=asc, reviewer=reviewer)

    def _ids(self, viewset, user, params=''):
        request = APIRequestFactory().get(f'/x/?{params}')
        force_authenticate(request, user=user)
        response = viewset.as_view({'get': 'list'})(request)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        rows = data.get('results', data) if isinstance(data, dict) else data
        return {str(row['id']) for row in rows}

    def _s(self, *objs):
        return {str(o.id) for o in objs}

    # TeacherApplicationViewSet

    def test_hsadmin_application_feed_is_empty_without_reviews(self):
        V = viewsets.TeacherApplicationViewSet
        self.assertEqual(self._ids(V, self.hsadmin), set())

    def test_hsadmin_params_cannot_widen_application_feed(self):
        V = viewsets.TeacherApplicationViewSet
        for params in (f'course={self.eng.id}', f'reviewer={self.rev.id}',
                       'course=-2', f'cohort={self.eng.cohort_id}'):
            self.assertEqual(self._ids(V, self.hsadmin, params), set(), params)

    def test_faculty_plus_hsadmin_application_feed_is_their_reviews(self):
        V = viewsets.TeacherApplicationViewSet
        self.assertEqual(self._ids(V, self.both), self._s(self.app_both))
        self.assertEqual(
            self._ids(V, self.both, f'reviewer={self.rev.id}'), set())
        self.assertEqual(
            self._ids(V, self.both, f'course={self.eng.id}'), self._s(self.app_both))

    def test_ce_application_feed_unchanged(self):
        V = viewsets.TeacherApplicationViewSet
        self.assertEqual(self._ids(V, self.ce),
                         self._s(self.app_a, self.app_b, self.app_both))

    # TeacherApplicationReviewerViewSet

    def test_hsadmin_reviewer_feed_is_empty_without_reviews(self):
        V = viewsets.TeacherApplicationReviewerViewSet
        self.assertEqual(self._ids(V, self.hsadmin), set())
        self.assertEqual(self._ids(V, self.hsadmin, f'course={self.eng.id}'), set())

    def test_faculty_plus_hsadmin_reviewer_feed_is_their_rows(self):
        V = viewsets.TeacherApplicationReviewerViewSet
        self.assertEqual(self._ids(V, self.both), self._s(self.row_both))

    def test_ce_reviewer_feed_unchanged(self):
        V = viewsets.TeacherApplicationReviewerViewSet
        self.assertEqual(self._ids(V, self.ce),
                         self._s(self.row_a, self.row_b, self.row_both))

    # TeacherApplicantViewSet

    def test_hsadmin_applicant_feed_empty_and_union_limited(self):
        V = viewsets.TeacherApplicantViewSet
        self.assertEqual(self._ids(V, self.hsadmin), set())
        self.assertEqual(len(self._ids(V, self.both)), 1)

    def test_ce_applicant_feed_sees_all(self):
        self.assertEqual(len(self._ids(viewsets.TeacherApplicantViewSet, self.ce)), 3)
