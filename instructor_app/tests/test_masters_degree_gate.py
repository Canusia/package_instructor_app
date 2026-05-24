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
