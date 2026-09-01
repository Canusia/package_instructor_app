"""Resolve table-config services from the tenant-configured app.

Mirrors `cis.services.table_configs`. It keeps `instructor_app` decoupled from
any one tenant's `myce_tenant_configs` app name: callers ask for
`get_table_config('faculty_coords_table').build_config(...)` and the module is
loaded from `settings.TABLE_CONFIGS_APP`.

Why this exists here as well as in `cis`
----------------------------------------
`instructor_app` currently renders several tables from hand-written markup with
inline `.DataTable({...})` initialisers — most visibly the
`#course_administrators` tab on the CE courses page. Those tables show the same
`CourseAdministrator` rows as the faculty pages in `cis`, which have moved onto
the shared per-tenant table services, so the two surfaces have drifted apart in
both columns and bulk actions.

This seam is the enabling step for closing that gap without a cross-package
template include: `instructor_app` resolves the same tenant service `cis` does,
so one config drives both surfaces.

HOST REQUIREMENT — read before upgrading
----------------------------------------
Using this seam makes `settings.TABLE_CONFIGS_APP` and the named service module
a REQUIREMENT of the host, not an optional extra. A tenant on a release that
calls `get_table_config(...)` without providing that setting, or without the
requested `<app>.services.<name>_table` module, fails at the point of use.

`available()` is provided so a caller can degrade rather than raise; prefer it
over a bare `get_table_config()` in any code path that must keep working on a
tenant that has not been migrated yet.
"""
import importlib

from django.conf import settings


def get_table_config(module_name):
    """Return the named `_table` service module from the tenant app.

    Raises ImproperlyConfigured if the host does not define
    settings.TABLE_CONFIGS_APP, and ModuleNotFoundError if that app does not
    ship the requested service module. Both are host-configuration problems,
    not bugs in this package -- see `available()` to check first.
    """
    from django.core.exceptions import ImproperlyConfigured

    app = getattr(settings, 'TABLE_CONFIGS_APP', None)
    if not app:
        raise ImproperlyConfigured(
            'instructor_app requires settings.TABLE_CONFIGS_APP to resolve '
            'shared table configs. See the "Shared table configs" section of '
            "this package's README."
        )

    return importlib.import_module(f'{app}.services.{module_name}')


def available(module_name):
    """True when the host can supply the named table-config service.

    Lets a caller fall back to its own markup on a tenant that has not yet
    adopted the shared services, instead of raising at render time.
    """
    try:
        get_table_config(module_name)
    except Exception:
        return False
    return True
