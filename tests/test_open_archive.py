# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import six
import gzip
import zipfile
import tarfile
import unittest
import pkg_resources

import fs.archive
import fs.errors

from fs.wrap import WrapReadOnly
from fs.opener import errors
from fs.archive.zipfs import ZipFS
from fs.archive.tarfs import TarFS, TarFile
from fs.archive._utils import import_from_names

lzma = import_from_names('lzma', 'backports.lzma')


class TestOpenArchive(unittest.TestCase):

    def test_open_unknown_archive(self):
        """Check opening an unknown archive type raises `Unsupported`.
        """
        with self.assertRaises(errors.UnsupportedProtocol):
            with fs.archive.open_archive('mem://', 'not-an-archive.txt'):
                pass

    def test_open_read_only(self):
        mem = fs.open_fs('mem://')
        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertIsInstance(archive, fs.archive.zipfs.ZipFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        mem = WrapReadOnly(mem)
        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertIsInstance(archive, fs.archive.zipfs.ZipReadFS)

    def test_zip(self):
        """Check ``*.zip`` files are opened in `ZipFS` filesystems.
        """
        mem = fs.open_fs('mem://')
        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertIsInstance(archive, ZipFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertEqual(sorted(archive.listdir('/')), ['abc.txt', 'dir'])
            self.assertEqual(archive.gettext('abc.txt'), 'abc')

        with mem.openbin('myzip.zip') as myzip:
            self.assertTrue(zipfile.is_zipfile(myzip))

    def _test_tar(self, filename, arcfile, opener):

        mem = fs.open_fs('mem://')

        # Check we can write
        with fs.archive.open_archive(mem, filename) as archive:
            self.assertIsInstance(archive, fs.archive.tarfs.TarFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        # Check the dumped archive is a gzipped file
        with mem.openbin(filename) as mytar:
            arc = arcfile(mytar)
            arc.read(1)

        # Check we can open it normally
        with mem.openbin(filename) as mytar:
            tar = getattr(TarFile, opener)(filename, fileobj=mytar)
        with mem.openbin(filename) as mytar:
            tar = TarFile.open(filename, fileobj=mytar)

        # Check we can read it with the TarFS
        with fs.archive.open_archive(mem, filename) as archive:
            self.assertEqual(sorted(archive.listdir('/')), ['abc.txt', 'dir'])
            self.assertEqual(archive.gettext('abc.txt'), 'abc')

    def test_tar_gz(self):
        """Check ``*.tar.gz`` files are opened in `TarFS` filesystems.
        """
        arc_gz = lambda fileobj: gzip.GzipFile(fileobj=fileobj)
        self._test_tar('mytar.tar.gz', arc_gz, 'gzopen')
        self._test_tar('mytar.tgz', arc_gz, 'gzopen')

    @unittest.skipIf(lzma is None, 'lzma module is not installed')
    def test_tar_xz(self):
        """Check ``*.tar.xz`` files are opened in `TarFS` filesystems.
        """
        arc_lz = lambda fileobj: lzma.LZMAFile(fileobj)
        self._test_tar('mytar.tar.xz', arc_lz, 'xzopen')
        self._test_tar('mytar.txz', arc_lz, 'xzopen')

    @unittest.skipUnless(lzma is None, 'lzma module is installed')
    def test_tar_no_xz(self):
        """Check opening ``*.tar.xz`` raises `Unsupported` on missing extras.
        """
        with self.assertRaises(fs.errors.Unsupported):
            with fs.archive.open_archive('mem://', 'archive.tar.xz'):
                pass
        with self.assertRaises(fs.errors.Unsupported):
            with fs.archive.open_archive('mem://', 'archive.txz'):
                pass

    # def test_iso(self):
    #
    #     test_dir = os.path.dirname(os.path.abspath(__file__))
    #     resources_dir = os.path.join(test_dir, 'resources')
    #
    #     with fs.open_fs(resources_dir) as resources_fs:
    #         try:
    #             with fs.archive.open_archive(resources_fs, 'test.iso') as iso_fs:
    #                 self.assertIsInstance(iso_fs, ISOReadFS)
    #                 self.assertFalse(iso_fs._handle.writable())
    #         except errors.Unsupported:
    #             self.skipTest('iso support is not enabled')
