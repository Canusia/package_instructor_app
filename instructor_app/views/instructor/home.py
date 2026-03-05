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
from cis.menu import draw_menu, INSTRUCTOR_APP_MENU, INSTRUCTOR_MENU
from cis.forms.student import(
    UserPasswordChangeForm
)

from ...forms.teacher_applicant import (
    TeacherApplicantProfileForm,
    TeacherApplicantEditableForm,
    RecommondationForm,
    AppUploadForm
)

from ...settings.inst_app_language import inst_app_language

def index(request):
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
        'instructor_app/instructor/applications.html',
        {
            'menu': draw_menu(INSTRUCTOR_MENU, 'instructor_apps', '', 'instructor'),
            'applications': applications,
            'intro': inst_app_language.from_db().get('instructor_apps_blurb', 'Change me')
        })