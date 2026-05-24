from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.settings import Setting


# Mandatory-flow fields (email + password fields) must never be hidden
# or made optional via the admin UI, so they are deliberately NOT in
# CONFIGURABLE_FIELDS. The form keeps their hard-coded behavior.
CONFIGURABLE_FIELDS = [
    'first_name', 'last_name', 'middle_name', 'maiden_name',
    'secondary_email',
    'primary_phone', 'secondary_phone', 'alt_phone',
    'date_of_birth', 'ssn',
    'home_address', 'home_address2', 'city', 'state', 'zip_code',
]

# Pre-existing required/optional state from the form definitions. Kept
# here so a fresh install reproduces today's UX without admin action.
DEFAULT_REQUIRED_FIELDS = [
    'first_name', 'last_name',
    'secondary_email',
    'primary_phone', 'secondary_phone',
    'date_of_birth',
    'home_address', 'city', 'state', 'zip_code',
]
DEFAULT_HIDDEN_FIELDS = []

PROFILE_FIELD_CHOICES = [
    (name, name.replace('_', ' ').title()) for name in CONFIGURABLE_FIELDS
]


class SettingForm(forms.Form):

    hidden_fields = forms.MultipleChoiceField(
        choices=PROFILE_FIELD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Hide Fields',
        help_text=(
            'Check a field to hide it from the Teacher Applicant Profile form. '
            'Hidden fields are removed from the form entirely; they are not '
            'rendered and are not validated.'
        ),
    )

    required_fields = forms.MultipleChoiceField(
        choices=PROFILE_FIELD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Required Fields',
        help_text=(
            'Check a field to make it required. Unchecked fields are optional. '
            'Fields hidden above are ignored here.'
        ),
    )

    def _to_python(self):
        return {
            'hidden_fields': self.cleaned_data.get('hidden_fields', []),
            'required_fields': self.cleaned_data.get('required_fields', []),
        }


class teacher_applicant_profile(SettingForm):
    key = 'instructor_app.teacher_applicant_profile'

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.helper = FormHelper()
        self.helper.attrs = {'target': '_blank'}
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy(
            'setting:run_record', args=[request.GET.get('report_id')])
        self.helper.add_input(Submit('submit', 'Save Setting'))

    @classmethod
    def from_db(cls):
        try:
            return Setting.objects.get(key=cls.key).value
        except Setting.DoesNotExist:
            return {}

    def install(self):
        defaults = {
            'hidden_fields': list(DEFAULT_HIDDEN_FIELDS),
            'required_fields': list(DEFAULT_REQUIRED_FIELDS),
        }
        setting, _ = Setting.objects.get_or_create(key=self.key)
        setting.value = defaults
        setting.save()

    def run_record(self):
        setting, _ = Setting.objects.get_or_create(key=self.key)
        setting.value = self._to_python()
        setting.save()
        return JsonResponse({
            'message': 'Successfully saved settings',
            'status': 'success',
        })
