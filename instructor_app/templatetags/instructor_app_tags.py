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


@register.filter
def br_to_newline(value):
    """Convert literal <br>/<br/>/<br /> substrings to newlines.

    Useful for legacy data that stored line breaks as HTML; chain with
    |linebreaksbr to render line breaks while still escaping the rest.
    """
    if not value:
        return value
    import re
    return re.sub(r'<br\s*/?>', '\n', str(value), flags=re.IGNORECASE)


@register.simple_tag
def status_label(model_name, key, default=None):
    """Look up the customised display label for a status key."""
    from ..services.status_labels import get_status_label
    return get_status_label(model_name, key, default)


COURSE_ADMINISTRATORS_API = '/ce/api/course_administrator?format=datatables'
COURSE_ADMINISTRATORS_VARIANT = 'faculty_coords_by_course'


@register.simple_tag(takes_context=True)
def course_administrators_table(context):
    """Config for the /ce/courses/ "By Course Administrator" table (#2), or
    None when the tenant cannot supply it.

    Built from the tenant's shared ``faculty_coords_table`` service (the one
    cis's faculty pages use), so all three CourseAdministrator tables come from
    one config. A tenant whose ``myce_tenant_configs`` predates the
    ``faculty_coords_by_course`` variant -- or has no TABLE_CONFIGS_APP at all
    -- gets None, and the template falls back to its own markup.
    """
    from ..services.table_configs import available, get_table_config

    if not available('faculty_coords_table'):
        return None
    urls = context.get('urls') or {}
    details_prefix = (urls.get('details_prefix') if hasattr(urls, 'get') else None) or '/ce/course/'
    try:
        return get_table_config('faculty_coords_table').build_config(
            variant=COURSE_ADMINISTRATORS_VARIANT,
            api_url=context.get('course_administrator_url') or COURSE_ADMINISTRATORS_API,
            details_prefix=details_prefix,
        )
    except KeyError:  # tenant service without this variant yet
        return None
