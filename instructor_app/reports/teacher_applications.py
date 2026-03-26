import datetime

from django import forms
from django.urls import reverse_lazy
from django.core.files.base import ContentFile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.backends.storage_backend import PrivateMediaStorage
from cis.utils import export_to_excel

from ..models.teacher_application import TeacherApplication


class teacher_applications(forms.Form):
    status = forms.MultipleChoiceField(
        choices=TeacherApplication.STATUS_OPTIONS,
        required=False,
        label='Status(es)',
        help_text='Leave blank to include all statuses.',
        widget=forms.CheckboxSelectMultiple,
    )

    created_on_from = forms.DateField(
        required=False,
        label='Created On (From)',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    created_on_to = forms.DateField(
        required=False,
        label='Created On (To)',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    roles = []
    request = None

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

        self.helper = FormHelper()
        self.helper.attrs = {'target': '_blank'}
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Generate Export'))

        if self.request:
            self.helper.form_action = reverse_lazy(
                'report:run_report', args=[request.GET.get('report_id')]
            )

    def run(self, task, data):
        statuses = data.get('status', [])
        created_on_from = (data.get('created_on_from') or [''])[0]
        created_on_to = (data.get('created_on_to') or [''])[0]

        records = TeacherApplication.objects.all().select_related(
            'user', 'highschool', 'assigned_to'
        )

        if statuses:
            records = records.filter(status__in=statuses)

        if created_on_from:
            try:
                records = records.filter(
                    createdon__gte=datetime.date.fromisoformat(created_on_from)
                )
            except ValueError:
                pass

        if created_on_to:
            try:
                records = records.filter(
                    createdon__lte=datetime.date.fromisoformat(created_on_to)
                )
            except ValueError:
                pass

        records = records.order_by('-createdon', 'user__last_name')

        fields = {
            'user.last_name': 'Last Name',
            'user.first_name': 'First Name',
            'user.email': 'Email',
            'user.primary_phone': 'Phone',
            'highschool': 'High School',
            'status': 'Status',
            'createdon': 'Created On',
            'assigned_to': 'Assigned To',
        }

        file_name = 'teacher_applications-' + str(datetime.datetime.now()) + '.xlsx'
        http_response = export_to_excel(file_name, records, fields)

        path = 'reports/' + str(task.id) + '/' + file_name
        media_storage = PrivateMediaStorage()
        path = media_storage.save(path, ContentFile(http_response.content))
        path = media_storage.url(path)

        return path
