"""The CE Checklist field follows the "Instructor Application Page" setting.

A tenant that removes every checklist item ("[]") does not use the checklist,
so the field must disappear. Only a setting that was never saved falls back to
the built-in items (package_instructor_app#3).
"""
from django.test import TestCase

from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    EditTeacherApplicationForm,
)

DEFAULT_ITEMS = [
    'Class Assigned', 'Hotel Room Requested', 'NetID Activated', 'Imported into PS',
]


class ChecklistConfigTests(TestCase):
    def _set(self, **value):
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': value})

    def _form(self):
        return EditTeacherApplicationForm()

    def test_cleared_config_removes_the_field(self):
        self._set(checklist_config='[]')
        self.assertNotIn('checklist', self._form().fields)

    def test_cleared_config_stored_as_a_list_removes_the_field(self):
        self._set(checklist_config=[])
        self.assertNotIn('checklist', self._form().fields)

    def test_never_saved_config_uses_defaults(self):
        self._set()
        choices = [v for v, _l in self._form().fields['checklist'].choices]
        self.assertEqual(choices, DEFAULT_ITEMS)

    def test_blank_config_uses_defaults(self):
        # A CharField saved before the checklist UI existed stores ''.
        self._set(checklist_config='')
        choices = [v for v, _l in self._form().fields['checklist'].choices]
        self.assertEqual(choices, DEFAULT_ITEMS)

    def test_configured_items_are_used(self):
        self._set(checklist_config='[{"value": "Badge", "label": "Badge Issued"}]')
        self.assertEqual(
            self._form().fields['checklist'].choices, [('Badge', 'Badge Issued')])


class ChecklistSaveTests(TestCase):
    """Saving with the field hidden must not wipe a previously recorded checklist."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from django.utils import timezone
        from cis.models.customuser import CustomUser
        from instructor_app.instructor_app.models.teacher_applicant import (
            TeacherApplication,
        )
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': {
                'new_applicant_email_subject': 'Started',
                'new_applicant_email': '<p>Welcome</p>',
                'internal_notify_on': [],
                'course_selected_email_recipient': '',
            }})
        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=user, createdon=timezone.localdate(),
            misc_info={'checklist': ['Class Assigned']})

    def test_hidden_checklist_keeps_stored_value(self):
        Setting.objects.update_or_create(
            key='inst_app_language', defaults={'value': {'checklist_config': '[]'}})
        form = EditTeacherApplicationForm({'status': self.app.status})
        self.assertTrue(form.is_valid(), form.errors)
        form.save(self.app)
        self.app.refresh_from_db()
        self.assertEqual(self.app.misc_info.get('checklist'), ['Class Assigned'])
