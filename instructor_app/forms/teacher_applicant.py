
import json
import logging
from datetime import date

from django import forms
from django.forms import formset_factory
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.core.validators import validate_email

from django_recaptcha.fields import ReCaptchaField

from cis.models.customuser import CustomUser
from cis.models.highschool import HighSchool
from cis.models.term import AcademicYear
from cis.models.course import Course, CourseAppRequirement
from instructor_app.models.teacher_applicant import (
    TeacherApplication, ApplicantRecommendation,
    ApplicantSchoolCourse, ApplicationUpload,
    ApplicantCourseReviewer
)

from cis.models.note import TeacherApplicationNote

from cis.utils import get_foreign_key_references
from cis.forms.utils import with_meta, MetaFormMixin

logger = logging.getLogger(__name__)
from form_fields import fields as FFields

from passwords.validators import (
    DictionaryValidator, LengthValidator, ComplexityValidator
)


class MigrateForm(forms.Form):
    
    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='migrate_teacher_application'
    )

    destination_record = forms.ModelChoiceField(
        required=True,
        queryset=None,
        label='Destination Record'
    )

    move_items = forms.MultipleChoiceField(
        label='Select Items to Move',
        choices=[
            ('registrations', 'Registrations'),
            ('support_docs', 'Support Docs.'),
            ('student_agreements', 'Student Agreements'),
            ('student_recommendation', 'Recommendations'),
            ('parent_consent', 'Parent Consent'),
            ('notes', 'Notes'),
        ],
        widget=forms.CheckboxSelectMultiple
    )

    confirm = forms.BooleanField(
        required=True,
        label='I understand this action cannot be undone.'
    )
    
    # class Media:
    #     js = [
    #         'js/student_migration.js'
    #     ]

    def __init__(self, record, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['destination_record'].queryset = TeacherApplication.objects.all().exclude(
            id=record.id
        )

        references = get_foreign_key_references(record)
        move_item_choices = []

        for model_name, obj in references:
            choice = (f"{model_name}", f"{model_name}")
            if choice not in move_item_choices:
                move_item_choices.append(choice)

        self.fields['move_items'].choices = move_item_choices

    def save(self, request, record):
        data = self.cleaned_data
        references = get_foreign_key_references(record)

        success, message = True, []
        for model_name, obj in references:

            if model_name in data.get('move_items'):
                try:
                    obj.teacher_application = data.get('destination_record')
                    obj.save()

                    message.append(
                        f'Successfully moved {model_name} - {obj}'
                    )
                except Exception as e:
                    success = False
                    message.append(
                        f'Failed to move {model_name} - {obj} {e}. Please edit/delete this record manually'
                    )

        return (success, message)
    
class EditTeacherAppCourseUploadForm(forms.Form):
    
    id = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )
    
    associated_with = forms.MultipleChoiceField(
        label='For',
        help_text='<b>Click the box next to each requirement for upload. If you select multiple boxes for one upload, this allows you to upload the same document for multiple requirements.</b>',
        choices=(),
        widget=forms.CheckboxSelectMultiple()
    )
    
    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='edit_teacher_application_upload'
    )

    def __init__(self, teacher_application=None, upload_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['id'].initial = upload_id

        interested_courses = ApplicantSchoolCourse.objects.filter(
            teacherapplication=teacher_application
        ).values_list('course__id', flat=True)

        course_reqs = CourseAppRequirement.objects.filter(
            course__id__in=interested_courses
        )
        req_list = []
        for req in course_reqs:
            req_list.append((str(req.id), f'{req.name} for {req.course.name}'))
        self.fields['associated_with'].choices = req_list

    def save(self, teacher_application):
        data = self.cleaned_data

        record = ApplicationUpload.objects.get(pk=data.get('id'))
        record.associated_with = data.get('associated_with')
        record.save()

        return record
        
class NoteReplyForm(forms.Form):
    
    message = forms.CharField(
        widget=forms.Textarea,
        label='Response',
        help_text=''
    )

    captcha = ReCaptchaField(
        label=''
    )

    def __init__(self, note, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, request, parent_note):
        note = TeacherApplicationNote(
            teacher_application=parent_note.teacher_application,
            note=self.cleaned_data.get('message'),
            createdby=parent_note.teacher_application.user,
            parent=parent_note.id,
            meta={
                'type':'response'
            }
        )
        note.save()

        return note

class ApplicantCourseFinalStatusForm(forms.Form):
    decision = forms.ChoiceField(
        choices=ApplicantSchoolCourse.STATUS_OPTIONS,
        label='Final Decision'
    )

    note = forms.CharField(
        widget=forms.Textarea,
        label='Note',
        required=False
    )

    application_course_id = forms.CharField(
        widget=forms.HiddenInput
    )

    def save(self):
        data = self.cleaned_data

        course = ApplicantSchoolCourse.objects.get(
            pk=data['application_course_id']
        )
        course.status = data['decision']
        course.note = data.get('note')
        course.save()

class ApplicantReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=ApplicantCourseReviewer.STATUS_OPTIONS,
        label='Your Decision/Recommendation'
    )

    comment = forms.CharField(
        widget=forms.Textarea,
        label='Comment',
        help_text='',
        required=False
    )

    application_course_id = forms.CharField(
        widget=forms.HiddenInput
    )

