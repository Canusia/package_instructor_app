"""Deleting an application from the CE Details modal reloads the list (#16).

The modal is an iframe; finishDelete() used to only close it, leaving the
deleted row in the parent's tables until a manual refresh.
"""
import pathlib
import re

from django.test import SimpleTestCase

JS = pathlib.Path(__file__).resolve().parents[1] / 'staticfiles' / 'js' / 'ce_application_detail.js'


class DeleteRefreshTests(SimpleTestCase):
    def _finish_delete(self):
        source = JS.read_text()
        match = re.search(r'function finishDelete\(response\) \{(.*?)\n    \}\n', source, re.S)
        self.assertIsNotNone(match, 'finishDelete() not found')
        return match.group(1)

    def test_refreshes_parent_tables_before_closing(self):
        body = self._finish_delete()
        self.assertIn("typeof window.parent.refreshTable === 'function'", body)
        self.assertLess(body.index('window.parent.refreshTable()'),
                        body.index('window.parent.closeModal()'))
