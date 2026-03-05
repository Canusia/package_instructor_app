from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from cis.utils import user_has_instructor_role, user_has_highschool_admin_role
from ..models.teacher_applicant import (
    TeacherApplication,
    ApplicantRecommendation,
)
from ..forms.teacher_applicant import RecommendationRequestForm
from cis.menu import draw_menu, INSTRUCTOR_APP_MENU, INSTRUCTOR_MENU, HS_ADMIN_MENU
from ..settings.inst_app_language import inst_app_language
from ..utils import get_teacher_application


def manage_recommendation(request, record_id):
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

    app_settings = inst_app_language.from_db()
    recommendations_needed = int(app_settings.get('recommendations_needed', '2'))

    # If no recommendations needed, skip to next step
    if recommendations_needed == 0:
        return redirect(
            'applicant_app:manage_ed_bg',
            record_id=record_id
        )

    initial = {
        'teacher_application': teacher_application.id
    }
    if teacher_application.misc_info:
        initial['name'] = teacher_application.misc_info.get('recommender_name')
        initial['email'] = teacher_application.misc_info.get('recommender_email')

        initial['name_2'] = teacher_application.misc_info.get('recommender_name_2')
        initial['email_2'] = teacher_application.misc_info.get('recommender_email_2')

        initial['name_3'] = teacher_application.misc_info.get('recommender_name_3')
        initial['email_3'] = teacher_application.misc_info.get('recommender_email_3')

    form = RecommendationRequestForm(
        initial=initial,
        recommendations_needed=recommendations_needed
    )
    try:
        recommendations = ApplicantRecommendation.objects.filter(
            teacher_application=teacher_application
        )
    except ApplicantRecommendation.DoesNotExist:
        recommendations = None

    if request.method == 'POST':
        form = RecommendationRequestForm(
            request.POST,
            recommendations_needed=recommendations_needed
        )

        if form.is_valid():
            form.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                'Successfully sent recommendation request.',
                'list-group-item-success')
            return redirect(
                'applicant_app:manage_ed_bg',
                record_id=record_id
            )
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'Please correct the error(s) and try again.',
                'list-group-item-danger'
            )

    menu = ''
    if user_has_instructor_role(request.user):
        menu = draw_menu(INSTRUCTOR_MENU, 'course_apps', '', 'instructor')
    elif user_has_highschool_admin_role(request.user):
        menu = draw_menu(HS_ADMIN_MENU, 'instructor_apps', '', 'highschool_admin')
    else:
        menu = draw_menu(INSTRUCTOR_APP_MENU, 'manage_app', '', 'applicant')

    return render(
        request,
        'instructor_app/request_recommendation.html',
        {
            'menu': menu,
            'page_intro': app_settings.get('rec_req_blurb', ''),
            'page_footer': app_settings.get('rec_req_blurb_bottom', ''),
            'teacher_application': teacher_application,
            'recommendations': recommendations,
            'form': form
        }
    )