class ApplicantCourseReviewerForm(forms.ModelForm):
    application_course_id = forms.CharField(
        widget=forms.HiddenInput,
        required=True
    )

    class Meta:
        model = ApplicantCourseReviewer

        fields = [
            'reviewer'
        ]

        labels = {
            'reviewer': 'Reviewer'
        }

    def __init__(self, application_course, *args, **kwargs):
        super().__init__(*args, **kwargs)

        faculty_coords = application_course.course.get_faculty_coordinators()
        self.fields['reviewer'].queryset = CustomUser.objects.filter(
            id__in=[fc.user.id for fc in faculty_coords]
        )
        self.fields['application_course_id'].initial = application_course.id

class EditTeacherApplicationForm(forms.Form):
    action = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    status = forms.ChoiceField(
        required=True,
        label='Status',
        choices=TeacherApplication.STATUS_OPTIONS
    )

    assigned_to = forms.CharField(
        required=False,
        label='Assigned To',
        widget=forms.HiddenInput
    )

    invite_to_interview = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label='Invite to Interview Sent On'
    )

    interviewed_on = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label='Interview Held On'
    )

    decision_letter_sent_on = forms.CharField(
        required=False,
        widget=forms.DateInput(),
        help_text='',
        label='Decision Letter Sent On'
    )

    participating_acad_year = forms.ChoiceField(
        required=False,
        choices=[],
        help_text='If approved to attend',
        label='Attending Academic Year'
    )
    
    psid = forms.CharField(
        required=False,
        help_text='If approved to attend',
        label='EMPLID'
    )

    # added_to_ps_on = forms.CharField(
    #     required=False,
    #     widget=forms.DateInput(),
    #     help_text='If approved to attend',
    #     label='Added to PS On'
    # )

    # imported_on = forms.CharField(
    #     required=False,
    #     widget=forms.DateInput(),
    #     help_text='If approved to attend',
    #     label='Added to PASS On'
    # )

    # grad_credit = forms.ChoiceField(
    #     required=False,
    #     label='Graduate Credit/CTLE Option',
    #     help_text='If approved to attend',
    #     choices=[
    #         ('----', 'Select'),
    #         ('CTLE', 'CTLE'),
    #         ('Graduate Credit', 'Graduate Credit'),
    #         ('Not Interested', 'Not Interested'),
    #     ]
    # )

    checklist = forms.MultipleChoiceField(
        required=False,
        label='Checklist',
        help_text='If approved to attend',
        widget=forms.CheckboxSelectMultiple(),
        choices=[]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_staff=True,
            is_active=True
        )

        self.fields['participating_acad_year'].choices = [
            (acad_year.id, acad_year.name) for acad_year in AcademicYear.objects.all()
        ]

        # Load checklist choices from settings
        from instructor_app.settings.inst_app_language import inst_app_language
        app_settings = inst_app_language.from_db()
        checklist_config = app_settings.get('checklist_config')
        if checklist_config:
            if isinstance(checklist_config, str):
                checklist_config = json.loads(checklist_config)
            self.fields['checklist'].choices = [
                (item['value'], item['label']) for item in checklist_config
            ]
        else:
            self.fields['checklist'].choices = [
                ('Class Assigned', 'Class Assigned'),
                ('Hotel Room Requested', 'Hotel Room Requested'),
                ('NetID Activated', 'NetID Activated'),
                ('Imported into PS', 'Imported into PS'),
            ]
        

    def save(self, teacher_application):
        data = self.cleaned_data

        teacher_application.status = data['status']
        # if data['assigned_to']:
        #     teacher_application.assigned_to = data['assigned_to']

        if data['invite_to_interview']:
            teacher_application.misc_info['invite_to_interview'] = data['invite_to_interview']

        if data['interviewed_on']:
            teacher_application.misc_info['interviewed_on'] = data['interviewed_on']

        if data['decision_letter_sent_on']:
            teacher_application.misc_info['decision_letter_sent_on'] = data['decision_letter_sent_on']
        
        teacher_application.misc_info['participating_acad_year'] = data.get('participating_acad_year')
        # teacher_application.misc_info['grad_credit'] = data.get('grad_credit')
        teacher_application.misc_info['checklist'] = data.get('checklist')
        
        if data.get('psid'):
            teacher_application.user.psid = data.get('psid')
            teacher_application.user.save()

        teacher_application.save()
        return teacher_application

class AppUploadForm(forms.ModelForm):
    associated_with = forms.MultipleChoiceField(
        label='For',
        choices=()
    )

    class Meta:
        model = ApplicationUpload
        fields = [
            'upload'
        ]

        labels = {
            'upload': ''
        }

        help_texts = {
            'upload': 'Maximum file upload size is 8MB. For larger files please zip them prior to uploading.'
        }

    def __init__(self, teacher_application, *args, **kwargs):
        super().__init__(*args, **kwargs)

        interested_courses = ApplicantSchoolCourse.objects.filter(
            teacherapplication=teacher_application
        ).values_list('course__id', flat=True)

        course_reqs = CourseAppRequirement.objects.filter(
            course__id__in=interested_courses
        )
        req_list = []
        for req in course_reqs:
            req_list.append((str(req.id), f'{req.name}'))
        self.fields['associated_with'].choices = req_list

    def save(self, commit=False):
        record = super().save(commit=commit)

        data = self.cleaned_data
        record.associated_with = data.get('associated_with')
        return record

