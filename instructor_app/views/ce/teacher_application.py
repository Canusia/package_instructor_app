# Backward-compatible re-export shim.
# All views have been split into separate modules:
#   viewsets.py, detail.py, actions.py, bulk_actions.py
from .viewsets import (
    TeacherApplicantViewSet,
    TeacherApplicationViewSet,
    TeacherApplicationReviewerViewSet,
    ApplicantCourseListViewSet,
)
from .detail import detail
from .actions import (
    send_approval_email,
    view_approval_email,
    download_as_pdf,
    download_files,
    delete_course,
    remind_reviewer,
    update_reviewer_status,
    do_action,
    add_new_course_reviewer,
    reply_to_note,
    remove_recommendation,
    remove_upload,
    delete_record,
)
from .bulk_actions import do_bulk_action

from django.shortcuts import render
from cis.menu import cis_menu, draw_menu
from cis.models.course import Course
from cis.models.term import AcademicYear
from ...models.teacher_applicant import (
    TeacherApplication,
    ApplicantCourseReviewer,
    ApplicantSchoolCourse,
)
from ...settings.inst_app_language import inst_app_language


def index(request):
    '''
     search and index page for staff
    '''
    menu = draw_menu(cis_menu, 'instructors', 'all_applicants')
    template = 'instructor_app/ce/index.html'

    return render(
        request,
        template, {
            'page_title': 'Instructor Applications',
            'urls': {
            },
            'menu': menu,
            'status': TeacherApplication.STATUS_OPTIONS,
            'course_status': ApplicantSchoolCourse.STATUS_OPTIONS,
            'course_review_status': ApplicantCourseReviewer.STATUS_OPTIONS,
            'academic_years': AcademicYear.objects.all().order_by('-name'),
            'courses': Course.objects.all().order_by('cohort__designator'),
            'api_url': '/ce/api/teacher_application?format=datatables',
            'reviewer_api_url': '/ce/api/teacher_application_reviewers?format=datatables',
            'applicant_api_url': '/ce/api/teacher_applicant?format=datatables',
            'fc_review_status': inst_app_language.from_db().get('fc_review_status_label', 'Ready for Review'),
        }
    )
