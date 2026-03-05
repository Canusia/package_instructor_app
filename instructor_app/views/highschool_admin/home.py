from django.shortcuts import (
    render, get_object_or_404,
    redirect
)
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse

from cis.utils import user_has_instructor_role

from cis.models.customuser import CustomUser
from ...models.teacher_applicant import (
    TeacherApplicant,
    TeacherApplication,
    ApplicantSchoolCourse,
    ApplicantRecommendation,
    ApplicationUpload
)
from cis.models.highschool import HighSchool
from cis.menu import draw_menu, HS_ADMIN_MENU
from cis.forms.student import(
    UserPasswordChangeForm
)

from ...forms.teacher_applicant import (
    TeacherApplicantProfileForm,
    TeacherApplicantEditableForm,
    RecommondationForm,
    AppUploadForm,
    HSAdminAddTeacherForm,
)

from cis.settings.highschool_admin_portal import highschool_admin_portal as portal_language

def index(request):
    user = request.user

    # get hsadmin for user, and then get high schools
    from django.db.models import Q
    from cis.models.highschool_administrator import HSAdministrator
    from cis.models.teacher import TeacherHighSchool
    hs_admin = HSAdministrator.objects.get(user__id=request.user.id)
    highschools = hs_admin.get_highschools()

    add_teacher_form = HSAdminAddTeacherForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_new_teacher':
            add_teacher_form = HSAdminAddTeacherForm(request.POST)
            if add_teacher_form.is_valid():
                applicant = add_teacher_form.save()
                new_app = TeacherApplication.create_new(applicant.user)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f'A new application has been started for {applicant.user.first_name} {applicant.user.last_name}.',
                    'list-group-item-success'
                )
                return redirect(
                    'applicant_app:manage_courses',
                    record_id=new_app.id
                )
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    'Please correct the error(s) below.',
                    'list-group-item-danger'
                )
        else:
            user_id = request.POST.get('user_id')
            app_user = CustomUser.objects.get(id=user_id)
            new_app = TeacherApplication.create_new(app_user)
            messages.add_message(
                request,
                messages.SUCCESS,
                f'A new application has been started for {app_user.first_name} {app_user.last_name}.',
                'list-group-item-success'
            )
            return redirect(
                'applicant_app:manage_courses',
                record_id=new_app.id
            )

    teachers = TeacherHighSchool.objects.filter(highschool__in=highschools).values_list('teacher__user', flat=True)

    teacher_apps = TeacherApplication.objects.filter(
        highschool__in=highschools
    ).values_list('user', flat=True).distinct()

    applications = TeacherApplication.objects.filter(
        Q(user__id__in=teachers) | Q(user__id__in=teacher_apps)
    ).order_by('-createdon')

    teacher_highschools = TeacherHighSchool.objects.filter(
        highschool__in=highschools
    ).select_related('teacher__user', 'highschool')

    # Set session key so address_suggestions view allows access
    request.session['record_key'] = str(request.user.pk)

    return render(
        request,
        'instructor_app/highschool_admin/applications.html',
        {
            'menu': draw_menu(HS_ADMIN_MENU, 'instructor_apps', '', 'highschool_admin'),
            'applications': applications,
            'teacher_highschools': teacher_highschools,
            'add_teacher_form': add_teacher_form,
            'intro': portal_language.from_db().get('instructor_apps_blurb', 'Change me')
        })