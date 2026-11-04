"""CE course-requirement bulk actions: Update modal title (#15) and delete
errors (#17)."""
import json
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

    def test_failure_payload_matches_the_modal_and_is_escaped(self):
        CourseAppRequirement.objects.filter(pk=self.req.pk).update(name='<b>x</b>')
        with mock.patch.object(
                CourseAppRequirement, 'delete', side_effect=RuntimeError('<i>boom</i>')):
            response = views.delete_req(self._request(
                'post', {'ids': [str(self.req.id)], 'action': 'delete_req'}))
        body = json.loads(response.content)
        message = json.loads(body['errors'])['__all__'][0]['message']
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', message)
        self.assertIn('&lt;i&gt;boom&lt;/i&gt;', message)
        self.assertNotIn('<b>', message)

    def test_delete_modal_opens_for_a_requirement_without_a_course(self):
        orphan = CourseAppRequirement.objects.create(course=None, name='Photo ID')
        for view in (views.delete_req, views.update_req_status):
            request = self._request('get', {'ids[]': [str(orphan.id), 'junk']})
            with mock.patch.object(views, 'render', return_value=mock.sentinel.page) as render:
                view(request)
            labels = [label for _v, label in render.call_args.args[2]['form'].fields['ids'].choices]
            self.assertEqual(labels, ['Photo ID'])
