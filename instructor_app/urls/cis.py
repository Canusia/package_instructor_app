from django.urls import path, include
from django.contrib.auth.decorators import user_passes_test
from rest_framework import routers

from cis.utils import user_has_cis_role

from ..views.ce.course_requirements import (
    CourseAppRequirementViewSet,
    do_bulk_action as course_req_bulk_actions,
)
from ..views.ce.course_administrators import (
    CourseAdministratorViewSet,
    manage_course_administrator_role,
    delete_course_administrator_role,
)

from ..views.ce.teacher_application import (
    index as teacher_applications,
    detail as teacher_application,
    TeacherApplicantViewSet,
    TeacherApplicationViewSet,
    TeacherApplicationReviewerViewSet,
    ApplicantCourseListViewSet,
    remove_upload as tapp_remove_file,
    view_approval_email,
    send_approval_email,
    remove_recommendation as tapp_remove_recommendation,
    delete_record as delete_teacher_application,
    reply_to_note as teacher_app_note_reply,
    remind_reviewer as remind_reviewer,
    update_reviewer_status as update_reviewer_status,
    delete_course as delete_teacher_course,
    download_files as download_tapp_files,
    download_as_pdf as download_tapp,
    do_action as do_teacher_app_action,
    do_bulk_action as teacher_app_bulk_actions,
    send_approval_email
)

app_name = 'ce_instructor_app'

router = routers.DefaultRouter()
router_viewsets = {
    'teacher_applicant': TeacherApplicantViewSet,
    'teacher_application': TeacherApplicationViewSet,
    'teacher_application_reviewers': TeacherApplicationReviewerViewSet,
    'applicant_course_list': ApplicantCourseListViewSet,
    'course-requirements': CourseAppRequirementViewSet,
    'course_administrator': CourseAdministratorViewSet,
}

for router_key in router_viewsets.keys():
    router.register(
        router_key,
        router_viewsets[router_key],
        basename=router_key
    )

urlpatterns = [
    path('api/', include(router.urls)),

    path(
        'teacher_applications/',
        user_passes_test(user_has_cis_role, login_url='/')(teacher_applications),
        name='teacher_applications'),
    path(
        'teacher_applications/bulk_actions',
        user_passes_test(user_has_cis_role, login_url='/')(teacher_app_bulk_actions),
        name='teacher_app_bulk_actions'),
    path(
        'teacher_application/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(teacher_application),
        name='teacher_application'),
    path(
        'teacher_application/remove_file/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(tapp_remove_file),
        name='tapp_remove_file'),
    path(
        'teacher_application/delete/course/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(delete_teacher_course),
        name='delete_teacher_course'),
    path(
        'teacher_application/download_files/<uuid:record_id>',
        download_tapp_files,
        name='download_tapp_files'
    ),
    path(
        'teacher_application/download/<uuid:record_id>',
        download_tapp,
        name='download_tapp'
    ),
    path(
        'teacher_application/send_approval_email/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(send_approval_email),
        name='send_approval_email'
    ),
    path(
        'teacher_application/remind_reviewer',
        remind_reviewer,
        name='remind_reviewer'
    ),
    path(
        'teacher_application/update_reviewer_status',
        update_reviewer_status,
        name='update_reviewer_status'
    ),
    path(
        'teacher_application/<uuid:record_id>/action',
        do_teacher_app_action,
        name='teacher_app_action'
    ),
    path(
        'teacher_application/remove_recommendation/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(tapp_remove_recommendation),
        name='tapp_remove_recommendation'),
    path(
        'teacher_application/delete/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(delete_teacher_application),
        name='delete_teacher_application'),
    path(
        'teacher_application/note/reply/<uuid:note_id>',
        teacher_app_note_reply,
        name='teacher_app_note_reply'
    ),
    path(
        'teacher_application/view_approval_email/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(view_approval_email),
        name='view_approval_email'
    ),
    path(
        'teacher_application/send_approval_email/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(send_approval_email),
        name='send_approval_email'
    ),

    # Course requirements
    path(
        'courses/req_bulk_actions',
        user_passes_test(user_has_cis_role, login_url='/')(course_req_bulk_actions),
        name='course_req_bulk_actions'
    ),

    # Course administrators
    path(
        'course/administrator/delete/<uuid:record_id>',
        user_passes_test(user_has_cis_role, login_url='/')(delete_course_administrator_role),
        name='delete_course_administrator_role'
    ),
]
