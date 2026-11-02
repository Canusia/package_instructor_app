"""The applicant's note-reply page (package-cis#120 port; cis 53325bc).

`ce_instructor_app:teacher_app_note_reply` is open without a login on
purpose: TeacherApplicationNote.teacher_reply_url is emailed to the applicant
for a 'to_instructor' note and the reply is saved as the applicant. The note
UUID is the credential, so the page serves only threads that were sent to the
applicant -- a root or child note of type 'to_instructor' or 'public'. A
private CE note thread is a 404, on GET and on POST.
"""
from unittest import mock

from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.db.models.signals import post_save
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from instructor_app.instructor_app.forms.teacher_applicant import NoteReplyForm
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.models.teacher_application_note import (
    TeacherApplicationNote,
)
from instructor_app.instructor_app.signals import teacher_applications as sig
from instructor_app.instructor_app.views.ce import actions


class _NoCaptchaReplyForm(NoteReplyForm):
    """The reply form without its captcha, so a POST can be valid here."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('captcha', None)


class NoteReplyAccessTests(TestCase):
    def setUp(self):
        post_save.disconnect(sig.create_new_application, sender=TeacherApplication)
        self.addCleanup(post_save.connect, sig.create_new_application,
                        sender=TeacherApplication)
        post_save.disconnect(sig.teacher_application_note_added,
                             sender=TeacherApplicationNote)
        self.addCleanup(post_save.connect, sig.teacher_application_note_added,
                        sender=TeacherApplicationNote)
        Group.objects.get_or_create(name='applicant')
        self.ce = CustomUser.objects.create(username='ce@x.com', email='ce@x.com')
        self.applicant = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=self.applicant, createdon=timezone.localdate(),
            highschool=HighSchool.objects.create(name='HS', status='Active'))

    def _note(self, kind, parent=None):
        return TeacherApplicationNote.objects.create(
            teacher_application=self.app, note=f'{kind} note', createdby=self.ce,
            parent=parent.id if parent else None, meta={'type': kind})

    def _call(self, note, method='get', data=None):
        path = reverse('ce_instructor_app:teacher_app_note_reply',
                       kwargs={'note_id': note.id})
        request = getattr(RequestFactory(), method)(path, data or {})
        request.user = AnonymousUser()
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        match = resolve(path)
        return match.func(request, **match.kwargs)

    def _post(self, note):
        with mock.patch.object(actions, 'NoteReplyForm', _NoCaptchaReplyForm):
            return self._call(note, 'post', {'message': 'my reply'})

    def test_private_thread_is_404_on_get_and_post(self):
        root = self._note('private')
        self._note('private', parent=root)
        with self.assertRaises(Http404):
            self._call(root)
        with self.assertRaises(Http404):
            self._post(root)
        self.assertFalse(TeacherApplicationNote.objects.filter(
            meta__type='response').exists())

    def test_note_without_type_is_404(self):
        root = TeacherApplicationNote.objects.create(
            teacher_application=self.app, note='x', createdby=self.ce, meta=None)
        with self.assertRaises(Http404):
            self._call(root)

    def test_to_instructor_root_is_served_and_reply_saved_as_applicant(self):
        root = self._note('to_instructor')
        self.assertEqual(self._call(root).status_code, 200)
        response = self._post(root)
        self.assertEqual(response.status_code, 302)
        reply = TeacherApplicationNote.objects.get(meta__type='response')
        self.assertEqual(reply.createdby, self.applicant)
        self.assertEqual(reply.parent, root.id)

    def test_private_root_with_an_applicant_facing_child_is_served(self):
        for kind in ('to_instructor', 'public'):
            with self.subTest(kind=kind):
                root = self._note('private')
                self._note(kind, parent=root)
                self.assertEqual(self._call(root).status_code, 200)

    def test_public_root_is_served(self):
        self.assertEqual(self._call(self._note('public')).status_code, 200)
