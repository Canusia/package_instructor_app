"""Application notes live in one table, instructor_app's (#11).

Applicant replies, faculty-visible public notes and reminder audit notes used
to go to the host's cis.TeacherApplicationNote, so the CE notes list never
showed them. Legacy rows are copied over by copy_legacy_application_notes.
"""
from types import SimpleNamespace
from unittest import mock
import uuid

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.test import TestCase
from django.utils import timezone

from cis.models.customuser import CustomUser
from instructor_app.instructor_app.forms.teacher_applicant import NoteReplyForm
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.models.teacher_application_note import (
    TeacherApplicationNote,
)
from instructor_app.instructor_app.services import legacy_notes
from instructor_app.instructor_app.signals import teacher_applications as sig


class SingleNoteTableTests(TestCase):
    def setUp(self):
        post_save.disconnect(sig.create_new_application, sender=TeacherApplication)
        self.addCleanup(post_save.connect, sig.create_new_application, sender=TeacherApplication)
        Group.objects.get_or_create(name='applicant')
        self.staff = CustomUser.objects.create(username='staff@x.com', email='staff@x.com')
        applicant = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=applicant, createdon=timezone.localdate(), status='Submitted', misc_info={})

    def test_applicant_reply_lands_in_package_table(self):
        parent = TeacherApplicationNote.objects.create(
            teacher_application=self.app, note='Please send transcripts',
            createdby=self.staff, meta={'type': 'private'})
        form = NoteReplyForm(parent)
        form.cleaned_data = {'message': 'Sent them'}
        reply = form.save(None, parent)

        self.assertIsInstance(reply, TeacherApplicationNote)
        ce_list = TeacherApplicationNote.objects.filter(teacher_application=self.app)
        self.assertIn(reply, ce_list)
        self.assertEqual(reply.parent, parent.id)

    def test_every_writer_and_reader_uses_package_model(self):
        from instructor_app.instructor_app.services import (
            incomplete_notifications, pending_review_notifications,
        )
        from instructor_app.instructor_app.views.faculty import home
        from instructor_app.instructor_app.forms import teacher_applicant
        for module in (incomplete_notifications, pending_review_notifications,
                       home, teacher_applicant):
            self.assertIs(module.TeacherApplicationNote, TeacherApplicationNote,
                          module.__name__)

    def test_no_legacy_table_on_this_tenant_is_a_no_op(self):
        with mock.patch.object(legacy_notes, 'legacy_note_model', return_value=None):
            self.assertEqual(legacy_notes.copy_legacy_notes(), (0, 0, 0))
            legacy_notes.delete_legacy_notes(self.app)  # must not raise

    def test_ewu_cis_note_model_is_not_legacy(self):
        # ewu's cis.TeacherApplicationNote points at cis.TeacherApplication.
        self.assertIsNone(legacy_notes.legacy_note_model())

    def _legacy(self, rows):
        fake = mock.MagicMock()
        fake.objects.all.return_value.iterator.side_effect = lambda: iter(rows)
        return mock.patch.object(legacy_notes, 'legacy_note_model', return_value=fake)

    def _row(self, **over):
        row = dict(id=uuid.uuid4(), teacher_application_id=self.app.id, note='Old note',
                   createdby_id=self.staff.id, parent=None, meta={'type': 'Private'},
                   createdon=timezone.now() - timezone.timedelta(days=30))
        row.update(over)
        return SimpleNamespace(**row)

    def test_copy_keeps_ids_and_is_idempotent(self):
        row = self._row()
        with self._legacy([row]):
            self.assertEqual(legacy_notes.copy_legacy_notes(dry_run=True), (1, 0, 0))
            self.assertFalse(TeacherApplicationNote.objects.filter(id=row.id).exists())
            self.assertEqual(legacy_notes.copy_legacy_notes(), (1, 0, 0))
            self.assertEqual(legacy_notes.copy_legacy_notes(), (0, 1, 0))
        note = TeacherApplicationNote.objects.get(id=row.id)
        self.assertEqual(note.createdon, row.createdon)
        self.assertEqual(note.note, 'Old note')

    def test_copy_sends_no_email_and_raises_no_alert(self):
        rows = [self._row(meta={'type': 'to_instructor'}),
                self._row(meta={'type': 'response'}, parent=uuid.uuid4())]
        with self._legacy(rows), \
                mock.patch.object(sig, 'teacher_application_note_added') as handler:
            post_save.disconnect(sig.teacher_application_note_added, sender=TeacherApplicationNote)
            post_save.connect(handler, sender=TeacherApplicationNote)
            try:
                self.assertEqual(legacy_notes.copy_legacy_notes()[0], 2)
            finally:
                post_save.disconnect(handler, sender=TeacherApplicationNote)
                post_save.connect(sig.teacher_application_note_added, sender=TeacherApplicationNote)
        handler.assert_not_called()

    def test_rows_without_application_are_skipped(self):
        rows = [self._row(), self._row(teacher_application_id=None)]
        with self._legacy(rows):
            self.assertEqual(legacy_notes.copy_legacy_notes(), (1, 0, 1))

    # --- CE Reply button (#11) ----------------------------------------------

    def _ce_request(self, method='get', query='', data=None):
        from django.test import RequestFactory
        request = getattr(RequestFactory(), method)(f'/x{query}', data or {})
        request.user = self.staff
        return request

    def test_ce_reply_is_saved_in_package_table_with_parent(self):
        from instructor_app.instructor_app.views.ce import actions
        root = TeacherApplicationNote.objects.create(
            teacher_application=self.app, note='Q', createdby=self.staff,
            meta={'type': 'private'})
        with mock.patch.object(actions, 'render') as render:
            actions.add_note(self._ce_request(query=f'?parent={root.id}'), self.app.id)
        form = render.call_args[0][2]['form']
        self.assertEqual(str(form.initial['parent']), str(root.id))

        with mock.patch.object(sig, 'notes_email') as notes_email:
            notes_email.from_db.return_value = {'is_active': 'No'}
            response = actions.add_note(self._ce_request(
                'post', data={'note': 'Thanks', 'type': 'to_instructor',
                              'parent': str(root.id)}), self.app.id)
        self.assertEqual(response.status_code, 200, response.content)
        reply = TeacherApplicationNote.objects.get(note='Thanks')
        self.assertEqual(reply.parent, root.id)

    def test_ce_reply_rejects_parent_from_another_application(self):
        from instructor_app.instructor_app.views.ce import actions
        other_user = CustomUser.objects.create(username='b@x.com', email='b@x.com')
        other = TeacherApplication.objects.create(
            user=other_user, createdon=timezone.localdate(), status='Submitted', misc_info={})
        foreign = TeacherApplicationNote.objects.create(
            teacher_application=other, note='Other', createdby=self.staff,
            meta={'type': 'private'})
        response = actions.add_note(self._ce_request(
            'post', data={'note': 'X', 'parent': str(foreign.id)}), self.app.id)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TeacherApplicationNote.objects.filter(note='X').exists())

    def test_reply_button_uses_package_action(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates',
                            'instructor_app', 'ce', 'details.html')
        with open(path) as fh:
            src = fh.read()
        self.assertNotIn('data-model="teacherapplicationnote"', src)
        self.assertIn('?parent={{ r.parent|default:r.id }}', src)
