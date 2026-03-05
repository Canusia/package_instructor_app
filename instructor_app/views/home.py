from django.shortcuts import (
    render, get_object_or_404,
    redirect
)
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse

from cis.utils import user_has_instructor_role, user_has_highschool_admin_role

from cis.models.customuser import CustomUser
from ..models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
    ApplicantSchoolCourse,
    ApplicantRecommendation,
    ApplicationUpload
)
from cis.models.highschool import HighSchool
from cis.menu import draw_menu, INSTRUCTOR_APP_MENU, INSTRUCTOR_MENU, HS_ADMIN_MENU
from cis.forms.student import(
    UserPasswordChangeForm
)

from ..forms.teacher_applicant import (
    TeacherApplicantProfileForm,
    TeacherApplicantEditableForm,
    RecommondationForm,
    AppUploadForm
)

from ..settings.inst_app_language import inst_app_language
from ..utils import get_teacher_application

def manage_password(request):

    user = CustomUser.objects.get(id=request.user.id)
    form = UserPasswordChangeForm()

    if request.method == 'POST' and request.POST.get('update_password') == 'Update Password':
        form = UserPasswordChangeForm(user, request.POST)

        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                'Successfully updated password. Please login again.',
                'list-group-item-success') 
            return redirect('applicant_app:manage_password')

    return render(
        request,
        'instructor_app/manage_password.html',
        {
            'form': form,
            'intro': inst_app_language.from_db().get('manage_password_blurb', 'Change me'),
            'menu': draw_menu(INSTRUCTOR_APP_MENU, 'manage_password', '', 'applicant')
        })

def profile(request):

    user = CustomUser.objects.get(id=request.user.id)
    applicant = TeacherApplicant.objects.get(user=user)
    form = TeacherApplicantEditableForm(applicant=applicant)

    if request.method == 'POST' and request.POST.get('update_profile') == 'Update Profile':
        form = TeacherApplicantEditableForm(applicant=applicant, data=request.POST)
        if form.is_valid():
            form.save(applicant)

            messages.add_message(
                request,
                messages.SUCCESS,
                'Successfully updated profile.',
                'list-group-item-success') 
            return redirect('applicant_app:profile')

    return render(
        request,
        'instructor_app/profile.html',
        {
            'form': form,
            'intro': inst_app_language.from_db().get('profile_blurb', 'Change me'),
            'menu': draw_menu(INSTRUCTOR_APP_MENU, 'profile', '', 'applicant')
        })

def submit_recommendation(request, record_id):
    teacher_application = get_object_or_404(TeacherApplication, pk=record_id)
    teacher_courses = ApplicantSchoolCourse.objects.filter(
        teacherapplication=teacher_application
    )

    recommender_emails = []
    recommender_emails.append(teacher_application.misc_info.get('recommender_email'))
    recommender_emails.append(teacher_application.misc_info.get('recommender_email_2'))
    recommender_emails.append(teacher_application.misc_info.get('recommender_email_3'))

    user_email = request.GET.get('email')
    error_message = None
    if user_email not in (recommender_emails):
        error_message = '<p class="alert alert-danger">The email address is not associated with a recommender for this application. Please contact the applicant and have them resend you the recommendation link.</p>'

    form = RecommondationForm(initial={
        'teacher_application':teacher_application.id,
        'email': request.GET.get('email', '')
    })

    if request.method == 'POST':
        # this block is repeated in cis/views/teacher_pplication.py details       
        recommendation = ApplicantRecommendation(
            teacher_application=teacher_application
        )

        form = RecommondationForm(request.POST, request.FILES, instance=recommendation)

        if form.is_valid():
            recommendation = form.save(commit=False)
            recommendation.recommendation = {}
            recommendation.recommendation['number_years'] = form.cleaned_data['years']

            recommendation.submitter = {}
            recommendation.submitter['name'] = form.cleaned_data['name']
            recommendation.submitter['position'] = form.cleaned_data['position']
            recommendation.submitter['email'] = form.cleaned_data.get('email')

            recommendation.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                f'Thank you for submitting the recommendation',
                'list-group-item-success')
            return redirect('index')
        else:
            messages.add_message(
                request,
                messages.ERROR,
                f'Please correct the error(s) and try again.',
                'list-group-item-danger')

    app_settings = inst_app_language.from_db()
    accepting_applications = app_settings.get('is_accepting_new', 'No') == 'Yes'
    closed_message = '' if accepting_applications else app_settings.get('closed_message', '-')

    return render(
        request,
        'instructor_app/submit_recommendation.html',
        {
            'error': error_message,
            'teacher_application': teacher_application,
            'interested_courses': teacher_courses,
            'page_intro': app_settings.get('rec_submit_page_header', ''),
            'pre_form': app_settings.get('rec_submit_page_pre_form', ''),
            'form': form,
            'accepting_applications': accepting_applications,
            'closed_message': closed_message
        }
    )
submit_recommendation.login_required = False

