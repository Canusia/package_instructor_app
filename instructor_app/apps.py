import os
from django.apps import AppConfig


class InstructorAppConfig(AppConfig):
    """Production config - pip installed."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instructor_app'
    path = os.path.dirname(os.path.abspath(__file__))

    REPORTS = [
        {
            'app': 'instructor_app',
            'name': 'teacher_applications',
            'title': 'Instructor Applications Export',
            'description': 'Export instructor applications filtered by status and created on date.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app',
            'name': 'course_reviewers',
            'title': 'Course Reviewers Export',
            'description': 'Export course reviewer assignments filtered by review status, application status, course, and assigned date.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app',
            'name': 'pending_notifications',
            'title': 'Pending Incomplete-Application Notifications',
            'description': 'Export applicants who would receive an incomplete-application reminder if the cron job ran now.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app',
            'name': 'pending_review_notifications',
            'title': 'Pending Review Notifications',
            'description': 'Export faculty reviewers with outstanding course application reviews.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
    ]

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

    REPORTS = [
        {
            'app': 'instructor_app.instructor_app',
            'name': 'teacher_applications',
            'title': 'Instructor Applications Export',
            'description': 'Export instructor applications filtered by status and created on date.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app.instructor_app',
            'name': 'course_reviewers',
            'title': 'Course Reviewers Export',
            'description': 'Export course reviewer assignments filtered by review status, application status, course, and assigned date.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app.instructor_app',
            'name': 'pending_notifications',
            'title': 'Pending Incomplete-Application Notifications',
            'description': 'Export applicants who would receive an incomplete-application reminder if the cron job ran now.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
        {
            'app': 'instructor_app.instructor_app',
            'name': 'pending_review_notifications',
            'title': 'Pending Review Notifications',
            'description': 'Export faculty reviewers with outstanding course application reviews.',
            'categories': ['Instructors'],
            'available_for': ['ce'],
        },
    ]

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
