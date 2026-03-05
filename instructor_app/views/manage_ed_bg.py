from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from cis.utils import user_has_instructor_role, user_has_highschool_admin_role
from ..models.teacher_applicant import TeacherApplication
from ..forms.teacher_applicant import EdBgForm, EducationEntryFormSet
from cis.menu import draw_menu, INSTRUCTOR_APP_MENU, INSTRUCTOR_MENU, HS_ADMIN_MENU
from ..settings.inst_app_language import inst_app_language
from ..utils import get_teacher_application


def manage_ed_background(request, record_id):
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

    ed_bg = teacher_application.user.education_background
    if not ed_bg or isinstance(ed_bg, str):
        ed_bg = {}

    # Build initial data for the formset from existing education entries
    formset_initial = []
    institutions = ed_bg.get('institution', [])
    degrees = ed_bg.get('degree', [])
    majors = ed_bg.get('major', [])
    max_entries = max(len(institutions), len(degrees), len(majors), 5)
    for i in range(max_entries):
        formset_initial.append({
            'institution': institutions[i] if i < len(institutions) else '',
            'degree': degrees[i] if i < len(degrees) else '',
            'major': majors[i] if i < len(majors) else '',
        })

    initial = {
        'teacher_application': teacher_application.id,
        'other_name': teacher_application.user.previous_names,
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
    formset = EducationEntryFormSet(initial=formset_initial)

    if request.method == 'POST':
        form = EdBgForm(request.POST)
        formset = EducationEntryFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            form.save(teacher_application, formset=formset)

            return redirect(
                'applicant_app:manage_uploads',
                record_id=record_id
            )
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

    return render(
        request,
        'instructor_app/manage_ed_bg.html',
        {
            'menu': menu,
            'page_intro': inst_app_language.from_db().get('ed_bg_page_header', 'Change in Settings'),
            'teacher_application': teacher_application,
            'form': form,
            'formset': formset,
        }
    )
