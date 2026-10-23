"""Ed. Background gains 'Discipline specific professional development' (#12):
opt-in per tenant, saved to education_background, shown on every read-only
view and in the PDF -- which also gets the three newer fields it left blank."""
import os

from django import forms
from django.test import SimpleTestCase

from instructor_app.instructor_app.forms.teacher_applicant import EdBgForm

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = 'professional_development'


def _read(*parts):
    with open(os.path.join(PKG, *parts)) as fh:
        return fh.read()


class ProfessionalDevelopmentFieldTests(SimpleTestCase):
    def test_hidden_when_tenant_config_lists_no_fields(self):
        form = EdBgForm(config={})
        self.assertIsInstance(form.fields[FIELD].widget, forms.HiddenInput)
        # Older fields keep the "nothing listed = all shown" behaviour.
        self.assertNotIsInstance(form.fields['courses_taught'].widget, forms.HiddenInput)

    def test_empty_fields_list_shows_all_but_opt_in(self):
        # The settings screen saves "fields": [] when nothing is ticked.
        form = EdBgForm(config={'fields': []})
        self.assertNotIsInstance(form.fields['courses_taught'].widget, forms.HiddenInput)
        self.assertIsInstance(form.fields[FIELD].widget, forms.HiddenInput)

    def test_hidden_when_tenant_lists_other_fields(self):
        form = EdBgForm(config={'fields': ['courses_taught']})
        self.assertIsInstance(form.fields[FIELD].widget, forms.HiddenInput)

    def test_shown_required_and_relabelled_when_configured(self):
        form = EdBgForm(config={'fields': [FIELD], 'required': [FIELD],
                                'labels': {FIELD: 'PD'}})
        self.assertNotIsInstance(form.fields[FIELD].widget, forms.HiddenInput)
        self.assertTrue(form.fields[FIELD].required)
        self.assertEqual(form.fields[FIELD].label, 'PD')

    def test_saved_with_the_other_fields(self):
        self.assertIn(FIELD, EdBgForm.SAVED_FIELDS)
        self.assertNotIn('other_name', EdBgForm.SAVED_FIELDS)

    def test_initial_carries_every_saved_field(self):
        from types import SimpleNamespace
        ed_bg = {f: f'v-{f}' for f in EdBgForm.SAVED_FIELDS}
        app = SimpleNamespace(id='app-1', user=SimpleNamespace(
            education_background=ed_bg, previous_names='Old Name'))
        initial = EdBgForm.initial_for(app)
        for f in EdBgForm.SAVED_FIELDS:
            self.assertEqual(initial[f], f'v-{f}', f)
        self.assertEqual(initial['other_name'], 'Old Name')
        app.user.education_background = 'not a dict'
        self.assertIsNone(EdBgForm.initial_for(app)[FIELD])

    def test_pdf_and_views_use_the_shared_initial(self):
        for parts in (('services', 'pdf.py'), ('views', 'ce', 'detail.py'),
                      ('views', 'faculty', 'home.py'), ('views', 'manage_ed_bg.py')):
            self.assertIn('EdBgForm.initial_for(', _read(*parts), '/'.join(parts))

    def test_every_view_renders_the_field(self):
        self.assertIn(f'form.{FIELD}|as_crispy_field',
                      _read('templates', 'instructor_app', 'manage_ed_bg.html'))
        for name in (('faculty', 'review_application.html'), ('ce', 'details.html')):
            self.assertIn(f'ed_bg_form.{FIELD}|as_crispy_field',
                          _read('templates', 'instructor_app', *name), name)
        self.assertIn(f'ed_bg.{FIELD}',
                      _read('templates', 'instructor_app', 'ce', 'details_single.html'))
        self.assertIn(f'#id_{FIELD}', _read('staticfiles', 'js', 'faculty_review.js'))

    def test_settings_screen_offers_the_field(self):
        self.assertIn(f"('{FIELD}',", _read('settings', 'inst_app_language.py'))
