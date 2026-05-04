"""
Customizable status label lookups.

Status keys for TeacherApplication, ApplicantSchoolCourse,
ApplicantCourseReviewer, and TeacherApplicant are stable; their display
labels can be overridden via the inst_app_language setting under the
``status_labels`` key.
"""
import json


MODEL_NAMES = (
    'TeacherApplication',
    'ApplicantSchoolCourse',
    'ApplicantCourseReviewer',
    'TeacherApplicant',
)


def _load_overrides():
    from ..settings.inst_app_language import inst_app_language
    raw = inst_app_language.from_db().get('status_labels', '{}')
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or '{}')
    except (TypeError, ValueError):
        return {}


def get_status_label_overrides(model_name):
    overrides = _load_overrides().get(model_name, {})
    return overrides if isinstance(overrides, dict) else {}


def get_status_label(model_name, key, default=None):
    return get_status_label_overrides(model_name).get(key, default if default is not None else key)


def get_status_choices(model_name, default_options):
    overrides = get_status_label_overrides(model_name)
    return [(k, overrides.get(k, label)) for k, label in default_options]


def default_options_for(model_name):
    """Return the canonical STATUS_OPTIONS for a model name."""
    from ..models.teacher_application import TeacherApplication
    from ..models.applicant_school_course import ApplicantSchoolCourse
    from ..models.applicant_course_reviewer import ApplicantCourseReviewer
    from ..models.teacher_applicant_model import TeacherApplicant
    return {
        'TeacherApplication': TeacherApplication.STATUS_OPTIONS,
        'ApplicantSchoolCourse': ApplicantSchoolCourse.STATUS_OPTIONS,
        'ApplicantCourseReviewer': ApplicantCourseReviewer.STATUS_OPTIONS,
        'TeacherApplicant': TeacherApplicant.STATUS_OPTIONS,
    }[model_name]
