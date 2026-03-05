import logging
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.contrib import messages

from cis.models.course import Cohort
from cis.models.faculty import FacultyCoordinator
from cis.models.note import TeacherApplicationNote
from cis.menu import draw_menu, FACULTY_MENU
from cis.settings.faculty_portal import faculty_portal as portal_lang

from ...forms.teacher_applicant import EdBgForm, ApplicantReviewForm
from ...models.teacher_applicant import (
    TeacherApplication,
    ApplicantSchoolCourse,
    ApplicantCourseReviewer,
    get_fc_review_status,
)
from ...settings.inst_app_language import inst_app_language

logger = logging.getLogger(__name__)


def teacher_applications(request):
    user = request.user
    fc_review_status = get_fc_review_status()
    app_status = (
        (fc_review_status, fc_review_status),
        ('Decision Made', 'Decision Made'),
    )

    my_courses = FacultyCoordinator.courses_overseeing(user)
    my_cohort_ids = my_courses.distinct('course__cohort').values_list(
        'course__cohort__id', flat=True
    )

    return render(
        request,
        'instructor_app/faculty/instructor_applications.html', {
            'page_title': 'Teacher Applications',
            'menu': draw_menu(FACULTY_MENU, 'applications', '', 'faculty'),
            'status': app_status,
            'course_status': ApplicantSchoolCourse.STATUS_OPTIONS,
            'intro': portal_lang(request).from_db().get('applications_blurb', 'Change me'),
            'cohorts': Cohort.objects.filter(
                pk__in=my_cohort_ids
            ).order_by('designator'),
            'api_url': '/ce/api/teacher_application?format=datatables'
        }
    )


def review_application(request, record_id):
    teacher_application = get_object_or_404(TeacherApplication, pk=record_id)
    user = request.user

    review_form = ApplicantReviewForm()

    if request.method == 'POST':
        review_form = ApplicantReviewForm(request.POST)

        if review_form.is_valid():
            course_review_id = review_form.cleaned_data['application_course_id']
            course_review = ApplicantCourseReviewer.objects.get(
                id=course_review_id
            )

            course_review.status = review_form.cleaned_data['decision']
            if not course_review.misc_info:
                course_review.misc_info = {}

            course_review.misc_info['reviewer_note'] = review_form.cleaned_data['comment'] + '<br>-----------<br>' + course_review.misc_info.get('reviewer_note', '')
            course_review.misc_info['reviewed_on'] = datetime.now().strftime('%m/%d/%Y')
            course_review.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                'Your review has been successfully submitted.',
                'list-group-item-success')
        else:
            logger.warning('Review form validation failed: %s', review_form.errors)

    menu = draw_menu(FACULTY_MENU, 'manage_app', 'faculty')
    courses = ApplicantCourseReviewer.objects.filter(
        reviewer=user,
        application_course__teacherapplication=teacher_application
    )

    ed_bg = teacher_application.user.education_background
    if not ed_bg or isinstance(ed_bg, str):
        ed_bg = {}

    initial = {
        'teacher_application': teacher_application.id,
        'other_name': teacher_application.user.previous_names,
        'transcripts': ed_bg.get('transcript_status'),
        'credits_earned': ed_bg.get('credits_earned'),
        'masters_level_credits': ed_bg.get('masters_level_credits'),
        'grad_courses': ed_bg.get('grad_courses'),
        'undergrad_program': ed_bg.get('undergrad_program'),
        'certified_states': ed_bg.get('certified_states'),
        'certified_subjects': ed_bg.get('certified_subjects'),
        'highschool_years': ed_bg.get('highschool_years'),
        'college_years': ed_bg.get('college_years'),
        'courses_taught': ed_bg.get('courses_taught'),
    }
    form = EdBgForm(initial=initial)

    return render(
        request,
        'instructor_app/faculty/review_application.html',
        {
            'menu': menu,
            'intro': portal_lang(request).from_db().get('manage_app_blurb', 'Change me'),
            'teacher_application': teacher_application,
            'record': teacher_application,
            'notes': TeacherApplicationNote.objects.filter(
                teacher_application=teacher_application,
                meta__type__iexact='public'
            ),
            'courses': courses,
            'review_form': review_form,
            'recommendations_needed': int(inst_app_language.from_db().get('recommendations_needed', '2')),
            'recommendations': teacher_application.recommendations,
            'ed_bg': teacher_application.user.education_background,
            'ed_bg_form': form,
            'uploads': teacher_application.uploads()
        }
    )
