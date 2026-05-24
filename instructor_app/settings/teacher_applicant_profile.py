import json

from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit

from cis.models.settings import Setting


# Mandatory-flow fields (email + password fields) must never be hidden
# or made optional via the admin UI, so they are deliberately NOT in
# CONFIGURABLE_FIELDS. The form keeps their hard-coded behavior.
#
# Each entry is (field_name, default_label). The label drives the table
# header on the settings page and the placeholder when no custom label
# is set.
CONFIGURABLE_FIELDS = [
    ('first_name',      'First Name'),
    ('last_name',       'Last Name'),
    ('middle_name',     'Middle Name or Initial'),
    ('maiden_name',     'Maiden Name'),
    ('secondary_email', 'Personal Email'),
    ('primary_phone',   'Work Phone'),
    ('secondary_phone', 'Personal Phone'),
    ('alt_phone',       'Other Phone'),
    ('date_of_birth',   'Date of Birth'),
    ('ssn',             'SSN'),
    ('home_address',    'Home Address'),
    ('home_address2',   'Home Address 2'),
    ('city',            'City'),
    ('state',           'State'),
    ('zip_code',                    'Zip/Postal Code'),
    ('has_completed_masters_degree', "Have you completed a master's degree?"),
]

CONFIGURABLE_FIELD_NAMES = [name for name, _ in CONFIGURABLE_FIELDS]

# Pre-existing required/optional state from the form definitions. Kept
# here so a fresh install reproduces today's UX without admin action.
DEFAULT_REQUIRED_FIELDS = [
    'first_name', 'last_name',
    'secondary_email',
    'primary_phone', 'secondary_phone',
    'date_of_birth',
    'home_address', 'city', 'state', 'zip_code',
]


def _build_field_config_html():
    """Build the visual table UI for configuring profile fields.

    Mirrors future_sections' Teaching Form Fields table: one row per
    configurable field with Visible + Required checkboxes, Custom Label
    text input, and Weight number input. JS in
    instructor_app/staticfiles/js/teacher_applicant_profile_settings.js
    syncs the table state to the hidden `field_config` JSON field.
    """
    rows = []
    for name, default_label in CONFIGURABLE_FIELDS:
        rows.append(
            '<tr>'
            f'<td>{default_label}</td>'
            '<td class="text-center">'
            f'<input type="checkbox" class="tapfc-visible" data-field="{name}">'
            '</td>'
            '<td class="text-center">'
            f'<input type="checkbox" class="tapfc-required" data-field="{name}">'
            '</td>'
            '<td>'
            f'<input type="text" class="form-control form-control-sm tapfc-label" '
            f'data-field="{name}" placeholder="{default_label}">'
            '</td>'
            '<td>'
            f'<input type="number" class="form-control form-control-sm tapfc-weight" '
            f'data-field="{name}" min="0" step="1">'
            '</td>'
            '</tr>'
        )

    return (
        '<div id="teacher-applicant-profile-config-ui" class="card mb-3">'
        '<div class="card-header">'
        '<h5 class="mb-0">Profile Form Fields</h5>'
        '</div>'
        '<div class="card-body">'
        '<table class="table table-sm table-bordered">'
        '<thead><tr>'
        '<th>Field</th>'
        '<th class="text-center" style="width:80px">Visible</th>'
        '<th class="text-center" style="width:80px">Required</th>'
        '<th style="width:250px">Custom Label</th>'
        '<th style="width:80px">Weight</th>'
        '</tr></thead>'
        '<tbody>'
        '<tr class="table-light">'
        '<td>Email <span class="badge badge-secondary">Always required</span></td>'
        '<td class="text-center"><input type="checkbox" checked disabled></td>'
        '<td class="text-center"><input type="checkbox" checked disabled></td>'
        '<td><input type="text" class="form-control form-control-sm" disabled '
        'placeholder="Email Address"></td>'
        '<td><input type="number" class="form-control form-control-sm" disabled '
        'value="0"></td>'
        '</tr>'
        + ''.join(rows) +
        '</tbody></table>'
        '<small class="form-text text-muted">'
        'Lighter weighted fields appear at the top of the form. '
        'Email and password are always present and cannot be hidden.'
        '</small>'
        '</div></div>'
    )


class SettingForm(forms.Form):

    class Media:
        js = ('js/teacher_applicant_profile_settings.js',)

    field_config = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.HiddenInput(),
        label='Profile Form Configuration',
    )

    def _to_python(self):
        # field_config is a JSON string written by the JS; parse and
        # re-serialize so we store a well-formed dict on the Setting row
        # (and silently drop garbage rather than persisting it).
        raw = self.cleaned_data.get('field_config') or '{}'
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                parsed = {}
        except (TypeError, ValueError):
            parsed = {}
        return {
            'visible':  parsed.get('visible',  list(CONFIGURABLE_FIELD_NAMES)),
            'required': parsed.get('required', list(DEFAULT_REQUIRED_FIELDS)),
            'labels':   parsed.get('labels', {}),
            'weights':  parsed.get('weights', {}),
        }


class teacher_applicant_profile(SettingForm):
    key = 'instructor_app.teacher_applicant_profile'

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

        # Hydrate the hidden field with the current DB value so the JS
        # can read existing state on page load.
        current = self.from_db()
        if isinstance(current, dict):
            self.fields['field_config'].initial = json.dumps(current)

        self.helper = FormHelper()
        self.helper.attrs = {'target': '_blank'}
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy(
            'setting:run_record', args=[request.GET.get('report_id')])
        self.helper.add_input(Submit('submit', 'Save Setting'))

        self.helper.layout = Layout(
            HTML(_build_field_config_html()),
            'field_config',
        )

    @classmethod
    def from_db(cls):
        try:
            return Setting.objects.get(key=cls.key).value
        except Setting.DoesNotExist:
            return {}

    def install(self):
        defaults = {
            'visible':  list(CONFIGURABLE_FIELD_NAMES),
            'required': list(DEFAULT_REQUIRED_FIELDS),
            'labels':   {},
            'weights':  {},
        }
        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting()
            setting.key = self.key
        setting.value = defaults
        setting.save()

    def run_record(self):
        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting()
            setting.key = self.key
        setting.value = self._to_python()
        setting.save()
        return JsonResponse({
            'message': 'Successfully saved settings',
            'status': 'success',
        })
