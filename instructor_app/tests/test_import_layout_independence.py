"""Guard against production-only ModuleNotFoundErrors.

This package ships two ways:

* flat in production   — ``site-packages/instructor_app/``
* nested in dev        — ``instructor_app/instructor_app/`` (editable submodule)

Runtime code that writes ``from instructor_app.instructor_app.… import …``
resolves fine in the dev checkout and raises ``ModuleNotFoundError: No module
named 'instructor_app.instructor_app'`` in production. Because the test suite
runs against the nested layout, no ordinary test catches it — this one reads the
source instead of importing it, so it fails in dev.

Relative imports (``from .models.… import …``) work under both layouts and are
the fix.
"""
import os
import re

from django.test import SimpleTestCase

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BAD_IMPORT = re.compile(r'\binstructor_app\.instructor_app\b')

# apps.py legitimately names the nested path: DevInstructorAppConfig exists only
# for the dev layout and is selected by a find_spec check in the host settings.
# tests/ only ever run against the dev checkout.
EXEMPT_DIRS = {'tests', 'migrations', '__pycache__'}
EXEMPT_FILES = {'apps.py'}


def _runtime_python_files():
    for dirpath, dirnames, filenames in os.walk(PACKAGE_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXEMPT_DIRS]
        for name in filenames:
            if name.endswith('.py') and name not in EXEMPT_FILES:
                yield os.path.join(dirpath, name)


class ImportLayoutIndependenceTests(SimpleTestCase):
    def test_no_runtime_module_hardcodes_the_nested_package_path(self):
        offenders = []
        for path in _runtime_python_files():
            with open(path, encoding='utf-8') as fh:
                for lineno, line in enumerate(fh, 1):
                    if BAD_IMPORT.search(line):
                        rel = os.path.relpath(path, PACKAGE_ROOT)
                        offenders.append(f'{rel}:{lineno}: {line.strip()}')

        self.assertEqual(
            offenders, [],
            'These runtime modules hardcode the nested dev-only package path '
            'and will ModuleNotFoundError in production. Use a relative import '
            'instead:\n  ' + '\n  '.join(offenders)
        )
