import logging

from django import forms
from django.db import transaction
from django.forms import ModelForm

from django_ckeditor_5.widgets import CKEditor5Widget as CKEditorWidget

from cis.models.course import Course, CourseAppRequirement
from cis.utils import YES_NO_SELECT_OPTIONS

from ..utils import valid_uuids

logger = logging.getLogger(__name__)


def requirement_label(record):
    """'<name> - <course>', or just the name when it has no course."""
    return f'{record.name} - {record.course.name}' if record.course else record.name


class CourseAppRequirementForm(ModelForm):

    class Meta:
        model = CourseAppRequirement
        fields = '__all__'
        exclude = ['course']
        widgets = {
            'description': CKEditorWidget()
        }


class AddCourseAppRequirementForm(CourseAppRequirementForm):

    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='add_new_req'
    )

    courses = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True,
        label='Courses'
    )

    def __init__(self, course=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['courses'].queryset = Course.objects.all()

    def save(self, request, commit=False):
        data = self.cleaned_data

        for course in data.get('courses'):
            record = CourseAppRequirement(
                course=course,
                name=data.get('name'),
                status=data.get('status'),
                required=data.get('required'),
                description=data.get('description'),
            )
            record.save()


class UpdateCourseRequirementForm(forms.Form):

    status = forms.ChoiceField(
        choices=CourseAppRequirement.STATUS_OPTIONS,
        required=False,
        label='Status'
    )

    required = forms.ChoiceField(
        choices=YES_NO_SELECT_OPTIONS,
        required=False,
        label='Required'
    )

    ids = forms.MultipleChoiceField(
        required=False,
        label='Records to Update',
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    field_order = ['ids', 'action']

    def __init__(self, ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['action'].initial = kwargs.get('action', 'update_req_status')

        if ids:
            records = CourseAppRequirement.objects.filter(
                id__in=valid_uuids(ids)).select_related('course')
            self.fields['ids'].choices = [
                (r.id, requirement_label(r)) for r in records
            ]
            self.fields['ids'].initial = ids
        else:
            self.fields['ids'].choices = [
                (v, v) for v in kwargs.get('data').getlist('ids')
            ]

    def save(self, request=None):
        from cis.models.note import CourseNote

        data = self.cleaned_data
        for record_id in data.get('ids'):
            try:
                record = CourseAppRequirement.objects.get(id=record_id)
                course_note = ''

                if data.get('status'):
                    record.status = data.get('status')
                    course_note += f'Changing Course App Req for {record.name}<br>'

                if data.get('required'):
                    record.required = data.get('required')
                    course_note += f'Changing Course App Req for {record.name}<br>'

                record.save()

                if course_note:
                    CourseNote(
                        course=record.course,
                        createdby=request.user,
                        note=course_note,
                    ).save()
            except Exception:
                pass


class DeleteCourseRequirementForm(forms.Form):

    ids = forms.MultipleChoiceField(
        required=False,
        label='Records to Delete',
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    field_order = ['ids', 'action']

    def __init__(self, ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['action'].initial = kwargs.get('action', 'delete_req')

        if ids:
            records = CourseAppRequirement.objects.filter(
                id__in=valid_uuids(ids)).select_related('course')
            self.fields['ids'].choices = [
                (r.id, requirement_label(r)) for r in records
            ]
            self.fields['ids'].initial = ids
        else:
            self.fields['ids'].choices = [
                (v, v) for v in kwargs.get('data').getlist('ids')
            ]

    def save(self, request=None):
        """Delete the selected requirements.

        Returns (deleted_count, failures), where failures is a list of
        human-readable messages, so the view never reports a failed delete as
        a success (#17).
        """
        from cis.models.note import CourseNote

        deleted, failures = 0, []
        for record_id in self.cleaned_data.get('ids'):
            record = CourseAppRequirement.objects.filter(
                id__in=valid_uuids([record_id])).select_related('course').first()
            if record is None:
                failures.append(f'{record_id}: not found (it may already be deleted)')
                continue
            name, course = record.name, record.course
            label = requirement_label(record)
            try:
                # Own savepoint, so one failure can't poison the rest.
                with transaction.atomic():
                    record.delete()
            except Exception as e:
                logger.exception('Could not delete course app requirement %s', record_id)
                failures.append(f'{label}: {e}')
                continue
            deleted += 1
            if course:
                CourseNote(
                    course=course,
                    createdby=request.user,
                    note=f'Deleted Course App Req: {name}',
                ).save()
        return deleted, failures
