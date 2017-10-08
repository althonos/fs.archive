# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest



from fs.test import FSTestCases
from fs.wrap import WrapReadOnly
from fs.opener import open_fs

from fs.archive.wrap import WrapWritable



class TestWrapWritable(FSTestCases, unittest.TestCase):

    def make_fs(self):
        src_fs = open_fs('mem://')
        src_fs.makedirs('foo/bar')
        src_fs.settext('root.txt', 'root file')
        src_fs.setbytes('foo/nested.bin', b'nested file')
        wrapped_fs = WrapWritable(WrapReadOnly(src_fs))
        wrapped_fs.remove('root.txt')
        wrapped_fs.remove('foo/nested.bin')
        wrapped_fs.removedir('foo/bar')
        wrapped_fs.removedir('foo')
        return wrapped_fs
