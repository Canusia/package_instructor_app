import os
from django.apps import AppConfig


class InstructorAppConfig(AppConfig):
    """Production config - pip installed."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instructor_app'
    path = os.path.dirname(os.path.abspath(__file__))

    CONFIGURATORS = [
        {
            'app': 'instructor_app',
            'name': 'incomplete_si_application',
            'title': 'Incomplete SI Application Email(s)',
            'description': '-',
            'categories': ['5']
        },
        {
            'app': 'instructor_app',
            'name': 'teacher_application_email',
            'title': 'Instructor Application Email(s)',
            'description': '-',
            'categories': ['5']
        },
        {
            'app': 'instructor_app',
            'name': 'inst_app_language',
            'title': 'Instructor Application Page',
            'description': '-',
            'categories': ['5']
        },
    ]

    def ready(self):
        import instructor_app.signals.teacher_applications  # noqa: F401


class DevInstructorAppConfig(AppConfig):
    """Development config - submodule."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instructor_app.instructor_app'
    verbose_name = 'Dev - Instructor App'

    CONFIGURATORS = [
        {
            'app': 'instructor_app.instructor_app',
            'name': 'incomplete_si_application',
            'title': 'Incomplete SI Application Email(s)',
            'description': '-',
            'categories': ['5']
        },
        {
            'app': 'instructor_app.instructor_app',
            'name': 'teacher_application_email',
            'title': 'Instructor Application Email(s)',
            'description': '-',
            'categories': ['5']
        },
        {
            'app': 'instructor_app.instructor_app',
            'name': 'inst_app_language',
            'title': 'Instructor Application Page',
            'description': '-',
            'categories': ['5']
        },
    ]

    def ready(self):
        import instructor_app.instructor_app.signals.teacher_applications  # noqa: F401
