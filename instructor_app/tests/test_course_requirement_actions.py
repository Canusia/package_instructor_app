"""CE course-requirement bulk actions: Update modal title (#15) and delete
errors (#17)."""
from unittest import mock

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase

from cis.models.course import Course, Cohort, CourseAppRequirement
from cis.models.customuser import CustomUser
from instructor_app.instructor_app.views.ce import course_requirements as views


class CourseRequirementActionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(username='ce@x.com', email='ce@x.com')
        course = Course.objects.create(
            name='ENG 101', status='active', title='English', catalog_number='101',
            cohort=Cohort.objects.create(name='101', designator='C101'))
        self.req = CourseAppRequirement.objects.create(course=course, name='Transcript')

    def _request(self, method, data):
        factory = RequestFactory()
        request = getattr(factory, method)('/ce/courses/requirements/', data)
        request.user = self.user
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def test_update_modal_title_names_the_action(self):
        request = self._request('get', {'ids[]': [str(self.req.id)]})
        with mock.patch.object(views, 'render', return_value=mock.sentinel.page) as render:
            views.update_req_status(request)
        context = render.call_args.args[2]
        self.assertEqual(context['title'], 'Update Course Application Requirement')

    def test_delete_removes_the_requirement(self):
        response = views.delete_req(self._request(
            'post', {'ids': [str(self.req.id)], 'action': 'delete_req'}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CourseAppRequirement.objects.filter(pk=self.req.pk).exists())

    def test_failed_delete_is_reported(self):
        with mock.patch.object(
                CourseAppRequirement, 'delete', side_effect=RuntimeError('db says no')):
            response = views.delete_req(self._request(
                'post', {'ids': [str(self.req.id)], 'action': 'delete_req'}))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Transcript', response.content)
        self.assertNotIn(b'Successfully', response.content)

    def test_already_deleted_requirement_is_reported(self):
        missing_id = str(self.req.id)
        self.req.delete()
        response = views.delete_req(self._request(
            'post', {'ids': [missing_id], 'action': 'delete_req'}))
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(b'Successfully', response.content)
