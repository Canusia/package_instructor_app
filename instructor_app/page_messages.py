"""instructor_app (applicant portal) page-message providers."""
from cis.page_messages import page_message, PageMessage


def _has_no_application(user):
    # Relative import: this module ships flat in production
    # (site-packages/instructor_app/) and nested in the editable-submodule dev
    # layout (instructor_app/instructor_app/). An absolute path pins one layout
    # and ModuleNotFoundErrors on the other.
    from .models.teacher_application import TeacherApplication
    return not TeacherApplication.objects.filter(user__id=user.id).exists()


@page_message('applicant', 'dashboard')
def start_application_prompt(request):
    if _has_no_application(request.user):
        return PageMessage(
            text='You have no applications yet. Start one below to begin.',
            level='info')
    return None
