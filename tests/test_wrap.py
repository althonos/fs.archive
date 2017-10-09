# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import datetime

from fs import errors
from fs.test import FSTestCases
from fs.wrap import WrapReadOnly
from fs.memoryfs import MemoryFS

from fs.archive.wrap import WrapWritable


def timestamp(d):
    d = d.replace(tzinfo=None)
    return (d - datetime.datetime.utcfromtimestamp(0)).total_seconds()


class TestWrapWritable(FSTestCases, unittest.TestCase):

    def assertDatetimeEqual(self, d1, d2):
        t1 = int(timestamp(d1))
        t2 = int(timestamp(d2))
        self.assertEqual(t1, t2)

    def make_fs(self):
        src_fs = self.sfs = MemoryFS()
        src_fs.makedirs('foo/bar')
        src_fs.settext('root.txt', 'root file')
        src_fs.setbytes('foo/nested.bin', b'nested file')
        wrapped_fs = self.wfs = WrapWritable(WrapReadOnly(src_fs))
        wrapped_fs.remove('root.txt')
        wrapped_fs.remove('foo/nested.bin')
        wrapped_fs.removedir('foo/bar')
        wrapped_fs.removedir('foo')
        return wrapped_fs

    def test_appendbytes(self):
        super(TestWrapWritable, self).test_appendbytes()
        self.assertRaises(errors.ResourceNotFound, self.fs.appendbytes, "abc/def", b'abc')
        self.wfs.makedir("abc")
        self.assertRaises(errors.FileExpected, self.fs.appendbytes, "abc", b'abc')
        self.wfs.appendbytes('root.txt', b'surprise')
        self.assertEqual(self.fs.getbytes('root.txt'), b'surprise')
        self.sfs.setbytes('root.bin', b'root bytes')
        self.wfs.appendbytes('root.bin', b'other bytes')
        self.assertEqual(self.fs.getbytes('root.bin'), b'root bytesother bytes')

    def test_appendtext(self):
        super(TestWrapWritable, self).test_appendtext()
        self.assertRaises(errors.ResourceNotFound, self.fs.appendtext, "abc/def", 'abc')
        self.wfs.makedir("abc")
        self.assertRaises(errors.FileExpected, self.fs.appendtext, "abc", 'abc')
        self.wfs.appendtext('root.txt', 'surprise')
        self.assertEqual(self.fs.gettext('root.txt'), 'surprise')
        self.sfs.settext('root.bin', 'root text')
        self.wfs.appendtext('root.bin', 'other text')
        self.assertEqual(self.fs.gettext('root.bin'), 'root textother text')

    def test_makedir(self):
        super(TestWrapWritable, self).test_makedir()
        self.assertRaises(errors.ResourceNotFound, self.fs.makedir, 'abc/def')
        self.fs.touch('abc')
        self.assertRaises(errors.DirectoryExpected, self.fs.makedir, 'abc/def')

    def test_setinfo_wrapped(self):
        epoch = datetime.datetime.fromtimestamp(0)
        now = datetime.datetime.now()
        self.sfs.settext('test.txt', 'test file')
        self.sfs.setinfo('test.txt', {'details':
            {'modified': timestamp(epoch), 'accessed': timestamp(epoch)}
        })
        self.assertDatetimeEqual(self.sfs.getdetails('test.txt').modified, epoch)
        self.assertDatetimeEqual(self.wfs.getdetails('test.txt').modified, epoch)
        self.assertDatetimeEqual(self.wfs.getdetails('test.txt').accessed, epoch)
        self.wfs.setinfo('test.txt', {'details':
            {'modified': timestamp(now)}
        })
        self.assertDatetimeEqual(
            self.wfs.getdetails('test.txt').accessed,
            self.sfs.getdetails('test.txt').accessed
        )
        self.assertDatetimeEqual(self.wfs.getdetails('test.txt').modified, now)

    def test_openbin_wrapped(self):
        self.sfs.setbytes('test.txt', b'this is a test')
        with self.wfs.openbin('test.txt', 'r') as f:
            self.assertEqual(f.read(), b'this is a test')
        with self.wfs.openbin('test.txt', 'r+') as f:
            self.assertEqual(f.read(), b'this is a test')
            f.seek(0)
            f.write(b'test should work')
        self.assertEqual(self.wfs.gettext('test.txt'), 'test should work')
