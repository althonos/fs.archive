# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import unittest
import tempfile

try:
    from unittest import mock
except ImportError:
    import mock

from fs.archive import _utils


class TestUtils(unittest.TestCase):

    @unittest.skipUnless(os.name == 'posix', 'POSIX platform needed')
    def test_writable_path(self):
        self.assertFalse(_utils.writable_path('/'))
        self.assertFalse(_utils.writable_path('/root_location'))
        self.assertTrue(_utils.writable_path(__file__))

    def test_writable_stream(self):
        with tempfile.NamedTemporaryFile(mode='wb+') as tmp:
            self.assertTrue(_utils.writable_stream(tmp))
            with open(tmp.name, 'rb') as tmp2:
                self.assertFalse(_utils.writable_stream(tmp2))

        buff = io.BytesIO()
        self.assertTrue(_utils.writable_stream(buff))
        buff = io.BufferedReader(buff)
        self.assertFalse(_utils.writable_stream(buff))

        buff = mock.MagicMock()
        buff.write = mock.MagicMock(side_effect=IOError("not writable"))
        self.assertFalse(_utils.writable_stream(buff))

    def test_import_from_names(self):
        imp = _utils.import_from_names
        self.assertIs(imp('os'), os)
        self.assertIs(imp('akjhkjhsk', 'os'), os)
        self.assertIs(imp('akeskjhk'), None)

    def test_unique(self):
        self.assertEqual(
            list(_utils.unique(iter('aaabbbccdef'))),
            list('abcdef')
        )
        self.assertEqual(
            list(_utils.unique(['a', 'aa', 'bb', 'ccc', 'ddd'], key=len)),
            ['a', 'aa', 'ccc',]
        )

    def test_universal_container(self):
        c = _utils.UniversalContainer()
        self.assertIn(1, c)
        self.assertIn(None, c)
