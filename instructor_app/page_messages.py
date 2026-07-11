"""instructor_app (applicant portal) page-message providers."""
from cis.page_messages import page_message, PageMessage


def _has_no_application(user):
    from instructor_app.instructor_app.models.teacher_applicant import TeacherApplication
    return not TeacherApplication.objects.filter(user__id=user.id).exists()


@page_message('applicant', 'dashboard')
def start_application_prompt(request):
    if _has_no_application(request.user):
        return PageMessage(
            text='You have no applications yet. Start one below to begin.',
            level='info')
    return None
