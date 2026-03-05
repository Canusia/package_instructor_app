"""
    URL Configuration
"""
from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from instructor_app.utils import user_has_applicant_role

from ..views.onboarding import (
    start_app,
    awaiting_verification,
    verify_email,
    complete_signup,
)

from ..views.home import (
    dashboard,
    submit_recommendation,
    manage_uploads,
    get_school_info,
    remove_upload,
    review_application,
    profile, manage_password,
)

from ..views.manage_ed_bg import manage_ed_background
from ..views.manage_recommendation import manage_recommendation

from ..views.manage_courses import (
    manage_course,
    remove_course,
    course_details,
)

app_name = 'applicant_app'
urlpatterns = [
    # Onboarding routes (public, no auth required)
    path(
        'start_request/',
        start_app,
        name='start_app'),
    path(
        'awaiting_verification/',
        awaiting_verification,
        name='awaiting_verification'),
    path(
        'verify_email/<uuid:verification_id>/',
        verify_email,
        name='verify_email'),
    path(
        'complete_signup/<uuid:applicant_id>/',
        complete_signup,
        name='complete_signup'),
    path(
        'remove_upload/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(remove_upload),
        name='remove_upload'),
    path(
        'remove_course/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(remove_course),
        name='remove_course'),  
    path(
        'highschool',
        user_passes_test(user_has_applicant_role, login_url='/')(get_school_info),
        name='highschool_info'),
    path(
        'review_application/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(review_application),
        name='review_application'),
    path(
        'manage_uploads/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(manage_uploads),
        name='manage_uploads'),
    path(
        'manage_courses/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(manage_course),
        name='manage_courses'),
    path(
        'course_details/<uuid:course_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(course_details),
        name='course_details'),
    path(
        'manage_recommendation/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(manage_recommendation),
        name='manage_recommendation'),
    path(
        'manage_ed_bg/<uuid:record_id>',
        user_passes_test(user_has_applicant_role, login_url='/')(manage_ed_background),
        name='manage_ed_bg'),
    path(
        'recommendation/<uuid:record_id>',
        submit_recommendation,
        name='instructor_recommendation'),        
    path(
        'profile/',
        user_passes_test(user_has_applicant_role, login_url='/')(profile),
        name='profile'),
    path(
        'manage_password/',
        user_passes_test(user_has_applicant_role, login_url='/')(manage_password),
        name='manage_password'),
    path(
        'dashboard/',
        user_passes_test(user_has_applicant_role, login_url='/')(dashboard),
        name='dashboard'),
]
