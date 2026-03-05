from django.shortcuts import get_object_or_404, redirect, render
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.utils.safestring import mark_safe

from cis.utils import user_has_instructor_role, user_has_highschool_admin_role
from ..models.teacher_applicant import (
    TeacherApplication,
    ApplicantSchoolCourse,
)
from cis.models.course import Course, CourseAppRequirement
from ..forms.teacher_applicant import SchoolCourseForm
from cis.menu import draw_menu, INSTRUCTOR_APP_MENU, INSTRUCTOR_MENU, HS_ADMIN_MENU
from ..settings.inst_app_language import inst_app_language
from ..utils import get_teacher_application


def manage_course(request, record_id):
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

    form = SchoolCourseForm(
        teacher_application=teacher_application,
        initial={
            'teacher_application': record_id,
            'highschool': teacher_application.highschool.id if teacher_application.highschool else None,
            'id': '-1',
            'course_description': inst_app_language.from_db().get('course_blurb', '')
        }
    )

    if request.method == 'POST':
        form = SchoolCourseForm(teacher_application, request.POST)

        if form.is_valid():
            try:
                teacher_course = form.save(teacher_application)

                # Update application's highschool if not already set
                if teacher_course.highschool and not teacher_application.highschool:
                    teacher_application.highschool = teacher_course.highschool
                    teacher_application.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    'Successfully added course.',
                    'list-group-item-success')

                if request.POST.get('submit').lower().find('continue') != -1:
                    return redirect(
                        'applicant_app:manage_recommendation',
                        record_id=teacher_application.id
                    )
                return redirect(
                    'applicant_app:manage_courses',
                    record_id=record_id
                )
            except IntegrityError as e:
                messages.add_message(
                    request,
                    messages.ERROR,
                    'You have already selected this course. Please select a different course',
                    'list-group-item-danger')
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'Please correct the error(s) and try again.',
                'list-group-item-danger')

    menu = ''
    if user_has_instructor_role(request.user):
        menu = draw_menu(INSTRUCTOR_MENU, 'course_apps', '', 'instructor')
    elif user_has_highschool_admin_role(request.user):
        menu = draw_menu(HS_ADMIN_MENU, 'instructor_apps', '', 'highschool_admin')
    else:
        menu = draw_menu(INSTRUCTOR_APP_MENU, 'manage_app', '', 'applicant')

    api_url = mark_safe(f'/ce/api/applicant_course_list?format=datatables&teacher_application_id={record_id}')

    return render(
        request,
        'instructor_app/manage_course.html',
        {
            'menu': menu,
            'form': form,
            'teacher_application': teacher_application,
            'api_url': api_url,
        }
    )


def remove_course(request, record_id):
    teacher_application = get_teacher_application(request, record_id)
    course_id = request.GET.get('course_id')
    try:
        course = ApplicantSchoolCourse.objects.get(
            pk=course_id,
            teacherapplication=teacher_application,
        )
        course.delete()

        messages.add_message(
            request,
            messages.SUCCESS,
            f'Successfully removed course.',
            'list-group-item-success')
        return redirect('applicant_app:manage_courses',
            record_id=record_id
        )
    except ApplicantSchoolCourse.DoesNotExist:
        messages.add_message(
            request,
            messages.ERROR,
            f'Unable to remove course.',
            'list-group-item-danger')
        return redirect(
            'applicant_app:manage_courses',
            record_id=record_id
        )


def course_details(request, course_id):
    """Return course details as JSON for the course details panel."""
    course = get_object_or_404(Course, pk=course_id)
    app_requirements = CourseAppRequirement.objects.filter(
        course=course, status='Active'
    )
    data = {
        'name': str(course),
        'title': course.title,
        'description': course.description or '',
        'teacher_requirement': course.teacher_requirement or '',
        'prereq': course.prereq or '',
        'app_requirements': [
            {'name': r.name, 'description': r.description, 'required': r.required}
            for r in app_requirements
        ],
    }
    return JsonResponse(data)