class EducationEntryForm(forms.Form):
    institution = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    degree = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    major = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    # transcript_copy = forms.CharField(required=False, widget=forms.HiddenInput())
    # transcript_recv = forms.CharField(required=False, widget=forms.HiddenInput())

EducationEntryFormSet = formset_factory(EducationEntryForm, extra=5, max_num=10)


class EdBgForm(forms.Form):

    teacher_application = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    other_name = forms.CharField(
        required=False,
        label='Enter your name as it appears on your transcript(s), if different from your current name',
        help_text='Separate multiple names with commas'
    )

    credits_earned = forms.CharField(
        required=False,
        label='Number of credit hours earned beyond highest degree',
        widget=forms.TextInput(attrs={'class': 'col-4'})
    )

    masters_level_credits = forms.CharField(
        required=False,
        label="Total number of Master's-level credits in your discipline",
        widget=forms.TextInput(attrs={'class': 'col-4'})
    )

    grad_courses = forms.CharField(
        required=False,
        label='List graduate course work that particularly pertains to the course you are interested in teaching',
        widget=forms.Textarea
    )

    undergrad_program = forms.CharField(
        required=False,
        label='Describe your undergraduate program as it pertains to the course you are interested in teaching',
        widget=forms.Textarea
    )

    certified_states = forms.CharField(
        required=False,
        label='In what state(s) are you permanently certified to teach?',
        widget=forms.TextInput(attrs={'class': 'col-8'})
    )

    certified_subjects = forms.CharField(
        required=False,
        label='In what subject(s) are you permanently certified to teach?',
        widget=forms.TextInput(attrs={'class': 'col-10'})
    )

    highschool_years = forms.CharField(
        required=False,
        label='Total years of teaching high school',
        widget=forms.TextInput(attrs={'class': 'col-4'})
    )

    college_years = forms.CharField(
        required=False,
        label='Total years of teaching college',
        widget=forms.TextInput(attrs={'class': 'col-4'})
    )

    courses_taught = forms.CharField(
        required=False,
        label='Specific subjects you have taught or currently teaching that relate to the course you are interested in teaching',
        widget=forms.Textarea
    )

    CONFIGURABLE_FIELDS = [
        'other_name', 'credits_earned', 'masters_level_credits',
        'grad_courses', 'undergrad_program', 'certified_states',
        'certified_subjects', 'highschool_years', 'college_years', 'courses_taught'
    ]

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', None)
        super().__init__(*args, **kwargs)

        if config is None:
            from instructor_app.settings.inst_app_language import inst_app_language
            raw = inst_app_language.from_db().get('ed_bg_form_config', '{}')
            try:
                config = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except (json.JSONDecodeError, TypeError):
                config = {}

        visible_fields = config.get('fields', None)
        required_fields = config.get('required', [])
        custom_labels = config.get('labels', {})

        for field_name in self.CONFIGURABLE_FIELDS:
            if field_name not in self.fields:
                continue
            if visible_fields is not None and field_name not in visible_fields:
                self.fields[field_name].widget = forms.HiddenInput()
                self.fields[field_name].required = False
                continue
            self.fields[field_name].required = field_name in required_fields
            if field_name in custom_labels:
                self.fields[field_name].label = custom_labels[field_name]

    def save(self, teacher_application, formset=None):
        user = teacher_application.user
        if self.cleaned_data.get('other_name'):
            user.previous_names = self.cleaned_data['other_name']

        ed_bg_data = {}
        if formset:
            institutions, degrees, majors = [], [], []
            for entry in formset.cleaned_data:
                institutions.append(entry.get('institution', ''))
                degrees.append(entry.get('degree', ''))
                majors.append(entry.get('major', ''))
            ed_bg_data['institution'] = institutions
            ed_bg_data['degree'] = degrees
            ed_bg_data['major'] = majors

        for field in ['credits_earned', 'masters_level_credits', 'grad_courses',
                      'undergrad_program', 'certified_states', 'certified_subjects',
                      'highschool_years', 'college_years', 'courses_taught']:
            ed_bg_data[field] = self.cleaned_data.get(field, '')

        user.education_background = ed_bg_data
        user.save()

