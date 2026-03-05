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

from ..views.instructor.home import index

app_name = 'instructor_app'
urlpatterns = [
    path('',
        user_passes_test(user_has_applicant_role, login_url='/')(index),
        name='instructor_apps')
]
