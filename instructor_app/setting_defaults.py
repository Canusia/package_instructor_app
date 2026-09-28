"""Seed-only Setting.install() for instructor_app's settings (package-cis #51).

Kept out of the settings/ package so the settings registry never mistakes it
for a setting.
"""
from cis.models.settings import Setting


def install_defaults(key, defaults):
    """Create the setting, or add only the keys it lacks (package-cis #19/#51).

    Setting.install_defaults when the installed cis ships it (v0.0.39+);
    otherwise the same merge inline, because this package also runs on
    tenants pinned to an older cis. Never overwrites a customised value.
    """
    helper = getattr(Setting, 'install_defaults', None)
    if helper is not None:
        return helper(key, defaults)
    setting, created = Setting.objects.get_or_create(
        key=key, defaults={'value': dict(defaults)})
    if not created:
        stored = setting.value if isinstance(setting.value, dict) else {}
        missing = {k: v for k, v in defaults.items() if k not in stored}
        if missing:
            stored.update(missing)
            setting.value = stored
            setting.save()
    return setting