class RecommondationForm(forms.ModelForm):

    teacher_application = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    name = forms.CharField(
        required=True,
        label='Your Name',
        widget=forms.TextInput()
    )

    position = forms.CharField(
        required=True,
        label='Your Position',
        widget=forms.TextInput()
    )

    email = forms.CharField(
        required=True,
        label='Your Email',
        widget=forms.TextInput()
    )

    terms = forms.CharField(
        required=False,
        label='I have reviewed the <a href="#" target="_blank">SUPA Administrative Guide</a> and affirm that I understand and agree to the high school\'s responsibilities as a SUPA Partner school.',
        widget=forms.HiddenInput
    )

    years = forms.CharField(
        required=True,
        label='Number of years you have worked with or known the applicant',
        widget=forms.TextInput(
            attrs={
                'class':'col-md-2',
                'placeholder':'Ex: 2'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.fields['name'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True

    class Meta:
        model = ApplicantRecommendation
        fields = [
            'email',
            'name',
            'position',
            'years',
            'upload',
            'terms'
        ]

        labels = {
            'upload': 'Please upload your letter of recommendation:'
        }

        help_texts = {
            'upload': 'Maximum file upload size is 8MB.'
        }

class StaffRecUploadForm(RecommondationForm, forms.ModelForm):

    years = forms.CharField(
        required=False,
        label='Number of years you have worked with the applicant',
        widget=forms.TextInput(
            attrs={
                'class':'col-md-2',
                'placeholder':'Ex: 2'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        del self.fields['terms']

        self.fields['email'].widget.attrs['readonly'] = False
        self.fields['name'].label = 'Name'
        self.fields['position'].label = 'Position'
        self.fields['email'].label = 'Email'

class RecommendationRequestForm(forms.Form):

    FIELD_PAIRS = [
        ('name', 'email'),
        ('name_2', 'email_2'),
        ('name_3', 'email_3'),
    ]

    teacher_application = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    name = forms.CharField(
        required=True,
        label='Name 1',
        help_text='This is how their email will be addressed. Include their first name and last name.',
        widget=forms.TextInput(
            attrs={
            'placeholder':'Ex: John Doe',
            'class':'col-md-8'
            }
        )
    )

    email = forms.EmailField(
        required=True,
        label='Email 1',
        widget=forms.EmailInput(
            attrs={
                'class':'col-md-7'
            }
        )
    )

    name_2 = forms.CharField(
        required=True,
        label='Name 2',
        help_text='This is how their email will be addressed. Include their first name and last name.',
        widget=forms.TextInput(
            attrs={
            'placeholder':'Ex: John Doe',
            'class':'col-md-8'
            }
        )
    )

    email_2 = forms.EmailField(
        required=True,
        label='Email 2',
        widget=forms.EmailInput(
            attrs={
                'class':'col-md-7'
            }
        )
    )

    name_3 = forms.CharField(
        required=True,
        label='Name 3',
        help_text='This is how their email will be addressed. Include their first name and last name.',
        widget=forms.TextInput(
            attrs={
            'placeholder':'Ex: John Doe',
            'class':'col-md-8'
            }
        )
    )

    email_3 = forms.EmailField(
        required=True,
        label='Email 3',
        widget=forms.EmailInput(
            attrs={
                'class':'col-md-7'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        recommendations_needed = kwargs.pop('recommendations_needed', None)
        super().__init__(*args, **kwargs)

        if recommendations_needed is None:
            from instructor_app.settings.inst_app_language import inst_app_language
            recommendations_needed = int(
                inst_app_language.from_db().get('recommendations_needed', '2')
            )

        self.recommendations_needed = recommendations_needed

        # Hide field pairs beyond what's needed
        for i, (name_field, email_field) in enumerate(self.FIELD_PAIRS):
            if i >= recommendations_needed:
                self.fields[name_field].widget = forms.HiddenInput()
                self.fields[name_field].required = False
                self.fields[email_field].widget = forms.HiddenInput()
                self.fields[email_field].required = False

        # Set readonly/help_text for submitted recommendations
        initial = kwargs.get('initial')
        if initial:
            try:
                teacher_app = TeacherApplication.objects.get(
                    pk=initial.get('teacher_application')
                )
            except TeacherApplication.DoesNotExist:
                return

            for i, (name_field, email_field) in enumerate(self.FIELD_PAIRS):
                if i >= recommendations_needed:
                    break
                rec_email = initial.get(email_field)
                if teacher_app.has_recommender_submitted(rec_email):
                    self.fields[email_field].widget.attrs['readonly'] = True
                    self.fields[name_field].widget.attrs['readonly'] = True
                    self.fields[email_field].help_text = 'Recommendation has been received'
                else:
                    if rec_email:
                        self.fields[email_field].help_text = (
                            'You can email this link - '
                            + teacher_app.get_recommendation_url(rec_email)
                            + ' or click the button below to resend the email'
                        )

    def clean_email(self):
        return self.data.get('email', '').lower()

    def clean_email_2(self):
        return self.data.get('email_2', '').lower()

    def clean_email_3(self):
        return self.data.get('email_3', '').lower()

    def clean(self):
        cleaned_data = super().clean()

        active_emails = []
        for i, (name_field, email_field) in enumerate(self.FIELD_PAIRS):
            if i >= self.recommendations_needed:
                break
            email_val = cleaned_data.get(email_field)
            if email_val:
                active_emails.append(email_val)

        if len(active_emails) != len(set(active_emails)):
            raise ValidationError(
                'Looks like two or more recommenders have the same email. '
                'Please enter unique email addresses'
            )

    def save(self):
        cleaned_data = self.cleaned_data

        teacher_app = TeacherApplication.objects.get(
            pk=cleaned_data['teacher_application']
        )

        teacher_app.update_recommendation_request_info(
            cleaned_data.get('name'),
            cleaned_data.get('email'),
            cleaned_data.get('name_2'),
            cleaned_data.get('email_2'),
            cleaned_data.get('name_3'),
            cleaned_data.get('email_3'),
        )

        for i, (name_field, email_field) in enumerate(self.FIELD_PAIRS):
            if i >= self.recommendations_needed:
                break
            rec_name = cleaned_data.get(name_field)
            rec_email = cleaned_data.get(email_field)
            if rec_name and rec_email:
                teacher_app.send_recommendation_request(rec_name, rec_email)

        return True


class AddCourseForm(forms.Form):
    
    id = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    course = forms.ModelMultipleChoiceField(
        queryset=None,
        label='Course(s)',
    )

    academic_year = forms.ModelChoiceField(
        queryset=None,
        label='Starting Academic Year',
    )

    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='add_teacher_application_course'
    )

    def __init__(self, teacher_application=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['academic_year'].queryset = AcademicYear.objects.all().order_by('-name')
        self.fields['course'].queryset = Course.objects.filter(
            status__iexact='active'
        ).exclude(
            id__in=ApplicantSchoolCourse.objects.filter(
                teacherapplication=teacher_application
            ).values_list('course__id', flat=True)
        )

        if teacher_application:
            self.fields['id'].initial = teacher_application.id
        
    def save(self, teacher_application):
        data = self.cleaned_data

        courses = data.get('course')
        for course in courses:
            try:
                app_course = ApplicantSchoolCourse(
                    teacherapplication=teacher_application,
                    course=course,
                    starting_academic_year=data.get('academic_year'),
                    highschool=teacher_application.highschool,
                    misc_info={}
                )

                app_course.save()
            except Exception as e:
                print(e)

        # add reviewers if applicable
        teacher_application.notify_status_change(teacher_application.status)
        return teacher_application
    
class EditSchoolCourseForm(forms.Form):
    
    id = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    highschool = forms.ChoiceField(
        choices=('', ''),
        label='High School',
        help_text='Select the school at which you instructor is applying to teach.'
    )

    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='edit_teacher_application_highschool'
    )

    def __init__(self, teacher_application=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        highschools = [
            ('', 'Select')
        ]
        highschools += [
            (h.id, h.name) for h in HighSchool.objects.filter(
                status__in=['Active']
            )
        ]
        self.fields['highschool'].choices = highschools

        if teacher_application:
            self.fields['id'].initial = teacher_application.id
            if teacher_application.highschool:
                self.fields['highschool'].initial = teacher_application.highschool.id

    def save(self, teacher_application):
        data = self.cleaned_data

        highschool = HighSchool.objects.get(pk=data.get('highschool'))
        teacher_application.highschool = highschool
        teacher_application.save()

        return teacher_application
    
class SchoolCourseForm(forms.Form):

    id = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    highschool_subsection = FFields.LongLabelField(
        required=False,
        label='',
        initial='Select your School',
        widget=FFields.LongLabelWidget(
            attrs={
                'class':'h-100 border-0',
                'style': 'padding-left: 0; font-size: 1.3em;'
            }
        )
    )

    highschool = forms.ChoiceField(
        choices=('', ''),
        label='High School',
        help_text='Select the school at which you are applying to teach. If your school is not in the list please contact us at <a href="mailto:help@canusia.com">info@canusia.com</a>'
    )

    new_school_name = forms.CharField(
        label='School Name',
        max_length=128,
        required=False,
    )

    principal_name = forms.CharField(
        label='Principal Name',
        max_length=200,
        required=False,
    )

    principal_email = forms.EmailField(
        label='Principal Email',
        required=False,
    )

    course_subsection = FFields.LongLabelField(
        required=False,
        label='',
        initial='Course Information',
        widget=FFields.LongLabelWidget(
            attrs={
                'class':'h-100 border-0',
                'style': 'padding-left: 0; font-size: 1.3em;'
            }
        )
    )

    course_description = FFields.LongLabelField(
        required=False,
        label='',
        initial='override this in __init__',
        widget=FFields.LongLabelWidget(
            attrs={
                'class':'border-0 bg-light h-100'
            }
        )
    )

    course = forms.ModelChoiceField(
        label='Which course are you applying to teach?',
        required=True,
        queryset=Course.objects.none(),
        empty_label='Select',
    )

    teacher_application = forms.CharField(
        widget=forms.HiddenInput,
        required=False
    )

    def save(self, teacher_application):
        data = self.cleaned_data

        if data.get('highschool', None):
            if data['highschool'] == '-1':
                highschool = HighSchool(
                    name=data['new_school_name'] + '**',
                    status='Pending'
                )
                highschool.save()

                self._create_principal_admin(
                    highschool,
                    data['principal_name'],
                    data['principal_email']
                )
            else:
                highschool = HighSchool.objects.get(
                    pk=data['highschool']
                )
        else:
            highschool = teacher_application.highschool

        if data['id'] == '-1':
            teacher_course = ApplicantSchoolCourse()
            teacher_course.teacherapplication = teacher_application
        else:
            teacher_course = ApplicantSchoolCourse.objects.get(
                id=data['id']
            )

        teacher_course.highschool = highschool
        teacher_course.course = data['course']
        teacher_course.misc_info = {}
        teacher_course.save()

        return teacher_course

    def _create_principal_admin(self, highschool, principal_name, principal_email):
        """Create an HSAdministrator and link them as Principal to the school."""
        from cis.models.highschool_administrator import (
            HSAdministrator, HSPosition, HSAdministratorPosition
        )

        name_parts = principal_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        hs_admin = HSAdministrator.get_or_add(
            email=principal_email.lower(),
            first_name=first_name,
            last_name=last_name,
        )

        if hs_admin is None:
            return

        position = HSPosition.get_or_add(name='Principal')

        HSAdministratorPosition.get_or_add(
            hsadmin=hs_admin,
            highschool=highschool,
            position=position,
            status='Active'
        )

    def __init__(self, teacher_application, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from instructor_app.settings.inst_app_language import inst_app_language
        app_settings = inst_app_language.from_db()
        allow_new_school = app_settings.get('allow_new_school', 'No') == 'Yes'

        # Build highschool choices
        highschools = [('', 'Select')]
        highschools += [
            (h.id, h.name) for h in HighSchool.objects.filter(
                status__in=['Active']
            )
        ]

        if allow_new_school:
            highschools.append(('-1', 'My school is not listed'))

        self.fields['highschool'].choices = highschools

        # Remove new-school fields if setting is off
        if not allow_new_school:
            self.fields.pop('new_school_name', None)
            self.fields.pop('principal_name', None)
            self.fields.pop('principal_email', None)

        # If application already has a highschool, remove school fields
        if teacher_application and teacher_application.highschool:
            for field_name in ['highschool', 'highschool_subsection',
                               'new_school_name', 'principal_name', 'principal_email']:
                self.fields.pop(field_name, None)

        # Available courses: active, open for application, not already applied for
        available_courses = Course.objects.filter(
            status__iexact='active',
            meta__available_for_si='1'
        ).order_by('name')

        try:
            self.fields['course_subsection'].initial = 'Select Course'
            available_courses = available_courses.exclude(
                id__in=ApplicantSchoolCourse.objects.filter(
                    teacherapplication=teacher_application
                ).values_list('course__id', flat=True)
            )
        except (ApplicantSchoolCourse.DoesNotExist, AttributeError):
            pass

        self.fields['course'].queryset = available_courses
        self.fields['course'].label_from_instance = lambda obj: f"{obj}: {obj.title}"

    def clean(self):
        data = super().clean()

        highschool_val = data.get('highschool')
        if highschool_val == '-1':
            if not data.get('new_school_name'):
                self.add_error('new_school_name', 'School name is required when adding a new school.')
            if not data.get('principal_name'):
                self.add_error('principal_name', 'Principal name is required when adding a new school.')
            if not data.get('principal_email'):
                self.add_error('principal_email', 'Principal email is required when adding a new school.')

        return data

class TeacherApplicantVerifyEmailForm(MetaFormMixin, forms.Form):
    """
    Step 1 of instructor applicant signup - collect name and email for verification.

    Field storage targets:
        first_name    -> user.first_name
        last_name     -> user.last_name
        middle_name   -> user.middle_name
        email         -> user.email (also sets username)
        confirm_email -> skip (validation only)
        captcha       -> (no metadata, ignored)
    """

    first_name = with_meta(
        forms.CharField(
            label='First Name',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-6 col-sm-12'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    last_name = with_meta(
        forms.CharField(
            label='Last Name',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-8 col-sm-12'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    middle_name = with_meta(
        forms.CharField(
            label='Middle Name or Initial',
            max_length=128,
            required=False,
            widget=forms.TextInput(attrs={'class': 'col-md-4 col-sm-12', 'autocomplete': 'off'}),
        ),
        target='user',
    )

    email = with_meta(
        forms.EmailField(
            label='Email Address',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true', 'email': 'true'},
    )

    confirm_email = with_meta(
        forms.EmailField(
            label='Confirm Email Address',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='skip',
        validate={'required': 'true', 'match': 'email'},
    )

    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default storage_path for fields that don't have one
        for field_name, field in self.fields.items():
            if hasattr(field, 'storage_target') and not field.storage_path:
                field.storage_path = field_name

        # Load dynamic labels/help_text from DB settings
        from instructor_app.settings.inst_app_language import inst_app_language
        form_settings = inst_app_language.from_db()
        try:
            form_labels = json.loads(
                form_settings.get('verify_form_field_messages', '{}'))
        except (json.JSONDecodeError, TypeError):
            form_labels = {}

        for field_name, field in self.fields.items():
            if form_labels.get(field_name):
                field_attr = form_labels[field_name]
                field.label = mark_safe(field_attr.get('label', field.label))
                field.help_text = mark_safe(
                    field_attr.get('help_text', field.help_text))

    def clean_first_name(self):
        return self.cleaned_data['first_name'].title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].title()

    def clean_email(self):
        data = self.cleaned_data.get('email', '').lower()

        existing = CustomUser.objects.filter(
            Q(email__iexact=data) |
            Q(username__iexact=data) |
            Q(secondary_email__iexact=data)
        )

        if existing.exists():
            user = existing.first()
            # Check if they have an unverified applicant account - resend verification
            try:
                applicant = user.teacherapplicant
                if not applicant.account_verified:
                    applicant.send_verification_request_email()
                    raise ValidationError(
                        _("A verification email has been resent to this address. Please check your email."),
                        code='invalid'
                    )
            except CustomUser.teacherapplicant.RelatedObjectDoesNotExist:
                pass

            raise ValidationError(
                _("This email is already registered in the system. Please login or choose a different email."),
                code='invalid'
            )
        return data

    def clean_confirm_email(self):
        email = self.data.get('email', '')
        confirm_email = self.data.get('confirm_email', '')

        if email.lower() != confirm_email.lower():
            raise ValidationError(_("The email addresses don't match. Please retry again."))
        return confirm_email

    def save(self):
        import uuid as _uuid
        from instructor_app.models.teacher_applicant import TeacherApplicant

        data = self.cleaned_data

        try:
            user = CustomUser()
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.middle_name = data.get('middle_name', '')
            user.email = data['email']
            user.username = data['email']
            user.set_unusable_password()
            user.save()

            applicant = TeacherApplicant(
                user=user,
                verification_id=_uuid.uuid4(),
                account_verified=False,
            )
            applicant.save()

            return applicant
        except Exception as e:
            logger.error(f'Error creating teacher applicant: {e}')
            return None


class TeacherApplicantVerifyAccountForm(forms.Form):
    """Simple form for the email verification confirmation page."""
    verification_id = forms.UUIDField(widget=forms.HiddenInput)


class TeacherApplicantProfileForm(MetaFormMixin, forms.Form):
    """
    Profile completion form for instructor applicants (step 2 of signup).
    Uses MetaFormMixin + with_meta declarative field metadata pattern.

    Field storage targets:
        user: first_name, last_name, middle_name, maiden_name (->previous_names),
              email, secondary_email, primary_phone, secondary_phone, alt_phone,
              date_of_birth, ssn, home_address (->address1), city, state,
              zip_code (->postal_code), country
        skip: password, confirm_password
    """

    class Media:
        js = (
            'js/form_validation.js',
            'js/address_auto_complete.js',
        )
        css = {
            'all': ['css/address_auto_complete.css'],
        }

    # ==================== Name Fields ====================

    first_name = with_meta(
        forms.CharField(
            label='First Name',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-6 col-sm-12'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    last_name = with_meta(
        forms.CharField(
            label='Last Name',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-8 col-sm-12'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    middle_name = with_meta(
        forms.CharField(
            label='Middle Name or Initial',
            max_length=128,
            required=False,
            widget=forms.TextInput(attrs={'class': 'col-md-4 col-sm-12'}),
        ),
        target='user',
    )

    maiden_name = with_meta(
        forms.CharField(
            label='Maiden Name (if applicable)',
            max_length=128,
            required=False,
            widget=forms.TextInput(attrs={'class': 'col-md-8 col-sm-12'}),
        ),
        target='user',
        path='previous_names',
    )

    # ==================== Email ====================

    email = with_meta(
        forms.EmailField(
            label='Email Address',
            disabled=True,
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true', 'email': 'true'},
    )

    secondary_email = with_meta(
        forms.EmailField(
            label='Personal Email',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'email': 'true'},
    )

    # ==================== Phone ====================

    primary_phone = with_meta(
        forms.CharField(
            label='Work Phone (10-digit)',
            max_length=15,
            help_text='10 digits (i.e. 5551231234)',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    secondary_phone = with_meta(
        forms.CharField(
            label='Personal Phone (10-digit)',
            max_length=15,
            help_text='10 digits (i.e. 5551231234)',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    alt_phone = with_meta(
        forms.CharField(
            label='Other Phone (10-digit)',
            max_length=15,
            required=False,
            help_text='10 digits (i.e. 5551231234)',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
    )

    # ==================== Personal Info ====================

    date_of_birth = with_meta(
        forms.DateField(
            widget=forms.SelectDateWidget(),
            label='Date of Birth',
        ),
        target='user',
        validate={'required': 'true'},
    )

    ssn = with_meta(
        forms.CharField(
            label='SSN',
            required=False,
            help_text='US SSN Eg: xxx-xx-xxxx',
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
    )

    # ==================== Address ====================

    home_address = with_meta(
        forms.CharField(
            label='Home Address',
            max_length=128,
            help_text='Do not enter symbols (e.g. #). You may include Apt, Unit, Box etc.',
            widget=forms.TextInput(attrs={'class': 'col-md-8 col-sm-12'}),
        ),
        target='user',
        path='address1',
        validate={'required': 'true'},
    )

    city = with_meta(
        forms.CharField(
            label='City',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    state = with_meta(
        forms.CharField(
            label='State',
            max_length=128,
            widget=forms.TextInput(attrs={'class': 'col-md-5 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    zip_code = with_meta(
        forms.CharField(
            label='Zip/Postal Code',
            max_length=10,
            widget=forms.TextInput(attrs={'class': 'col-md-4 col-sm-6'}),
        ),
        target='user',
        path='postal_code',
        validate={'required': 'true'},
    )

    country = with_meta(
        forms.CharField(
            label='Country',
            max_length=50,
            widget=forms.TextInput(attrs={'class': 'col-md-4 col-sm-6'}),
        ),
        target='user',
        validate={'required': 'true'},
    )

    # ==================== Password ====================

    password = with_meta(
        forms.CharField(
            max_length=128,
            label='Create Password or Passphrase',
            validators=[
                DictionaryValidator(words=['banned_word'], threshold=0.9),
                LengthValidator(min_length=12),
                ComplexityValidator(complexities=dict(
                    UPPER=1,
                    LOWER=1,
                    DIGITS=1
                ))
            ],
            help_text='Please choose a strong password, with min. 12 characters, at least 1 digit, 1 special character and 1 uppercase letter',
            widget=forms.PasswordInput(attrs={'class': 'col-md-6 col-sm-12', 'autocomplete': 'off'}),
        ),
        target='skip',
        validate={'required': 'true', 'min-length': '12'},
    )

    confirm_password = with_meta(
        forms.CharField(
            max_length=128,
            label='Retype Password or Passphrase',
            widget=forms.PasswordInput(attrs={'class': 'col-md-6 col-sm-12', 'autocomplete': 'off'}),
        ),
        target='skip',
        validate={'required': 'true', 'match': 'password'},
    )

    # ==================== Form Methods ====================

    def __init__(self, applicant=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.applicant = applicant

        # Set default storage_path for fields that don't have one
        for field_name, field in self.fields.items():
            if hasattr(field, 'storage_target') and not getattr(field, 'storage_path', None):
                field.storage_path = field_name

        # Configure DOB year range
        this_year = date.today().year
        years = range(this_year - 80, this_year - 20 + 1)
        self.fields['date_of_birth'].widget = forms.SelectDateWidget(years=years)

        # Load dynamic labels from DB
        self._load_field_labels_from_db()

        # Populate initial values from applicant instance
        if applicant:
            self._populate_initial_from_instance(applicant)

    def _load_field_labels_from_db(self):
        """Load dynamic labels/help_text from DB settings"""
        from instructor_app.settings.inst_app_language import inst_app_language
        try:
            form_settings = inst_app_language.from_db()
            form_labels = json.loads(
                form_settings.get('profile_form_field_messages', '{}'))
        except (json.JSONDecodeError, TypeError):
            form_labels = {}

        for field_name, field in self.fields.items():
            if form_labels.get(field_name):
                field_attr = form_labels.get(field_name, {})
                if field_attr.get('label'):
                    field.label = mark_safe(field_attr.get('label'))
                if field_attr.get('help_text'):
                    field.help_text = mark_safe(field_attr.get('help_text'))

    def _populate_initial_from_instance(self, applicant):
        """Populate form initial values from applicant using field metadata."""
        if not applicant:
            return

        user = applicant.user

        for name, field in self.fields.items():
            target = getattr(field, 'storage_target', None)
            if not target or target == 'skip':
                continue

            path = getattr(field, 'storage_path', None) or name

            try:
                if target == 'user' and user:
                    self.initial[name] = getattr(user, path, '')
            except AttributeError:
                pass

    def save(self, applicant=None):
        """Save form data to user model using metadata, handle password separately."""
        from datetime import datetime

        data = self.cleaned_data
        applicant = applicant or self.applicant

        if not applicant:
            raise ValueError("Applicant instance is required for save")

        user = applicant.user

        # Save fields using metadata (only user target for this form)
        self._save_fields_to_models(user=user, commit=False)

        # Handle password separately
        if data.get('password'):
            user.set_password(data['password'])

        # Update username to match email
        user.username = user.email

        user.save()

        # Mark signup as complete
        applicant.account_verified_on = datetime.now()
        applicant.save()

        return user

    # ==================== Validation Methods ====================

    def clean_first_name(self):
        return self.cleaned_data['first_name'].title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].title()

    def clean_email(self):
        email = self.cleaned_data['email'].lower()

        if self.applicant:
            qs = CustomUser.objects.filter(
                email__iexact=email
            ).exclude(id=self.applicant.user.id)

            if qs.exists():
                raise ValidationError(
                    _('This email is already registered. Please use a different email or contact our office for assistance')
                )
        return email

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password', '')
        confirm_password = self.cleaned_data['confirm_password']

        if password != confirm_password:
            raise ValidationError(_("The passwords don't match. Please retry again."))
        return confirm_password


class TeacherApplicantEditableForm(TeacherApplicantProfileForm):
    """
    Profile form without password fields.
    Used for editing profile after initial signup.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in ['password', 'confirm_password']:
            if field in self.fields:
                del self.fields[field]


class HSAdminAddTeacherForm(TeacherApplicantProfileForm):
    """Profile form for HS admins to create a new teacher applicant.
    Inherits all profile fields but removes password and enables email."""

    def __init__(self, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        self.fields['email'].disabled = False

    def clean_email(self):
        from django.db.models import Q
        data = self.cleaned_data.get('email', '').lower()
        existing = CustomUser.objects.filter(
            Q(email__iexact=data) | Q(username__iexact=data)
        )
        if existing.exists():
            raise ValidationError("This email is already registered in the system.")
        return data

    def save(self, applicant=None):
        """Create CustomUser + TeacherApplicant (pre-verified). Returns the TeacherApplicant."""
        from instructor_app.models.teacher_applicant import TeacherApplicant
        user = CustomUser()
        self._save_fields_to_models(user=user, commit=False)
        user.username = user.email
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        else:
            user.set_unusable_password()
        user.save()

        applicant = TeacherApplicant(
            user=user,
            account_verified=True,
        )
        applicant.save()
        return applicant
