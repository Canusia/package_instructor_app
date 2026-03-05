from django.shortcuts import get_object_or_404

from cis.utils import user_has_instructor_role, user_has_highschool_admin_role, user_has_cis_role
from instructor_app.models.teacher_applicant import TeacherApplication


def user_has_applicant_role(user):
    """
    Returns True if user has applicant, instructor, highschool_admin, or ce role.
    """
    if user_has_cis_role(user):
        return True

    if user.is_anonymous:
        return False

    roles = user.get_roles()
    return True if 'applicant' in roles or 'instructor' in roles or 'highschool_admin' in roles else False


def get_teacher_application(request, record_id):
    """
    Get a TeacherApplication by ID with role-based access control.

    Instructors and HS admins can access any application.
    Applicants can only access their own.
    """
    if user_has_instructor_role(request.user) or user_has_highschool_admin_role(request.user):
        return get_object_or_404(TeacherApplication, pk=record_id)
    return get_object_or_404(TeacherApplication, pk=record_id, user=request.user)
