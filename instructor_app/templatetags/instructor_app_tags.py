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
