from django import template

register = template.Library()

STEP_MAP = {
    'Select Course(s)': 1,
    'Manage Recommendation': 2,
    'Manage Ed. Background': 3,
    'Upload Materials': 4,
    'Review & Submit': 5,
}


@register.simple_tag
def active_step_number(active_step):
    """Return the numeric step index (1-5) for the given active_step string."""
    return STEP_MAP.get(active_step, 0)


@register.simple_tag
def recommendations_required():
    """Return True if recommendations_needed > 0 in inst_app_language settings."""
    from ..settings.inst_app_language import inst_app_language
    return int(inst_app_language.from_db().get('recommendations_needed') or 0) > 0
