import datetime

from django import forms
from django.urls import reverse_lazy
from django.core.files.base import ContentFile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.backends.storage_backend import PrivateMediaStorage
from cis.utils import export_to_excel
from cis.models.course import Course

from ..models.applicant_course_reviewer import ApplicantCourseReviewer
from ..models.teacher_application import TeacherApplication


class course_reviewers(forms.Form):
    review_status = forms.MultipleChoiceField(
        choices=ApplicantCourseReviewer.STATUS_OPTIONS,
        required=False,
        label='Review Status(es)',
        help_text='Leave blank to include all statuses.',
        widget=forms.CheckboxSelectMultiple,
    )

    teacher_app_status = forms.MultipleChoiceField(
        choices=TeacherApplication.STATUS_OPTIONS,
        required=False,
        label='Application Status(es)',
        help_text='Leave blank to include all statuses.',
        widget=forms.CheckboxSelectMultiple,
    )

    course = forms.MultipleChoiceField(
        choices=[],
        required=False,
        label='Course(s)',
        help_text='Leave blank to include all courses.',
        widget=forms.CheckboxSelectMultiple,
    )

    assigned_on_from = forms.DateField(
        required=False,
        label='Reviewer Assigned On (From)',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    assigned_on_to = forms.DateField(
        required=False,
        label='Reviewer Assigned On (To)',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    roles = []
    request = None

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

        course_choices = [
            (str(c.id), str(c))
            for c in Course.objects.all().order_by('name')
        ]
        self.fields['course'].choices = course_choices

        self.helper = FormHelper()
        self.helper.attrs = {'target': '_blank'}
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Generate Export'))

        if self.request:
            self.helper.form_action = reverse_lazy(
                'report:run_report', args=[request.GET.get('report_id')]
            )

    def run(self, task, data):
        review_statuses = data.get('review_status', [])
        teacher_app_statuses = data.get('teacher_app_status', [])
        course_ids = data.get('course', [])
        assigned_on_from = (data.get('assigned_on_from') or [''])[0]
        assigned_on_to = (data.get('assigned_on_to') or [''])[0]

        records = ApplicantCourseReviewer.objects.all().select_related(
            'reviewer',
            'application_course__course',
            'application_course__teacherapplication__user',
            'application_course__teacherapplication__highschool',
        )

        if review_statuses:
            records = records.filter(status__in=review_statuses)

        if teacher_app_statuses:
            records = records.filter(
                application_course__teacherapplication__status__in=teacher_app_statuses
            )

        if course_ids:
            records = records.filter(application_course__course_id__in=course_ids)

        if assigned_on_from:
            try:
                records = records.filter(
                    assigned_on__gte=datetime.date.fromisoformat(assigned_on_from)
                )
            except ValueError:
                pass

        if assigned_on_to:
            try:
                records = records.filter(
                    assigned_on__lte=datetime.date.fromisoformat(assigned_on_to)
                )
            except ValueError:
                pass

        records = records.order_by(
            'application_course__teacherapplication__user__last_name',
            'application_course__course__name',
            'reviewer__last_name',
        )

        fields = {
            'application_course.teacherapplication.user.last_name': 'Teacher Last Name',
            'application_course.teacherapplication.user.first_name': 'Teacher First Name',
            'application_course.teacherapplication.user.email': 'Teacher Email',
            'application_course.teacherapplication.status': 'Application Status',
            'application_course.teacherapplication.highschool': 'High School',
            'application_course.course': 'Course',
            'reviewer.last_name': 'Reviewer Last Name',
            'reviewer.first_name': 'Reviewer First Name',
            'reviewer.email': 'Reviewer Email',
            'status': 'Review Status',
            'assigned_on': 'Assigned On',
        }

        file_name = 'course_reviewers-' + str(datetime.datetime.now()) + '.xlsx'
        http_response = export_to_excel(file_name, records, fields)

        path = 'reports/' + str(task.id) + '/' + file_name
        media_storage = PrivateMediaStorage()
        path = media_storage.save(path, ContentFile(http_response.content))
        path = media_storage.url(path)

        return path
