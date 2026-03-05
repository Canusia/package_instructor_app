from django.template.loader import get_template


def application_as_pdf(application):
    """
    Render a TeacherApplication as a PDF document.

    Returns the PDF bytes.
    """
    import pdfkit
    from instructor_app.forms.teacher_applicant import (
        TeacherApplicantProfileForm, EditTeacherApplicationForm, EdBgForm
    )
    from cis.models.note import TeacherApplicationNote

    record = application

    base_template = 'instructor_app/ce/details_single.html'
    template = get_template(base_template)

    app_profile_form = TeacherApplicantProfileForm(
        user=record.user
    )

    ed_bg = record.user.education_background
    if not ed_bg:
        ed_bg = {}

    ed_bg = record.user.education_background
    if not ed_bg or isinstance(ed_bg, str):
        ed_bg = {}

    ed_bg_form = EdBgForm(initial={
        'teacher_application': record.id,
        'other_name': record.user.previous_names,
        'credits_earned': ed_bg.get('credits_earned'),
        'masters_level_credits': ed_bg.get('masters_level_credits'),
        'grad_courses': ed_bg.get('grad_courses'),
        'undergrad_program': ed_bg.get('undergrad_program'),
        'certified_states': ed_bg.get('certified_states'),
        'certified_subjects': ed_bg.get('certified_subjects'),
        'highschool_years': ed_bg.get('highschool_years'),
        'college_years': ed_bg.get('college_years'),
        'courses_taught': ed_bg.get('courses_taught'),
    })

    form = EditTeacherApplicationForm(initial={
        'status': record.status,
        'assigned_to': record.assigned_to,
        'invite_to_interview': record.misc_info.get('invite_to_interview'),
        'interviewed_on': record.misc_info.get('interviewed_on'),
        'decision_letter_sent_on': record.misc_info.get('decision_letter_sent_on'),
        'action': 'edit_application',
        'participating_acad_year': record.misc_info.get('participating_acad_year'),
        'grad_credit': record.misc_info.get('grad_credit'),
        'checklist': record.misc_info.get('checklist'),
        'psid': record.user.psid
    })

    html = template.render({
        'form': form,
        'page_title': "Application",
        'record': record,
        'app_profile_form': app_profile_form,
        'recommendations': record.recommendations,
        'interested_courses': record.selected_courses,
        'ed_bg': record.user.education_background,
        'ed_bg_form': ed_bg_form,
        'uploads': record.uploads,
        'notes': TeacherApplicationNote.objects.filter(
            teacher_application=record
        ).order_by("-createdon")
    })

    options = {
        'page-size': 'Letter'
    }

    template = get_template('cis/print_base.html')
    html = template.render({'main_content': html})

    pdf = pdfkit.from_string(html, False, options)

    return pdf
