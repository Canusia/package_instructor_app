"""
An existing non-applicant user can start an instructor application.

Scope doc: docs/plans/2026-08-08-instructor-app-existing-user-can-apply.md

Rules under test:
  * student / instructor / highschool_admin (and users with no groups) may apply
  * ce and faculty may not, unless they also hold an eligible role (allow-wins)
  * an existing applicant is told to log in or reset their password
  * attaching an applicant never touches the account's password or profile
  * the complete-app step prefills from the user record, minus SSN and DOB,
    and a blank submission does not erase the stored values
  * a live prior application is resumed; a terminal one is not
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
from instructor_app.instructor_app.services.applicant_eligibility import (
    existing_user_may_apply,
)
from instructor_app.instructor_app.services.applications import (
    start_or_resume_application,
)

ALL_ROLES = [
    'applicant', 'ce', 'district_admin', 'faculty',
    'highschool_admin', 'instructor', 'student', 'speaker',
]


def make_user(email='existing@example.com', roles=(), **kwargs):
    for name in ALL_ROLES:
        Group.objects.get_or_create(name=name)
    user = CustomUser.objects.create(
        username=email, email=email, first_name='Pat', last_name='Existing',
        **kwargs
    )
    for role in roles:
        user.groups.add(Group.objects.get(name=role))
    return user


@contextmanager
def no_welcome_email():
    from django.db.models.signals import post_save

    from instructor_app.instructor_app.signals.teacher_applications import (
        create_new_application,
    )

    post_save.disconnect(create_new_application, sender=TeacherApplication)
    try:
        yield
    finally:
        post_save.connect(create_new_application, sender=TeacherApplication)


@contextmanager
def no_login_history():
    """force_login fires django_login_history, which needs a real REMOTE_ADDR."""
    from django.contrib.auth.signals import user_logged_in
    from django_login_history.models import post_login

    user_logged_in.disconnect(post_login)
    try:
        yield
    finally:
        user_logged_in.connect(post_login)


def make_application(user, status='In Progress', createdon=None):
    with no_welcome_email():
        return TeacherApplication.objects.create(
            user=user,
            createdon=createdon or date.today(),
            status=status,
            misc_info={},
        )


def clean_email_for(value, allow=True):
    form = TeacherApplicantVerifyEmailForm()
    form.cleaned_data = {'email': value}
    with patch.object(
        TeacherApplicantVerifyEmailForm, '_existing_users_may_apply',
        staticmethod(lambda: allow),
    ):
        return form, form.clean_email()


class EligibilityRuleTests(TestCase):

    def test_eligible_roles_may_apply(self):
        for role in ['student', 'instructor', 'highschool_admin']:
            with self.subTest(role=role):
                user = make_user(f'{role}@example.com', roles=[role])
                self.assertTrue(existing_user_may_apply(user))

    def test_staff_and_faculty_may_not_apply(self):
        for role in ['ce', 'faculty']:
            with self.subTest(role=role):
                user = make_user(f'{role}@example.com', roles=[role])
                self.assertFalse(existing_user_may_apply(user))

    def test_allow_wins_when_user_holds_both(self):
        user = make_user('both@example.com', roles=['instructor', 'ce'])
        self.assertTrue(existing_user_may_apply(user))

    def test_user_with_no_groups_may_apply(self):
        user = make_user('nogroups@example.com', roles=[])
        self.assertTrue(existing_user_may_apply(user))

    def test_other_roles_are_denied(self):
        for role in ['district_admin', 'speaker']:
            with self.subTest(role=role):
                user = make_user(f'{role}@example.com', roles=[role])
                self.assertFalse(existing_user_may_apply(user))

    def test_existing_applicant_is_not_eligible_via_this_path(self):
        user = make_user('appl@example.com', roles=['applicant', 'student'])
        self.assertFalse(existing_user_may_apply(user))


class CleanEmailTests(TestCase):

    def test_eligible_user_passes_and_is_stashed(self):
        user = make_user(roles=['instructor'])
        form, cleaned = clean_email_for('existing@example.com')
        self.assertEqual(cleaned, 'existing@example.com')
        self.assertEqual(form.existing_user.pk, user.pk)

    def test_denied_role_still_raises(self):
        make_user(roles=['faculty'])
        with self.assertRaises(ValidationError) as ctx:
            clean_email_for('existing@example.com')
        self.assertIn('already registered', str(ctx.exception))

    def test_verified_applicant_is_told_to_login_or_reset(self):
        user = make_user(roles=['student'])
        TeacherApplicant.objects.create(user=user, account_verified=True)
        with self.assertRaises(ValidationError) as ctx:
            clean_email_for('existing@example.com')
        message = str(ctx.exception)
        self.assertIn('log in', message)
        self.assertIn('reset your password', message)

    def test_unverified_applicant_still_gets_a_resend(self):
        user = make_user(roles=['student'])
        TeacherApplicant.objects.create(user=user, account_verified=False)
        with patch.object(TeacherApplicant, 'send_verification_request_email') as mock_send:
            with self.assertRaises(ValidationError) as ctx:
                clean_email_for('existing@example.com')
        mock_send.assert_called_once()
        self.assertIn('resent', str(ctx.exception))

    def test_toggle_off_restores_the_hard_stop(self):
        make_user(roles=['instructor'])
        with self.assertRaises(ValidationError) as ctx:
            clean_email_for('existing@example.com', allow=False)
        self.assertIn('already registered', str(ctx.exception))

    def test_unknown_email_is_unaffected(self):
        _form, cleaned = clean_email_for('brand-new@example.com')
        self.assertEqual(cleaned, 'brand-new@example.com')


class AttachToExistingUserTests(TestCase):

    def _attach(self, user):
        form = TeacherApplicantVerifyEmailForm()
        form.cleaned_data = {
            'first_name': 'Typed', 'last_name': 'Name',
            'middle_name': '', 'email': user.email,
        }
        form.existing_user = user
        return form.save()

    def test_creates_applicant_without_creating_a_user(self):
        user = make_user(roles=['student'])
        before = CustomUser.objects.count()

        applicant = self._attach(user)

        self.assertIsNotNone(applicant)
        self.assertEqual(applicant.user_id, user.pk)
        self.assertEqual(CustomUser.objects.count(), before)
        self.assertFalse(applicant.account_verified)
        self.assertTrue(applicant.meta.get('pre_existing_account'))

    def test_password_and_profile_are_untouched(self):
        user = make_user(roles=['student'])
        user.set_password('OriginalPassw0rd!')
        user.save()
        original_hash = CustomUser.objects.get(pk=user.pk).password

        self._attach(user)

        refreshed = CustomUser.objects.get(pk=user.pk)
        self.assertEqual(refreshed.password, original_hash)
        self.assertEqual(refreshed.first_name, 'Pat')
        self.assertEqual(refreshed.last_name, 'Existing')

    def test_applicant_role_is_granted_and_others_survive(self):
        user = make_user(roles=['instructor'])

        self._attach(user)

        names = set(user.groups.values_list('name', flat=True))
        self.assertIn('applicant', names)
        self.assertIn('instructor', names)


class StartOrResumeApplicationTests(TestCase):

    def test_creates_when_none_exists(self):
        user = make_user(roles=['student'])
        with no_welcome_email():
            application = start_or_resume_application(user)
        self.assertEqual(TeacherApplication.objects.filter(user=user).count(), 1)
        self.assertEqual(application.status, 'In Progress')

    def test_resumes_a_live_application(self):
        user = make_user(roles=['student'])
        existing = make_application(user, status='In Progress')

        resumed = start_or_resume_application(user)

        self.assertEqual(resumed.pk, existing.pk)
        self.assertEqual(TeacherApplication.objects.filter(user=user).count(), 1)

    def test_terminal_application_starts_a_fresh_one(self):
        user = make_user(roles=['instructor'])
        for status in ['Decision Made', 'Withdrawn', 'Closed']:
            with self.subTest(status=status):
                TeacherApplication.objects.filter(user=user).delete()
                finished = make_application(user, status=status)

                with no_welcome_email():
                    fresh = start_or_resume_application(user)

                self.assertNotEqual(fresh.pk, finished.pk)
                self.assertEqual(fresh.status, 'In Progress')


class CompleteSignupFormTests(TestCase):
    """The prefilled, credential-neutral complete-app step."""

    def _pre_existing_applicant(self):
        user = make_user(roles=['instructor'], ssn='123456789',
                         date_of_birth=date(1980, 5, 4),
                         primary_phone='5095551234', city='Spokane')
        user.set_password('OriginalPassw0rd!')
        user.save()
        applicant = TeacherApplicant.objects.create(
            user=user, meta={'pre_existing_account': True},
        )
        return user, applicant

    def _form(self, applicant):
        from instructor_app.instructor_app.forms.teacher_applicant import (
            TeacherApplicantProfileForm,
        )
        return TeacherApplicantProfileForm(applicant=applicant)

    @staticmethod
    def _submitted(form, **overrides):
        """What a real POST of the rendered form would clean to: every field
        posted back at its prefilled value."""
        data = {name: form.initial.get(name, '') for name in form.fields}
        data.update(overrides)
        return data

    def test_password_fields_are_absent(self):
        _user, applicant = self._pre_existing_applicant()
        form = self._form(applicant)
        self.assertNotIn('password', form.fields)
        self.assertNotIn('confirm_password', form.fields)

    def test_new_signup_keeps_password_fields(self):
        user = make_user('fresh@example.com', roles=[])
        applicant = TeacherApplicant.objects.create(user=user)
        form = self._form(applicant)
        self.assertIn('password', form.fields)

    def test_profile_is_prefilled(self):
        _user, applicant = self._pre_existing_applicant()
        form = self._form(applicant)
        self.assertEqual(form.initial.get('first_name'), 'Pat')
        self.assertEqual(form.initial.get('city'), 'Spokane')

    def test_ssn_and_dob_are_not_prefilled(self):
        _user, applicant = self._pre_existing_applicant()
        form = self._form(applicant)
        self.assertFalse(form.initial.get('ssn'))
        self.assertFalse(form.initial.get('date_of_birth'))

    def test_blank_ssn_and_dob_do_not_erase_stored_values(self):
        user, applicant = self._pre_existing_applicant()
        form = self._form(applicant)
        form.cleaned_data = self._submitted(form, ssn='', date_of_birth=None)

        form.save(applicant)

        refreshed = CustomUser.objects.get(pk=user.pk)
        self.assertEqual(refreshed.ssn, '123456789')
        self.assertEqual(refreshed.date_of_birth, date(1980, 5, 4))

    def test_password_survives_the_step(self):
        user, applicant = self._pre_existing_applicant()
        original_hash = CustomUser.objects.get(pk=user.pk).password
        form = self._form(applicant)
        form.cleaned_data = self._submitted(form)

        form.save(applicant)

        self.assertEqual(CustomUser.objects.get(pk=user.pk).password, original_hash)


class OnboardingRoutingTests(TestCase):
    """Where each kind of applicant lands after verifying."""

    def _applicant(self, pre_existing, verification_id=None):
        import uuid
        user = make_user(roles=['instructor'])
        user.set_password('OriginalPassw0rd!')
        user.save()
        meta = {'pre_existing_account': True} if pre_existing else {}
        applicant = TeacherApplicant.objects.create(
            user=user,
            verification_id=verification_id or uuid.uuid4(),
            account_verified=False,
            meta=meta,
        )
        return user, applicant

    def test_pre_existing_user_is_sent_to_login(self):
        from django.conf import settings as dj_settings

        _user, applicant = self._applicant(pre_existing=True)

        response = self.client.post(
            f'/instructor_app/verify_email/{applicant.verification_id}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(dj_settings.LOGIN_URL))
        self.assertIn(str(applicant.id), response.url)

    def test_new_signup_goes_straight_to_complete_signup(self):
        _user, applicant = self._applicant(pre_existing=False)

        response = self.client.post(
            f'/instructor_app/verify_email/{applicant.verification_id}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('complete_signup', response.url)

    def test_complete_signup_refuses_anonymous_for_pre_existing(self):
        from django.conf import settings as dj_settings

        _user, applicant = self._applicant(pre_existing=True)

        response = self.client.get(
            f'/instructor_app/complete_signup/{applicant.id}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(dj_settings.LOGIN_URL))

    def test_complete_signup_refuses_a_different_signed_in_user(self):
        _user, applicant = self._applicant(pre_existing=True)
        other = make_user('other@example.com', roles=['student'])
        other.set_password('OtherPassw0rd!')
        other.save()
        with no_login_history():
            self.client.force_login(other)

        response = self.client.get(
            f'/instructor_app/complete_signup/{applicant.id}/'
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn('complete_signup', response.url)
