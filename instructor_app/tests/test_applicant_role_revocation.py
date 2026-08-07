from datetime import date

from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, pre_save
from django.test import TestCase
from django.urls import reverse

from cis.models.customuser import CustomUser
from cis.models.teacher import Teacher
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
)
from instructor_app.instructor_app.services.applicant_role import (
    revoke_applicant_access,
)
from instructor_app.instructor_app.signals import teacher_applications as sig


# Application saves fire notification emails that need the tapp_email setting.
_NOISY = [
    (post_save, sig.create_new_application, TeacherApplication),
    (pre_save, sig.teacher_app_status_updated, TeacherApplication),
]


class QuietSignalsMixin:
    def silence_application_signals(self):
        for signal, receiver, sender in _NOISY:
            signal.disconnect(receiver, sender=sender)
        self.addCleanup(self._reconnect_application_signals)

    def _reconnect_application_signals(self):
        for signal, receiver, sender in _NOISY:
            signal.connect(receiver, sender=sender)


class StaffClientTestCase(QuietSignalsMixin, TestCase):
    """Logs in a CE user.

    The django_login_history post_login receiver crashes on the test client's
    missing REMOTE_ADDR, so it is disconnected for the duration of the test —
    the same workaround as cis/tests/test_pending_sis_mirror.py.
    """

    def setUp(self):
        self.silence_application_signals()
        self._receivers = list(user_logged_in.receivers)
        user_logged_in.receivers = []
        self.addCleanup(setattr, user_logged_in, 'receivers', self._receivers)

        Group.objects.get_or_create(name='ce')
        self.staff = CustomUser.objects.create_user(
            username='ce@example.com', email='ce@example.com', password='pw',
        )
        self.staff.groups.add(Group.objects.get(name='ce'))


def make_applicant(email='applicant@example.com', applications=1):
    Group.objects.get_or_create(name='applicant')
    user = CustomUser.objects.create(
        username=email, email=email, first_name='Sarah', last_name='Lee',
    )
    applicant = TeacherApplicant.objects.create(user=user)
    for _ in range(applications):
        TeacherApplication.objects.create(user=user, createdon=date.today())
    return user, applicant


class RevokeApplicantAccessTests(QuietSignalsMixin, TestCase):
    def setUp(self):
        self.silence_application_signals()

    def test_no_op_while_an_application_remains(self):
        user, _ = make_applicant(applications=1)

        self.assertFalse(revoke_applicant_access(user))
        self.assertIn('applicant', user.get_roles())
        self.assertTrue(TeacherApplicant.objects.filter(user=user).exists())

    def test_revokes_role_and_record_when_no_applications_remain(self):
        user, _ = make_applicant(applications=1)
        TeacherApplication.objects.filter(user=user).delete()

        self.assertTrue(revoke_applicant_access(user))
        self.assertNotIn('applicant', user.get_roles())
        self.assertFalse(TeacherApplicant.objects.filter(user=user).exists())

    def test_leaves_the_user_account_alone(self):
        user, _ = make_applicant(applications=0)

        revoke_applicant_access(user)

        self.assertTrue(CustomUser.objects.filter(pk=user.pk).exists())

    def test_leaves_other_roles_and_records_alone(self):
        user, _ = make_applicant(applications=0)
        Group.objects.get_or_create(name='instructor')
        user.groups.add(Group.objects.get(name='instructor'))
        teacher = Teacher.objects.create(user=user)

        revoke_applicant_access(user)

        self.assertEqual(user.get_roles(), ['instructor'])
        self.assertTrue(Teacher.objects.filter(pk=teacher.pk).exists())

    def test_survives_a_missing_applicant_group(self):
        user, _ = make_applicant(applications=0)
        Group.objects.filter(name='applicant').delete()

        self.assertTrue(revoke_applicant_access(user))
        self.assertFalse(TeacherApplicant.objects.filter(user=user).exists())


