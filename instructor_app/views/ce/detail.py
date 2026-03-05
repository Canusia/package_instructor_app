import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt

from instructor_app.models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
    ApplicantRecommendation,
    ApplicantCourseReviewer,
    ApplicantSchoolCourse,
    ApplicationUpload
)
from cis.models.note import TeacherApplicationNote

from cis.menu import cis_menu, draw_menu
from instructor_app.forms.teacher_applicant import (
    RecommendationRequestForm,
    StaffRecUploadForm,
    EdBgForm,
    EducationEntryFormSet,
    AppUploadForm,
    EditTeacherApplicationForm,
    ApplicantCourseFinalStatusForm,
    TeacherApplicantEditableForm,
    MigrateForm,
)
from instructor_app.settings.inst_app_language import inst_app_language

logger = logging.getLogger(__name__)


@xframe_options_exempt
def detail(request, record_id):
    '''
    Record details page
    '''
    template = 'instructor_app/ce/details.html'
    record = get_object_or_404(TeacherApplication, pk=record_id)
    if not record.misc_info:
        record.misc_info = {}

    app_settings = inst_app_language.from_db()
    recommendations_needed = int(app_settings.get('recommendations_needed', '2'))

    applicant = TeacherApplicant.objects.filter(user=record.user).first()
    app_profile_form = TeacherApplicantEditableForm(
        applicant=applicant
    )

    # Set session key so address autocomplete endpoint doesn't return session_expired
    request.session['record_key'] = str(record.user.pk)

    migration_form = MigrateForm(record)

    action = request.GET.get('action')
    if request.method == 'POST':
        action = request.POST.get('action')

        if request.POST.get('action') == 'migrate_teacher_application':
            migration_form = MigrateForm(
                record=record, data=request.POST
            )

            if migration_form.is_valid():
                success, message = migration_form.save(request, record)

                if not success:
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        'Your request was processed with some errors.<br>' + '<br>'.join(message),
                        'list-group-item-warning')
                else:
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        'Successfully completed request. ' + ','.join(message),
                        'list-group-item-success')
            else:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Please correct the errors and try again',
                    'list-group-item-danger')

        elif action == 'update_teacher':
            app_profile_form = TeacherApplicantEditableForm(
                applicant,
                request.POST
            )

            if app_profile_form.is_valid():
                app_profile_form.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'The applicant profile has been successfully updated.',
                    'list-group-item-success')
                return redirect(
                    'ce_instructor_app:teacher_application',
                    record_id=record.id
                )

        elif action == 'Import as Instructor':
            try:
                teacher = record.import_as_teacher()
                record.remove_role()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Successfully imported as teacher. Please update the username, and review the course certification status.',
                    'list-group-item-success'
                )
                return redirect(
                    'cis:instructor',
                    record_id=teacher.id
                )
            except KeyError as e:
                logger.exception('Import as teacher failed')
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Please make sure the decision letter sent date has been entered.',
                    'list-group-item-danger'
                )

    if action == 'delete_reviewer':
        reviewer_id = request.GET.get('reviewer')
        reviewer = get_object_or_404(ApplicantCourseReviewer, pk=reviewer_id)

        reviewer.delete()
        messages.add_message(
            request,
            messages.SUCCESS,
            f'The reviewer has been successfully deleted',
            'list-group-item-success'
        )
        return redirect(
            'ce_instructor_app:teacher_application',
            record_id=record.id
        )

    form = EditTeacherApplicationForm(initial={
        'status': record.status,
        'assigned_to': record.assigned_to,
        'invite_to_interview': record.misc_info.get('invite_to_interview'),
        'interviewed_on': record.misc_info.get('interviewed_on'),
        'decision_letter_sent_on': record.misc_info.get('decision_letter_sent_on'),
        'action': 'edit_application',
        'participating_acad_year': record.misc_info.get('participating_acad_year'),
        'grad_credit': record.misc_info.get('grad_credit'),
        'checklist': record.misc_info.get('checklist'),
        'psid': record.user.psid,
        'migration_form': migration_form
    })

    if not record.misc_info:
        record.misc_info = {}

    ed_bg = record.user.education_background
    if not ed_bg:
        ed_bg = {}

    rec_req_form = rec_upload_form = ed_bg_form = ed_bg_formset = app_upload_form = None
    if request.method == 'POST':
        if request.POST.get('action') == 'upload_recommendation':
            recommendation = ApplicantRecommendation(
                teacher_application=record
            )

            rec_upload_form = StaffRecUploadForm(
                request.POST,
                request.FILES,
                instance=recommendation)

            if rec_upload_form.is_valid():
                recommendation = rec_upload_form.save(commit=False)
                recommendation.recommendation = {}
                recommendation.recommendation['number_years'] = rec_upload_form.cleaned_data.get('years', '-')

                recommendation.submitter = {}
                recommendation.submitter['name'] = rec_upload_form.cleaned_data['name']
                recommendation.submitter['position'] = rec_upload_form.cleaned_data['position']
                recommendation.submitter['email'] = rec_upload_form.cleaned_data.get('email')

                recommendation.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'The recommendation has been successfully uploaded',
                    'list-group-item-success')

        if request.POST.get('action') == 'send_recommendation_link':
            rec_req_form = RecommendationRequestForm(
                request.POST,
                recommendations_needed=recommendations_needed
            )

            if rec_req_form.is_valid():
                result = rec_req_form.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Successfully sent recommendation request.',
                    'list-group-item-success')
            else:
                logger.warning('Recommendation request form errors: %s', rec_req_form.errors)

        if request.POST.get('action') == 'edit_application':
            form = EditTeacherApplicationForm(request.POST)
            if form.is_valid():
                form.save(record)

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Successfully updated application',
                    'list-group-item-success')
            else:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Please correct the error(s) and try again',
                    'list-group-item-warning')

        if request.POST.get('action') == 'update_course_status':
            update_course_form = ApplicantCourseFinalStatusForm(request.POST)
            if update_course_form.is_valid():
                update_course_form.save()
                return JsonResponse({
                    'message': 'Successfully updated course status.',
                    'status': 'success'
                }, status=200)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': update_course_form.errors.as_json()
                }, status=400)

        if request.POST.get('action') == 'update_ed_background':
            ed_bg_form = EdBgForm(request.POST)
            ed_bg_formset = EducationEntryFormSet(request.POST)
            if ed_bg_form.is_valid() and ed_bg_formset.is_valid():
                ed_bg_form.save(record, formset=ed_bg_formset)
                return JsonResponse({
                    'message': 'Successfully saved educational background information.',
                    'status': 'success'
                }, status=200)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': ed_bg_form.errors.as_json()
                }, status=400)

        if request.POST.get('action') == 'app_upload':
            app_upload_form = AppUploadForm(
                record,
                request.POST,
                request.FILES
            )

            if request.FILES.get('upload') and app_upload_form.is_valid():
                upload = app_upload_form.save(commit=False)
                upload.teacher_application = record
                upload.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Your file has been uploaded. Please repeat the step for additional files. ',
                    'list-group-item-success')
            else:
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'Unable to upload file. Did you select a file?',
                    'list-group-item-danger')

    course_status_forms = {}
    for course in record.selected_courses:
        course_status_forms[course.id] = ApplicantCourseFinalStatusForm(
            initial={
                'application_course_id': course.id,
                'note': course.note,
                'decision': course.status
            }
        )

    if not rec_req_form:
        rec_req_form = RecommendationRequestForm(
            initial={
                'name': record.misc_info.get('recommender_name'),
                'email': record.misc_info.get('recommender_email'),
                'name_2': record.misc_info.get('recommender_name_2'),
                'email_2': record.misc_info.get('recommender_email_2'),
                'name_3': record.misc_info.get('recommender_name_3'),
                'email_3': record.misc_info.get('recommender_email_3'),
                'teacher_application': record.id
            },
            recommendations_needed=recommendations_needed
        )

    if not rec_upload_form:
        rec_upload_form = StaffRecUploadForm(initial={
            'teacher_application': record.id
        })

    if not ed_bg_form:
        ed_bg = record.user.education_background
        if not ed_bg or isinstance(ed_bg, str):
            ed_bg = {}

        ed_bg_form = EdBgForm(initial={
            'teacher_application': record.id,
            'other_name': record.user.previous_names,
            'credits_earned': ed_bg.get('credits_earned'),
            'masters_level_credits': ed_bg.get('masters_level_credits'),
            'grad_courses': ed_bg.get('grad_courses'),
            'undergrad_program': ed_bg.get('undergrad_program'),
            'certified_states': ed_bg.get('certified_states'),
            'certified_subjects': ed_bg.get('certified_subjects'),
            'highschool_years': ed_bg.get('highschool_years'),
            'college_years': ed_bg.get('college_years'),
            'courses_taught': ed_bg.get('courses_taught'),
        })

        formset_initial = []
        institutions = ed_bg.get('institution', [])
        degrees = ed_bg.get('degree', [])
        majors = ed_bg.get('major', [])
        max_entries = max(len(institutions), len(degrees), len(majors), 5)
        for i in range(max_entries):
            formset_initial.append({
                'institution': institutions[i] if i < len(institutions) else '',
                'degree': degrees[i] if i < len(degrees) else '',
                'major': majors[i] if i < len(majors) else '',
            })
        ed_bg_formset = EducationEntryFormSet(initial=formset_initial)

    if not app_upload_form:
        app_upload_form = AppUploadForm(
            record,
            initial={
                'teacher_application': record.id
            }
        )

    return render(
        request,
        template, {
            'form': form,
            'page_title': "Application",
            'labels': {
                'all_items': 'All Applications'
            },
            'urls': {
                'all_items': 'ce_instructor_app:teacher_applications'
            },
            'menu': draw_menu(cis_menu, 'instructors', 'all_applicants'),
            'record': record,
            'app_profile_form': app_profile_form,
            'recommendations': record.recommendations,
            'recommendations_needed': recommendations_needed,
            'rec_req_form': rec_req_form,
            'rec_upload_form': rec_upload_form,
            'interested_courses': record.selected_courses,
            'course_status_forms': course_status_forms,
            'ed_bg_form': ed_bg_form,
            'ed_bg_formset': ed_bg_formset,
            'uploads': record.uploads,
            'is_modal': True if request.GET.get('modal') else False,
            'notes': TeacherApplicationNote.objects.filter(teacher_application=record).order_by("-createdon"),
            'app_upload_form': app_upload_form,
            'fc_review_status': app_settings.get('fc_review_status_label', 'Ready for Review'),
        })
