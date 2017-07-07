# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import unittest
import construct

import fs.memoryfs
import fs.archive.isofs

import fs.test

from fs.archive.test import ArchiveReadTestCases
# from fs.archive.isofs import structs


class TestISOFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        handle = io.BufferedWriter(io.BytesIO())
        return fs.archive.isofs.ISOFS(handle)



#
# class _TestISOReadFS(ArchiveReadTestCases):
#
#     long_names = False
#     unicode_names = False
#
#     make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
#     _archive_read_fs = fs.archive.isofs.ISOReadFS
#
#     def compress(self, handle, source_fs):
#         tests_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
#         resources_path = os.path.join(tests_dir, 'resources')
#         with open(os.path.join(resources_path, self.img_file), 'rb') as iso_file:
#             handle.write(iso_file.read())
#
#     @staticmethod
#     def remove_archive(handle):
#         handle.close()
#
#     def setUp(self):
#         handle = io.BytesIO()
#         super(_TestISOReadFS, self).setUp(handle)
#
#
#
# class TestISOReadFSLevel1(_TestISOReadFS, unittest.TestCase):
#     img_file = 'test.iso'
#
# class TestISOReadFSJoliet(_TestISOReadFS, unittest.TestCase):
#     unicode_names = True
#     img_file = 'test.joliet.iso'
#
# class TestISOReadFSRockRidge(_TestISOReadFS, unittest.TestCase):
#     unicode_names = True
#     img_file = 'test.rr.iso'
#
#
# class TestISOStructs(unittest.TestCase):
#
#     def test_both_endian(self):
#
#         be1 = structs.BothEndian(construct.Int8ul, construct.Int8ub)
#         self.assertEqual(be1.parse(b'\x01\x01'), 1)
#         self.assertEqual(be1.build(1), b'\x01\x01')
#         self.assertEqual(be1.sizeof(), 2)
#
#         be2 = structs.BothEndian(construct.Int32sb, construct.Int32sl)
#         self.assertEqual(be2.parse(b'\xff\xff\xfd\xde\xde\xfd\xff\xff'), -546)
#         self.assertEqual(be2.build(2048), b'\0\0\x08\0\0\x08\0\0')
#         self.assertEqual(be2.sizeof(), 8)
#
#         be3 = structs.BothEndian(construct.Int8un, construct.Int8un)
#         self.assertEqual(be3.parse(construct.Int8un.build(99)*2), 99)
#         self.assertEqual(be3.build(123), construct.Int8un.build(123)*2)
#
#         be4 = structs.BothEndian(construct.Int16un, construct.Int16un)
#         with self.assertRaises(construct.FieldError):
#             be4.parse(b'\x00\x01\x00\x00')
#
#     def test_long_time(self):
#
#         lt = structs.LongTime
#         time1 = structs.LongTime.parse(b'1824041900000000\x0c')
#         self.assertEqual(time1.year, b'1824')
#         self.assertEqual(time1.month, b'04')
#         self.assertEqual(time1.day, b'19')
#         self.assertEqual(time1.hour, b'00')
#         self.assertEqual(time1.minute, b'00')
#         self.assertEqual(time1.second, b'00')
#         self.assertEqual(time1.hundredths, b'00')
#         self.assertEqual(time1.gmt_offset, 12)
#
#     #def test_long_time_adapter(self):
#     #    pass
#
#     # def test_short_time(self):
#     #     pass
#
#     # def test_short_time_adapter(self):
#     #     pass