class DeleteRecordResponseTests(StaffClientTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_flags_role_as_revocable_when_it_was_the_last_application(self):
        user, _ = make_applicant(applications=1)
        application = TeacherApplication.objects.get(user=user)

        response = self.client.get(reverse(
            'ce_instructor_app:delete_teacher_application',
            kwargs={'record_id': application.id},
        ))

        body = response.json()
        self.assertTrue(body['applicant_role_revocable'])
        self.assertEqual(body['applicant_name'], 'Sarah Lee')

    def test_does_not_flag_when_other_applications_remain(self):
        user, _ = make_applicant(applications=2)
        application = TeacherApplication.objects.filter(user=user).first()

        response = self.client.get(reverse(
            'ce_instructor_app:delete_teacher_application',
            kwargs={'record_id': application.id},
        ))

        self.assertFalse(response.json()['applicant_role_revocable'])

    def test_reports_the_roles_that_survive(self):
        user, _ = make_applicant(applications=1)
        Group.objects.get_or_create(name='instructor')
        user.groups.add(Group.objects.get(name='instructor'))
        application = TeacherApplication.objects.get(user=user)

        response = self.client.get(reverse(
            'ce_instructor_app:delete_teacher_application',
            kwargs={'record_id': application.id},
        ))

        self.assertEqual(response.json()['other_roles'], ['instructor'])

    def test_never_deletes_the_user_account(self):
        user, _ = make_applicant(applications=1)
        application = TeacherApplication.objects.get(user=user)

        self.client.get(reverse(
            'ce_instructor_app:delete_teacher_application',
            kwargs={'record_id': application.id},
        ))

        self.assertTrue(CustomUser.objects.filter(pk=user.pk).exists())
        self.assertIn('applicant', user.get_roles())


class RevokeEndpointTests(StaffClientTestCase):

    def url_for(self, user):
        return reverse(
            'ce_instructor_app:revoke_applicant_access',
            kwargs={'user_id': user.id},
        )

    def test_revokes_for_ce_staff(self):
        user, _ = make_applicant(applications=0)
        self.client.force_login(self.staff)

        response = self.client.post(self.url_for(user))

        self.assertEqual(response.json()['status'], 'success')
        self.assertNotIn('applicant', user.get_roles())

    def test_refuses_when_an_application_still_exists(self):
        user, _ = make_applicant(applications=1)
        self.client.force_login(self.staff)

        response = self.client.post(self.url_for(user))

        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('applicant', user.get_roles())
        self.assertTrue(TeacherApplicant.objects.filter(user=user).exists())

    def test_rejects_get(self):
        user, _ = make_applicant(applications=0)
        self.client.force_login(self.staff)

        response = self.client.get(self.url_for(user))

        self.assertEqual(response.status_code, 405)
        self.assertIn('applicant', user.get_roles())

    def test_rejects_non_ce_users(self):
        user, _ = make_applicant(applications=0)
        Group.objects.get_or_create(name='instructor')
        outsider = CustomUser.objects.create_user(
            username='nosy@example.com', email='nosy@example.com', password='pw',
        )
        outsider.groups.add(Group.objects.get(name='instructor'))
        self.client.force_login(outsider)

        self.client.post(self.url_for(user))

        self.assertIn('applicant', user.get_roles())


class ApplicantsTabFilterTests(StaffClientTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_lists_only_applicants_with_no_applications(self):
        orphan, orphan_record = make_applicant('orphan@example.com', applications=0)
        make_applicant('active@example.com', applications=1)

        response = self.client.get(
            reverse('ce_instructor_app:teacher_applicant-list'),
            {'format': 'datatables', 'no_applications': '1'},
        )

        returned = [row['id'] for row in response.json()['data']]
        self.assertEqual(returned, [str(orphan_record.id)])

    def test_unfiltered_list_still_returns_everyone(self):
        make_applicant('orphan@example.com', applications=0)
        make_applicant('active@example.com', applications=1)

        response = self.client.get(
            reverse('ce_instructor_app:teacher_applicant-list'),
            {'format': 'datatables'},
        )

        self.assertEqual(len(response.json()['data']), 2)
