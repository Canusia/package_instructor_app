from django.contrib.auth.models import Group
from django.test import TestCase

from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    TeacherApplicantProfileForm,
)
from instructor_app.instructor_app.models.teacher_applicant import (
    TeacherApplicant,
)


def make_applicant(email='m@example.com'):
    Group.objects.get_or_create(name='applicant')
    user = CustomUser.objects.create(
        username=email, email=email, first_name='Test', last_name='User',
    )
    return TeacherApplicant.objects.create(user=user)


class MastersDegreeFieldRenderTests(TestCase):
    def test_field_is_on_form_by_default(self):
        form = TeacherApplicantProfileForm()
        self.assertIn('has_completed_masters_degree', form.fields)
        choice_values = [c[0] for c in form.fields['has_completed_masters_degree'].choices]
        self.assertIn('yes', choice_values)
        self.assertIn('no', choice_values)

    def test_field_can_be_hidden_via_configurator(self):
        Setting.objects.update_or_create(
            key='instructor_app.teacher_applicant_profile',
            defaults={'value': {
                'visible': ['first_name'],
                'required': [],
                'labels': {},
                'weights': {},
            }},
        )
        form = TeacherApplicantProfileForm()
        self.assertNotIn('has_completed_masters_degree', form.fields)


class MastersDegreeSaveTests(TestCase):
    def test_saving_yes_writes_to_applicant_meta(self):
        applicant = make_applicant()
        form = TeacherApplicantProfileForm(
            applicant=applicant,
            data={
                'first_name': 'Test', 'last_name': 'User',
                'email': applicant.user.email,
                'secondary_email': 'second@example.com',
                'primary_phone': '5551112222',
                'secondary_phone': '5553334444',
                'date_of_birth_year':  '1990',
                'date_of_birth_month': '1',
                'date_of_birth_day':   '1',
                'home_address': '1 Test St', 'city': 'Town', 'state': 'WA',
                'zip_code': '99201',
                'password': 'TestPassword12!',
                'confirm_password': 'TestPassword12!',
                'has_completed_masters_degree': 'yes',
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save(applicant)
        applicant.refresh_from_db()
        self.assertEqual(applicant.meta.get('has_completed_masters_degree'), 'yes')

    def test_populate_initial_reads_from_meta(self):
        applicant = make_applicant()
        applicant.meta = {'has_completed_masters_degree': 'no'}
        applicant.save()
        form = TeacherApplicantProfileForm(applicant=applicant)
        self.assertEqual(
            form.initial.get('has_completed_masters_degree'), 'no',
        )


from datetime import date

from cis.models.settings import Setting as _Setting
from instructor_app.instructor_app.models.teacher_application import (
    TeacherApplication,
)


def seed_tapp_email():
    """Seed the tapp_email Setting so the post_save signal doesn't KeyError."""
    _Setting.objects.update_or_create(
        key='tapp_email',
        defaults={'value': {
            'new_applicant_email_subject': 'Test',
            'new_applicant_email': 'Hello {{ first_name }}',
        }},
    )


def set_global_recs(count):
    """Helper: write inst_app_language.recommendations_needed."""
    _Setting.objects.update_or_create(
        key='inst_app_language',
        defaults={'value': {'recommendations_needed': str(count)}},
    )


def set_profile_visible(field_names):
    """Helper: write the field-config visible list."""
    _Setting.objects.update_or_create(
        key='instructor_app.teacher_applicant_profile',
        defaults={'value': {
            'visible': list(field_names),
            'required': [],
            'labels': {},
            'weights': {},
        }},
    )


class EffectiveRecommendationsNeededTests(TestCase):
    def setUp(self):
        self.applicant = make_applicant()
        seed_tapp_email()
        self.application = TeacherApplication.objects.create(
            user=self.applicant.user,
            createdon=date.today(),
        )

    def test_returns_zero_when_global_setting_is_zero(self):
        set_global_recs(0)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'no'}
        self.applicant.save()
        self.assertEqual(self.application.effective_recommendations_needed, 0)

    def test_returns_global_count_when_field_hidden(self):
        set_global_recs(2)
        set_profile_visible(['first_name'])  # masters question hidden
        self.applicant.meta = {'has_completed_masters_degree': 'yes'}
        self.applicant.save()
        # Even though applicant says yes, the field is hidden — gate bypassed.
        self.assertEqual(self.application.effective_recommendations_needed, 2)

    def test_returns_zero_when_applicant_has_masters(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'yes'}
        self.applicant.save()
        self.assertEqual(self.application.effective_recommendations_needed, 0)

    def test_returns_global_count_when_applicant_lacks_masters(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'no'}
        self.applicant.save()
        self.assertEqual(self.application.effective_recommendations_needed, 2)

    def test_unanswered_treated_as_no(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        # applicant.meta is {} — the question hasn't been answered yet.
        self.assertEqual(self.application.effective_recommendations_needed, 2)


class HasReceivedRecommendationGateTests(TestCase):
    def setUp(self):
        self.applicant = make_applicant()
        seed_tapp_email()
        self.application = TeacherApplication.objects.create(
            user=self.applicant.user,
            createdon=date.today(),
        )

    def test_satisfied_when_applicant_has_masters_and_zero_received(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'yes'}
        self.applicant.save()
        # No ApplicantRecommendation rows created; should still be True
        # because the effective requirement is 0.
        self.assertTrue(self.application.has_received_recommendation())


def _safe_force_login(client, user):
    """force_login without triggering django_login_history's IP lookup."""
    from django.contrib.auth.signals import user_logged_in
    from django_login_history.models import post_login
    user_logged_in.disconnect(post_login)
    try:
        client.force_login(user)
    finally:
        user_logged_in.connect(post_login)


class ManageRecommendationSkipTests(TestCase):
    def setUp(self):
        self.applicant = make_applicant()
        seed_tapp_email()
        self.application = TeacherApplication.objects.create(
            user=self.applicant.user,
            createdon=date.today(),
        )
        _safe_force_login(self.client, self.applicant.user)

    def test_skips_when_applicant_has_masters(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'yes'}
        self.applicant.save()

        from django.urls import reverse
        url = reverse('applicant_app:manage_recommendation',
                      kwargs={'record_id': str(self.application.id)})
        resp = self.client.get(url)
        # Skipped → 302 redirect to manage_ed_bg
        self.assertEqual(resp.status_code, 302)
        self.assertIn('manage_ed_bg', resp.url)

    def test_renders_form_when_recs_required(self):
        set_global_recs(2)
        set_profile_visible(['has_completed_masters_degree'])
        self.applicant.meta = {'has_completed_masters_degree': 'no'}
        self.applicant.save()

        from django.urls import reverse
        url = reverse('applicant_app:manage_recommendation',
                      kwargs={'record_id': str(self.application.id)})
        resp = self.client.get(url)
        # Not skipped → 200 with the request-recommendation page
        self.assertEqual(resp.status_code, 200)
