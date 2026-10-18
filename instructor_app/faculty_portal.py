"""The faculty portal page text setting (package-cis#81).

The faculty package (Canusia/package-faculty, myce_faculty) owns this text
now, as `faculty.settings.faculty_portal_text`. Read it when that app is
installed (nested submodule or pip layout); fall back to the cis setting it
replaces on hosts that still carry the in-tree faculty app.
"""
import importlib
import importlib.util

_CANDIDATES = (
    'faculty.faculty.settings.faculty_portal_text',
    'faculty.settings.faculty_portal_text',
)


def faculty_portal_setting():
    """The setting class; call it as before: faculty_portal_setting()(request).from_db()."""
    for module in _CANDIDATES:
        try:
            found = importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:   # parent package missing
            found = False
        if found:
            return importlib.import_module(module).faculty_portal_text
    from cis.settings.faculty_portal import faculty_portal
    return faculty_portal
