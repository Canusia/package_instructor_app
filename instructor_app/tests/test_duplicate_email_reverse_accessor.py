"""
Regression tests for the stale `user.teacherapplicant` reverse accessor.

Migration 0003 renamed TeacherApplicant.user's related_name to
`inst_app_teacherapplicant`, but two call sites kept the old accessor:

  * forms/teacher_applicant.py::TeacherApplicantVerifyEmailForm.clean_email
  * views/ce/bulk_actions.py::_get_applicants_from_ids

The symptom depends on the deployment:

  * Where the legacy `cis.models.teacher_applicant` module is never
    imported, `user.teacherapplicant` raises AttributeError — a 500 on
    every duplicate-email submission, and the CE bulk actions break.
  * On tenants like ewu, `cis/signals/teacher_applications.py` imports
    that module, so the legacy `cis.TeacherApplicant` is registered and
    claims the default `teacherapplicant` accessor. No crash — the code
    silently consults the *wrong model*, so the resend-verification
    branch never fires for an instructor_app applicant.

See Canusia/package_instructor_app#1.
"""
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase

from cis.models.customuser import CustomUser
from instructor_app.instructor_app.forms.teacher_applicant import (
    TeacherApplicantVerifyEmailForm,
)
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
)


def make_user(email='dupe@example.com'):
    Group.objects.get_or_create(name='applicant')
    return CustomUser.objects.create(
        username=email, email=email, first_name='Test', last_name='User',
    )


@contextmanager
def no_welcome_email():
    """The TeacherApplication post_save receiver needs configured email
    settings; these tests only care about the reverse accessor."""
    from django.db.models.signals import post_save

    from instructor_app.instructor_app.signals.teacher_applications import (
        create_new_application,
    )

    post_save.disconnect(create_new_application, sender=TeacherApplication)
    try:
        yield
    finally:
        post_save.connect(create_new_application, sender=TeacherApplication)


def clean_email_for(value):
    """Drive clean_email directly — the full form carries a ReCaptchaField."""
    form = TeacherApplicantVerifyEmailForm()
    form.cleaned_data = {'email': value}
    return form.clean_email()


class CleanEmailExistingUserTests(TestCase):

    def test_existing_user_without_applicant_raises_already_registered(self):
        make_user()

        with self.assertRaises(ValidationError) as ctx:
            clean_email_for('dupe@example.com')

        self.assertIn('already registered', str(ctx.exception))

    def test_existing_user_with_verified_applicant_is_routed_to_login(self):
        """Copy changed when existing users became able to apply — the point
        here is still that the accessor resolves instead of raising
        AttributeError."""
        user = make_user()
        TeacherApplicant.objects.create(user=user, account_verified=True)

        with self.assertRaises(ValidationError) as ctx:
            clean_email_for('dupe@example.com')

        self.assertIn('log in', str(ctx.exception))

    def test_existing_user_with_unverified_applicant_resends_verification(self):
        user = make_user()
        TeacherApplicant.objects.create(user=user, account_verified=False)

        with patch.object(
            TeacherApplicant, 'send_verification_request_email'
        ) as mock_send:
            with self.assertRaises(ValidationError) as ctx:
                clean_email_for('dupe@example.com')

        mock_send.assert_called_once()
        self.assertIn('verification email has been resent', str(ctx.exception))

    def test_match_is_case_insensitive(self):
        make_user('MiXeD@example.com')

        with self.assertRaises(ValidationError):
            clean_email_for('mixed@example.com')

    def test_unused_email_passes_through_lowercased(self):
        self.assertEqual(clean_email_for('Fresh@Example.com'), 'fresh@example.com')


class BulkActionApplicantLookupTests(TestCase):

    def test_application_id_resolves_to_its_applicant(self):
        from instructor_app.instructor_app.views.ce.bulk_actions import (
            _get_applicants_from_ids,
        )

        user = make_user('bulk@example.com')
        applicant = TeacherApplicant.objects.create(user=user)
        with no_welcome_email():
            application = TeacherApplication.objects.create(
                user=user, createdon=date.today(),
            )

        result = _get_applicants_from_ids([str(application.id)])

        self.assertEqual([a.id for a in result], [applicant.id])

    def test_application_without_applicant_is_skipped(self):
        from instructor_app.instructor_app.views.ce.bulk_actions import (
            _get_applicants_from_ids,
        )

        user = make_user('noapplicant@example.com')
        with no_welcome_email():
            application = TeacherApplication.objects.create(
                user=user, createdon=date.today(),
            )

        self.assertEqual(_get_applicants_from_ids([str(application.id)]), [])