def review_application(request, record_id):
    teacher_application = get_teacher_application(request, record_id)

    if request.method == 'POST':
        teacher_application.status = 'Submitted'
        teacher_application.save()

        messages.add_message(
            request,
            messages.SUCCESS,
            f'Your application has been successfully submitted.',
            'list-group-item-success')
        return redirect(
            'applicant_app:review_application',
            record_id=teacher_application.id
        )

    menu = ''
    if user_has_instructor_role(request.user):
        menu = draw_menu(INSTRUCTOR_MENU, 'course_apps', '', 'instructor')
    elif user_has_highschool_admin_role(request.user):
        menu = draw_menu(HS_ADMIN_MENU, 'instructor_apps', '', 'highschool_admin')
    else:
        menu = draw_menu(INSTRUCTOR_APP_MENU, 'manage_app', '', 'applicant')

    app_settings = inst_app_language.from_db()
    accepting_applications = app_settings.get('is_accepting_new', 'No') == 'Yes'
    closed_message = '' if accepting_applications else app_settings.get('closed_message', '-')

    return render(
        request,
        'instructor_app/review_application.html',
        {
            'menu': menu,
            'page_intro': app_settings.get('submit_page_header', 'Change in Settings'),
            'teacher_application': teacher_application,
            'recommendations': teacher_application.recommendations,
            'ed_bg': teacher_application.user.education_background,
            'uploads': teacher_application.uploads(),
            'accepting_applications': accepting_applications,
            'closed_message': closed_message,
            'certification_text': app_settings.get('certification_text', ''),
            'app_not_editable_message': app_settings.get('app_not_editable_message', '') if not teacher_application.can_edit() else '',
        }
    )

def manage_uploads(request, record_id):
    teacher_application = get_teacher_application(request, record_id)
    if not teacher_application.can_edit():
        messages.add_message(
            request,
            messages.SUCCESS,
            'This application is not editable.',
            'list-group-item-danger'
        )
        return redirect(
            'applicant_app:review_application',
            record_id=teacher_application.id
        )

    form = AppUploadForm(
        teacher_application,
        initial={
        'teacher_application':teacher_application.id
    })

    uploads = ApplicationUpload.objects.filter(
        teacher_application=teacher_application
    )

    if request.method == 'POST':
        form = AppUploadForm(
            teacher_application,
            request.POST,
            request.FILES
        )

        if form.is_valid():
            if request.FILES.get('upload'):
                upload = form.save(commit=False)
                upload.teacher_application = teacher_application
                upload.save()

            if request.POST.get('submit').lower().find('continue') != -1:
                return redirect(
                    'applicant_app:review_application',
                    record_id=teacher_application.id
                )
            return redirect(
                'applicant_app:manage_uploads',
                record_id=record_id
            )
        else:
            messages.add_message(
                request,
                messages.ERROR,
                f'Please correct the error(s) and try again.',
                'list-group-item-danger')

    menu = ''
    if user_has_instructor_role(request.user):
        menu = draw_menu(INSTRUCTOR_MENU, 'course_apps', '', 'instructor')
    else:
        menu = draw_menu(INSTRUCTOR_APP_MENU, 'manage_app', '', 'applicant')

    return render(
        request,
        'instructor_app/manage_uploads.html',
        {
            'menu': menu,
            'page_intro': inst_app_language.from_db().get('file_upload_page_header'),
            'teacher_application': teacher_application,
            'uploads': uploads,
            'form': form
        }
    )

def dashboard(request):
    user = request.user

    if request.method == 'POST':
        new_app = TeacherApplication.create_new(user)
        messages.add_message(
            request,
            messages.SUCCESS,
            f'Your new application has been started. Please continue below',
            'list-group-item-success'
        )
        return redirect(
            'applicant_app:manage_courses',
            record_id=new_app.id
        )

    applications = TeacherApplication.objects.filter(
        user__id=user.id
    ).order_by('-createdon')

    return render(
        request,
        'instructor_app/dashboard.html',
        {
            'menu': draw_menu(INSTRUCTOR_APP_MENU, 'home', '', 'applicant'),
            'applications': applications,
            'intro': inst_app_language.from_db().get('dashboard_blurb', 'Change me')
        })

def get_school_info(request):
    highschool_id = request.GET.get('highschool_id')

    highschool = HighSchool.objects.get(
        pk=highschool_id
    )
    result = {
        'name': highschool.name,
        'district': highschool.district.name,
        'address1': highschool.address1,
        'address2': highschool.address2,
        'city': highschool.city,
        'state': highschool.state,
        'zipcode': highschool.postal_code
    }

    return JsonResponse(result)

def remove_upload(request, record_id):
    teacher_application = get_teacher_application(request, record_id)
    upload_id = request.GET.get('upload_id')
    try:
        upload = ApplicationUpload.objects.get(
            pk=upload_id,
            teacher_application=teacher_application,
        )
        upload.delete()

        messages.add_message(
            request,
            messages.SUCCESS,
            f'Successfully removed file.',
            'list-group-item-success')
        return redirect('applicant_app:manage_uploads',
            record_id=record_id
        )
    except ApplicationUpload.DoesNotExist:
        messages.add_message(
            request,
            messages.ERROR,
            f'Unable to remove file.',
            'list-group-item-danger')
        return redirect(
            'applicant_app:manage_uploads',
            record_id=record_id
        )


