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
            self.assertEqual(legacy_notes.copy_legacy_notes(), (0, 0))
            legacy_notes.delete_legacy_notes(self.app)  # must not raise

    def test_copy_keeps_ids_and_is_idempotent(self):
        created = timezone.now() - timezone.timedelta(days=30)
        old_id = uuid.uuid4()
        rows = [SimpleNamespace(
            id=old_id, teacher_application_id=self.app.id, note='Reminder sent',
            createdby_id=self.staff.id, parent=None, meta={'type': 'Private'},
            createdon=created)]
        fake = mock.MagicMock()
        fake.objects.all.return_value.iterator.side_effect = lambda: iter(rows)
        with mock.patch.object(legacy_notes, 'legacy_note_model', return_value=fake):
            self.assertEqual(legacy_notes.copy_legacy_notes(dry_run=True), (1, 0))
            self.assertFalse(TeacherApplicationNote.objects.filter(id=old_id).exists())
            self.assertEqual(legacy_notes.copy_legacy_notes(), (1, 0))
            self.assertEqual(legacy_notes.copy_legacy_notes(), (0, 1))
        note = TeacherApplicationNote.objects.get(id=old_id)
        self.assertEqual(note.createdon, created)
        self.assertEqual(note.note, 'Reminder sent')
