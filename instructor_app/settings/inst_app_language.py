import json
from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError

from django.utils.safestring import mark_safe
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, HTML
from form_fields import fields as FFields

from cis.models.term import Term, AcademicYear
from cis.models.settings import Setting
from cis.validators import validate_json

class SettingForm(forms.Form):
    class Media:
        js = ('js/checklist_settings.js',)

    STATUS_OPTIONS = [
        ('', 'Select'),
        ('Yes', 'Yes'),
        ('No', 'No')
    ]

    is_accepting_new = forms.ChoiceField(
        choices=STATUS_OPTIONS,
        label='Accepting New Applications',
        help_text='Turning this off will stop all emails, and prevent any new or in-progress applications from being submitted. Staff can override status internally on each application',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'}))

    allow_new_school = forms.ChoiceField(
        choices=STATUS_OPTIONS,
        label='Allow Applicants to Enter New School',
        help_text='If Yes, applicants can add a school not already in the system, along with the principal\'s name and email.',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'}))

    closed_message = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed when no longer accepting applications',
        label="Applications Closed Message")

    page_intros_header = FFields.ReadOnlyField(
        required=False,
        label=mark_safe('<h4>Page Introductions</h4><p class="text-muted">These messages are displayed at the top of each page in the applicant portal.</p>'),
        initial='',
        widget=FFields.LongLabelWidget(attrs={'style': 'display:none;'}),
    )

    dashboard_blurb = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed at the top in Dashboard. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'dashboard\')" >See Preview</a>',
        label="Dashboard Intro.")

    course_blurb = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed above course selection drop down. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'courses\')" >See Preview</a>',
        label="Course Description Blurb")

    ed_bg_page_header = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed at the top of Educational Background Page. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'ed_bg_page_header\')" >See Preview</a>',
        label="Educational Background Page Intro")

    file_upload_page_header = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed at the top of material upload page. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'file_upload_page_header\')" >See Preview</a>',
        label="Material Upload Page Intro")

    submit_page_header = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed at the top of submit page. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'submit_page_header\')" >See Preview</a>',
        label="Application Submit Page Intro")

    app_not_editable_message = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed on the review page when the application is no longer editable by the applicant.',
        label="Application Not Editable Message")

    # number of recommendations needed 0-3
    recommendations_needed = forms.IntegerField(
        min_value=0,
        max_value=3
    )

    rec_req_blurb = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed at the top of recommendation request page. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_req\')" >See Preview</a>',
        label="Rec. Request Page Intro.")

    rec_req_blurb_bottom = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed at the bottom before \'Request Recommendation\' button. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_bottom\')" >See Preview</a>',
        label="Rec. Request Page Intro.")

    rec_req_email_subject = forms.CharField(
        max_length=None,
        required=False,
        help_text='',
        label="Rec. Request Email Subject")

    rec_req_email_message = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Customize with {{recommender_name}}, {{teacher_first_name}}, {{teacher_last_name}}, {{recommendation_link}}, {{highschool}}, {{course_titles}}. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_req_email_message\')" >See Preview</a>',
        label="Rec. Request Email Message")

    rec_received_email_subject = forms.CharField(
        max_length=None,
        required=False,
        help_text='',
        label="Rec. Received Email Subject")

    rec_received_email_message = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Customize with {{teacher_first_name}}, {{teacher_last_name}}, {{recommender_name}}. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_received_email_message\')" >See Preview</a>',
        label="Rec. Received Email Message")

    rec_submit_page_header = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed at the top of recommendation submission page. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_submit_page_header\')" >See Preview</a>',
        label="Rec. Submit Page Intro")

    rec_submit_page_pre_form = forms.CharField(
        max_length=None,
        required=False,
        widget=forms.Textarea,
        help_text='Displayed after teacher details, and before recommendation form. <a href="#" class="float-right" onClick="do_bulk_action(\'inst_app_language\', \'rec_submit_page_header\')" >See Preview</a>',
        label="Rec. Submit Form Intro.")

    signup_onboarding_header = FFields.ReadOnlyField(
        required=False,
        label=mark_safe('<h4>Signup &amp; Onboarding</h4><p class="text-muted">Content shown during the applicant registration and email verification flow.</p>'),
        initial='',
        widget=FFields.LongLabelWidget(attrs={'style': 'display:none;'}),
    )

    signup_intro = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed at the top of the signup page',
        label="Signup Page Intro")

    verify_form_field_messages = forms.CharField(
        max_length=None,
        validators=[validate_json],
        widget=forms.Textarea,
        help_text='JSON: customize field labels & help text. Keys: first_name, last_name, middle_name, email, confirm_email. Each with "label" and "help_text".',
        label="Verify Email Form Field Labels")

    profile_form_field_messages = forms.CharField(
        max_length=None,
        validators=[validate_json],
        widget=forms.Textarea,
        help_text='JSON: customize profile form field labels & help text. Keys: first_name, last_name, middle_name, maiden_name, email, secondary_email, primary_phone, secondary_phone, alt_phone, date_of_birth, ssn, home_address, city, state, zip_code, country, password, confirm_password. Each with "label" and "help_text".',
        label="Profile Form Field Labels")

    verify_email_subject = forms.CharField(
        max_length=None,
        help_text='Subject line for the email verification email',
        label="Verification Email Subject")

    verification_email = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Customize with {{teacher_first_name}}, {{teacher_last_name}}, {{teacher_email}}, {{verification_link}}',
        label="Verification Email Message")

    awaiting_verify_intro = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed after applicant submits their email for verification',
        label="Awaiting Verification Page Intro")

    confirm_verify_intro = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed on the email confirmation page',
        label="Confirm Verification Page Intro")

    certification_text = forms.CharField(
        max_length=None,
        widget=forms.Textarea,
        help_text='Displayed next to the certification checkbox on the application submit page.',
        label="Certification of Applicant Text")

    ed_bg_form_config = forms.CharField(
        max_length=None,
        required=False,
        validators=[validate_json],
        widget=forms.HiddenInput(),
        label="Ed. Background Form Configuration",
    )

    checklist_config = forms.CharField(
        max_length=None,
        required=False,
        validators=[validate_json],
        widget=forms.HiddenInput(),
        label="Application Checklist Configuration",
    )

    fc_review_status_label = forms.ChoiceField(
        required=False,
        label="Faculty Review Trigger Status",
        help_text='When an application is set to this status, faculty coordinator reviewers will be automatically assigned and notified.',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    REC_FIELDS = [
        'rec_req_blurb', 'rec_req_blurb_bottom',
        'rec_req_email_subject', 'rec_req_email_message',
        'rec_received_email_subject', 'rec_received_email_message',
        'rec_submit_page_header', 'rec_submit_page_pre_form',
    ]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('is_accepting_new') == 'No' and not cleaned_data.get('closed_message', '').strip():
            self.add_error('closed_message', 'This field is required when not accepting new applications.')

        rec_needed = int(cleaned_data.get('recommendations_needed', 0) or 0)
        if rec_needed > 0:
            for field_name in self.REC_FIELDS:
                if not cleaned_data.get(field_name, '').strip():
                    self.add_error(field_name, 'This field is required when recommendations are enabled.')

        return cleaned_data

    def _to_python(self):
        """
        Return dict of form elements from $_POST
        """
        return {
            'closed_message': self.cleaned_data.get('closed_message'),
            'is_accepting_new': self.cleaned_data.get('is_accepting_new'),
            'allow_new_school': self.cleaned_data.get('allow_new_school'),
            'recommendations_needed': self.cleaned_data.get('recommendations_needed'),
            
            'dashboard_blurb': self.cleaned_data.get('dashboard_blurb'),
            'course_blurb': self.cleaned_data.get('course_blurb'),
            'rec_req_blurb': self.cleaned_data.get('rec_req_blurb'),
            'rec_req_blurb_bottom': self.cleaned_data.get('rec_req_blurb_bottom'),
            'rec_submit_page_header': self.cleaned_data.get('rec_submit_page_header'),
            'rec_req_email_subject': self.cleaned_data.get('rec_req_email_subject'),            
            'rec_req_email_message': self.cleaned_data.get('rec_req_email_message'),
            'rec_req_email_subject': self.cleaned_data.get('rec_req_email_subject'),
            'rec_received_email_subject': self.cleaned_data.get('rec_received_email_subject'),
            'rec_received_email_message': self.cleaned_data.get('rec_received_email_message'),
            'file_upload_page_header': self.cleaned_data.get('file_upload_page_header'),
            'submit_page_header': self.cleaned_data.get('submit_page_header'),
            'app_not_editable_message': self.cleaned_data.get('app_not_editable_message'),
            'ed_bg_page_header': self.cleaned_data.get('ed_bg_page_header'),
            'rec_submit_page_pre_form': self.cleaned_data.get('rec_submit_page_pre_form'),
            'signup_intro': self.cleaned_data.get('signup_intro'),
            'verify_form_field_messages': self.cleaned_data.get('verify_form_field_messages'),
            'profile_form_field_messages': self.cleaned_data.get('profile_form_field_messages'),
            'verify_email_subject': self.cleaned_data.get('verify_email_subject'),
            'verification_email': self.cleaned_data.get('verification_email'),
            'awaiting_verify_intro': self.cleaned_data.get('awaiting_verify_intro'),
            'confirm_verify_intro': self.cleaned_data.get('confirm_verify_intro'),
            'certification_text': self.cleaned_data.get('certification_text'),
            'ed_bg_form_config': self.cleaned_data.get('ed_bg_form_config'),
            'checklist_config': self.cleaned_data.get('checklist_config'),
            'fc_review_status_label': self.cleaned_data.get('fc_review_status_label', 'Ready for Review'),
        }

class inst_app_language(SettingForm):
    key = "inst_app_language"

    def preview(self, request, field_name):

        from django.template.loader import get_template, render_to_string
        from django.template import Context, Template
        from django.shortcuts import render, get_object_or_404
        
        from instructor_app.forms.teacher_applicant import (
            TeacherApplicantProfileForm,
            SchoolCourseForm,
            RecommendationRequestForm,
            RecommondationForm,
            EdBgForm,
            AppUploadForm
        )

        email_settings = self.from_db()

        if field_name in ['dashboard']:
            # content = self.from_db().get('student_terms')
            template = 'instructor_app/dashboard.html'
            return render(
                request,
                template,
                {
                    'intro':self.from_db().get('dashboard_blurb')
                },
            )
        elif field_name in ['file_upload_page_header']:
            return render(
                request,
                'instructor_app/manage_uploads.html',
                {
                    'page_intro': self.from_db().get('file_upload_page_header'),
                }
            )
        elif field_name in ['rec_submit_page_header']:
            return render(
                request,
                'instructor_app/submit_recommendation.html',
                {
                    'page_intro': self.from_db()['rec_submit_page_header'],
                    'pre_form': self.from_db()['rec_submit_page_pre_form'],
                }
            )
        elif field_name in ['submit_page_header']:
            return render(
                request,
                'instructor_app/review_application.html',
                {
                    'menu': None,
                    'page_intro': self.from_db().get('submit_page_header', 'Change in Settings'),
                }
            )
        elif field_name in ['ed_bg_page_header']:
            return render(
                request,
                'instructor_app/manage_ed_bg.html',
                {
                    'menu': None,
                    'page_intro': self.from_db().get('ed_bg_page_header', 'Change in Settings'),
                    'teacher_application': None,
                    'form': EdBgForm(),
                    'formset': None,
                }
            )
        elif field_name in ['rec_req', 'rec_bottom']:
            return render(
                request,
                'instructor_app/request_recommendation.html',
                {
                    'menu': None,
                    'page_intro': self.from_db()['rec_req_blurb'],
                    'page_footer': self.from_db()['rec_req_blurb_bottom'],
                    'teacher_application': None,
                    'recommendations': None,
                    'form': None
                }
            )
        if field_name in ['courses']:
            # content = self.from_db().get('student_terms')

            form = SchoolCourseForm(
                teacher_application=None,
                initial={
                    
                    'course_description': self.from_db()['course_blurb']
                }
            )

            template = 'instructor_app/manage_course.html'
            return render(
                request,
                template,
                {
                    'form': form,
                    'teacher_application': None,
                    'interested_courses': None
                },
            )
        if field_name == 'rec_req_email_message':
            email = email_settings.get('rec_req_email_message')
            subject = email_settings.get('course_reviewed_email_subject')
        if field_name == 'rec_received_email_message':
            email = email_settings.get('rec_received_email_message')
            subject = email_settings.get('course_reviewed_email_subject')
        
        email_template = Template(email)
        context = Context({
            'recommender_name': request.user.first_name,
            'teacher_first_name': request.user.first_name,
            'teacher_last_name': request.user.last_name,
            'teacher_email': request.user.email,
            'highschool': 'High School',
            'recommendation_link': 'https://custom-url',
            'course': 'Course',
            'course_titles': 'Course 1 and Course 2',
        })

        text_body = email_template.render(context)
        
        return render(
            request,
            'cis/email.html',
            {
                'message': text_body
            }
        )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from instructor_app.models.teacher_applicant import TeacherApplication
        self.fields['fc_review_status_label'].choices = TeacherApplication.STATUS_OPTIONS

        self.request = request
        self.helper = FormHelper()
        self.helper.attrs = {'target':'_blank'}
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy(
            'setting:run_record', args=[request.GET.get('report_id')])
        self.helper.add_input(Submit('submit', 'Save Setting'))

        # Build ed bg form config visual UI
        ed_bg_configurable_fields = [
            ('other_name', 'Name as it appears on transcripts'),
            ('credits_earned', 'Credit hours earned beyond highest degree'),
            ('masters_level_credits', "Master's-level credits in discipline"),
            ('grad_courses', 'Graduate coursework pertaining to course'),
            ('undergrad_program', 'Undergraduate program description'),
            ('certified_states', 'State(s) of permanent certification'),
            ('certified_subjects', 'Subject(s) of permanent certification'),
            ('highschool_years', 'Total years teaching high school'),
            ('college_years', 'Total years teaching college'),
            ('courses_taught', 'Subjects taught related to course'),
        ]

        eb_rows_html = ""
        for name, default_label in ed_bg_configurable_fields:
            eb_rows_html += (
                '<tr>'
                f'<td>{default_label}</td>'
                '<td class="text-center">'
                f'<input type="checkbox" class="ebc-visible" data-field="{name}">'
                '</td>'
                '<td class="text-center">'
                f'<input type="checkbox" class="ebc-required" data-field="{name}">'
                '</td>'
                '<td>'
                f'<input type="text" class="form-control form-control-sm ebc-label" '
                f'data-field="{name}" placeholder="{default_label}">'
                '</td>'
                '</tr>'
            )

        ed_bg_config_html = (
            '<div id="ed-bg-form-config-ui" class="card mb-3">'
            '<div class="card-header"><h5 class="mb-0">Ed. Background Form Fields</h5></div>'
            '<div class="card-body">'
            '<table class="table table-sm table-bordered">'
            '<thead><tr>'
            '<th>Field</th>'
            '<th class="text-center" style="width:80px">Visible</th>'
            '<th class="text-center" style="width:80px">Required</th>'
            '<th style="width:250px">Custom Label</th>'
            '</tr></thead>'
            '<tbody>'
        )
        ed_bg_config_html += eb_rows_html
        ed_bg_config_html += (
            '</tbody></table>'
            '<small class="form-text text-muted">If no fields are checked, all fields will be shown by default.</small>'
            '</div></div>'
        )

        rec_field_ids = [
            'id_rec_req_blurb', 'id_rec_req_blurb_bottom',
            'id_rec_req_email_subject', 'id_rec_req_email_message',
            'id_rec_received_email_subject', 'id_rec_received_email_message',
            'id_rec_submit_page_header', 'id_rec_submit_page_pre_form',
        ]
        rec_selectors = ','.join(f'#{fid}' for fid in rec_field_ids)

        toggle_js = (
            '<script>'
            '$(document).ready(function(){'
            '  function toggleClosedMessage(){'
            '    var val=$("#id_is_accepting_new").val();'
            '    var $row=$("#id_closed_message").closest("div.form-group,div.mb-3").first();'
            '    if(val==="No"){'
            '      $row.slideDown();'
            '    }else{'
            '      $row.slideUp();'
            '    }'
            '  }'
            '  $("#id_is_accepting_new").on("change",toggleClosedMessage);'
            '  toggleClosedMessage();'
            ''
            '  var recFields=$("' + rec_selectors + '");'
            '  function toggleRecFields(){'
            '    var val=parseInt($("#id_recommendations_needed").val())||0;'
            '    recFields.each(function(){'
            '      var $row=$(this).closest("div.form-group,div.mb-3").first();'
            '      if(val>0){$row.slideDown();}else{$row.slideUp();}'
            '    });'
            '  }'
            '  $("#id_recommendations_needed").on("change input",toggleRecFields);'
            '  toggleRecFields();'
            '});'
            '</script>'
        )

        ed_bg_js = (
            '<script>'
            'function initEdBgFormConfig(){'
            '  var $hidden=$("input[name=\'ed_bg_form_config\']");'
            '  if(!$hidden.length)return;'
            '  var $ui=$("#ed-bg-form-config-ui");'
            '  if(!$ui.length)return;'
            '  if($ui.data("ebc-init"))return;'
            '  $ui.data("ebc-init",true);'
            '  var config={};'
            '  try{config=JSON.parse($hidden.val()||"{}");}catch(e){config={};}'
            '  var fields=config.fields||[];'
            '  var required=config.required||[];'
            '  var labels=config.labels||{};'
            '  $ui.find(".ebc-visible").each(function(){'
            '    $(this).prop("checked",fields.indexOf($(this).data("field"))!==-1);'
            '  });'
            '  $ui.find(".ebc-required").each(function(){'
            '    $(this).prop("checked",required.indexOf($(this).data("field"))!==-1);'
            '  });'
            '  $ui.find(".ebc-label").each(function(){'
            '    var l=labels[$(this).data("field")];'
            '    if(l)$(this).val(l);'
            '  });'
            '  function sync(){'
            '    var vis=[];'
            '    $ui.find(".ebc-visible:checked").each(function(){vis.push($(this).data("field"));});'
            '    var req=[];'
            '    $ui.find(".ebc-required:checked").each(function(){req.push($(this).data("field"));});'
            '    var lbl={};'
            '    $ui.find(".ebc-label").each(function(){'
            '      var v=$(this).val().trim();'
            '      if(v)lbl[$(this).data("field")]=v;'
            '    });'
            '    var c={fields:vis,required:req};'
            '    if(Object.keys(lbl).length>0)c.labels=lbl;'
            '    $hidden.val(JSON.stringify(c));'
            '  }'
            '  $ui.on("change",".ebc-required",function(){'
            '    if($(this).is(":checked")){'
            '      $ui.find(".ebc-visible[data-field=\'"+$(this).data("field")+"\']").prop("checked",true);'
            '    }'
            '    sync();'
            '  });'
            '  $ui.on("change",".ebc-visible",function(){'
            '    if(!$(this).is(":checked")){'
            '      $ui.find(".ebc-required[data-field=\'"+$(this).data("field")+"\']").prop("checked",false);'
            '    }'
            '    sync();'
            '  });'
            '  $ui.on("input",".ebc-label",sync);'
            '  $hidden.closest("form").on("submit",sync);'
            '}'
            '$(document).ready(function(){initEdBgFormConfig();});'
            '$(document).ajaxComplete(function(){initEdBgFormConfig();});'
            '</script>'
        )

        # Build layout with config UI inserted before the hidden field
        field_keys = list(self.fields.keys())
        layout_fields = []
        for key in field_keys:
            if key == 'ed_bg_form_config':
                layout_fields.append(HTML(ed_bg_config_html))
            layout_fields.append(key)

        self.helper.layout = Layout(
            HTML(toggle_js),
            HTML(ed_bg_js),
            *layout_fields
        )

    def install(self):
        defaults = {
            'allow_new_school': 'No',
            'dashboard_blurb': "Change this in Settings -> Instructor -> Application Language",
            'course_blurb': "Change this in Settings -> Instructor -> Application Language",
            'rec_req_blurb': "Change this in Settings -> Instructor -> Application Language",
            'rec_req_blurb_bottom': "Change this in Settings -> Instructor -> Application Language",
            'rec_req_email_subject': "Change this in Settings -> Instructor -> Application Language",
            'rec_req_email_message': "Change this in Settings -> Instructor -> Application Language",
            'rec_received_email_subject': "Change this in Settings -> Instructor -> Application Language",
            'rec_received_email_message': "Change this in Settings -> Instructor -> Application Language",
            'rec_submit_page_header': "Change this in Settings -> Instructor -> Application Language",
            'rec_submit_page_pre_form': "Change this in Settings -> Instructor -> Application Language",
            'app_not_editable_message': 'Your application is no longer editable.',
            'ed_bg_page_header': 'Change this in settings',
            'signup_intro': 'Change this in Settings -> Instructor -> Application Language',
            'verify_form_field_messages': '{}',
            'profile_form_field_messages': '{}',
            'verify_email_subject': 'Verify your email address',
            'verification_email': '<p>Dear {{teacher_first_name}},</p><p>Thank you for starting your instructor application. Please click the link below to verify your email address:</p><p><a href="{{verification_link}}">Verify Email Address</a></p>',
            'awaiting_verify_intro': '<p>Thank you! Please check your email for a verification link. Click the link to continue your application.</p>',
            'confirm_verify_intro': '<p>Click the button below to confirm your email address and continue with your application.</p>',
            'certification_text': 'CERTIFICATION OF APPLICANT: I certify that there are no misrepresentations or falsifications in my answers to the questions above. I am aware that any misstatements disclosed through investigation will constitute sufficient grounds, disqualification and/or dismissal from employment.',
            'ed_bg_form_config': '{}',
        }

        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting()
            setting.key = self.key

        setting.value = defaults
        setting.save()

    @classmethod
    def from_db(cls):
        try:
            setting = Setting.objects.get(key=cls.key)
            return setting.value
        except Setting.DoesNotExist:
            return {}

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
            'status': 'success'})
