# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import tempfile
import unittest

from six.moves import filterfalse
from six.moves.queue import Queue

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases

try:
    import pycdlib
except ImportError:
    pycdlib = None

try:
    from fs.archive.isofs import ISOReadFS, ISOFS, ISOSaver
    from fs.archive.isofs import _utils as isofs_utils
except ImportError:
    SevenZipReadFS = SevenZipFS = SevenZipSaver = None
    isofs_utils = None


FS_VERSION = tuple(map(int, fs.__version__.split('.')))


def compress(rr, joliet, il):
    def iso_compress(handle, source_fs):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
        saver = fs.archive.isofs.ISOSaver(
            handle, overwrite=False,
            rock_ridge=rr, joliet=joliet,
            interchange_level=il
        )
        saver.save(source_fs)
    return iso_compress


def iso_name(entry, joliet=False, rock_ridge=False):
    if entry.file_identifier() in b'/':
        return '/'
    elif rock_ridge:
        return entry.rock_ridge.name().decode('utf-8').rsplit(';1').rsplit('.')
    elif joliet:
        return entry.file_identifier().decode('utf-16be')
    return entry.file_identifier().decode('ascii')


def iso_path(iso_entry, joliet=False, rock_ridge=False):
    path = iso_name(iso_entry, joliet, rock_ridge)
    while iso_entry.parent is not None:
        path = join(iso_name(iso_entry.parent, joliet, rock_ridge), path)
        iso_entry = iso_entry.parent
    return abspath(path).lower()


### rw FS ###

@unittest.skipUnless(pycdlib, 'pycdlib not available')
class TestISOFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return ISOFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move(self):
        super(TestISOFS, self).test_move()

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move_file_same_fs(self):
        super(TestISOFS, self).test_move_file_same_fs()

### ro FS ###

@unittest.skipUnless(pycdlib, 'pycdlib not available')
class _TestISOReadFS(ArchiveReadTestCases):

    long_names = False
    unicode_names = False
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_read_fs = ISOReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(_TestISOReadFS, self).setUp(handle)

    def test_create_failed(self):
        self.assertRaises(fs.errors.CreateFailed, ISOFS, 1)


class TestISOv1ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 1))


class TestISOv2ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 2))


class TestISOv3ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 3))


class TestISOv4ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 4))


@unittest.skip('fails')
class TestISORockRidge112ReadFS(_TestISOReadFS, unittest.TestCase):

    long_names = True
    compress = staticmethod(compress('1.12', False, 1))


class TestISORockRidge109ReadFS(_TestISOReadFS, unittest.TestCase):

    long_names = True
    compress = staticmethod(compress('1.09', False, 1))


class TestISOJolietReadFS(_TestISOReadFS, unittest.TestCase):

    long_name = True
    compress = staticmethod(compress(None, True, 1))



### FS IO ###

@unittest.skipUnless(pycdlib, 'pycdlib not available')
class TestISOFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(compress('1.12', False, 1))
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_fs = ISOFS

    @staticmethod
    def load_archive(handle):
        return ISOFS(handle)

    @staticmethod
    def iter_entries(handle):

        cd = pycdlib.PyCdlib()

        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
            cd.open_fp(handle)
        else:
            cd.open(handle)

        rock_ridge = cd.rock_ridge is not None
        joliet = cd.joliet_vd is not None
        joliet_only = joliet and not rock_ridge

        directories = Queue()
        directories.put(cd.get_entry('/', joliet_only))

        while not directories.empty():
            directory = directories.get()

            for child in directory.children:
                if not child.is_dot() and not child.is_dotdot():
                    if child.is_dir():
                        directories.put(child)
                    yield child

    def iter_files(self, handle):
        for entry in self.iter_entries(handle):
            if entry.is_file():
                yield iso_path(entry)

    def iter_dirs(self, handle):
        for entry in self.iter_entries(handle):
            if entry.is_dir():
                yield iso_path(entry)



### FS Saver ###

@unittest.skipUnless(pycdlib, 'pycdlib not available')
class TestISOSaver(unittest.TestCase):

    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)

    def test_unicode_duplicates(self):
        """Check unicode names are not collisioning when slugified.
        """
        source = self.make_source_fs()
        source.makedir('/😋')
        source.settext('/😋/éé.txt', 'some accents in an emoji')
        source.settext('/éé.txt', 'some accents')
        source.settext('/üü.txt', 'some umlauts')
        source.settext('/☭☭.txt', 'some communism')

        stream = io.BytesIO()
        saver = ISOSaver(stream)
        saver.save(source)

        stream.seek(0)
        iso = ISOReadFS(stream)
        self.assertEqual(
            sorted(iso.listdir('/')),
            ['éé.txt', 'üü.txt' ,'☭☭.txt', '😋'],
        )
        self.assertEqual(iso.gettext('/éé.txt'), 'some accents')
        self.assertEqual(iso.gettext('/üü.txt'), 'some umlauts')
        self.assertEqual(iso.gettext('/☭☭.txt'), 'some communism')
        self.assertEqual(iso.gettext('/😋/éé.txt'), 'some accents in an emoji')



### utils ###

@unittest.skipUnless(isofs_utils, 'fs.archive.isofs not available')
class TestISOUtils(unittest.TestCase):

    def test_name_slugify(self):
        slugify = isofs_utils.iso_name_slugify
        self.assertEqual(slugify("épatant"), "_patant")

    def test_name_increment(self):
        increment = isofs_utils.iso_name_increment
        self.assertEqual(increment('foo.txt'), 'foo1.txt')
        self.assertEqual(increment('foo1.txt'), 'foo2.txt')
        self.assertEqual(increment('foo9.txt'), 'foo10.txt')
        self.assertEqual(increment('foo9.txt', max_length=4), 'fo10.txt')
        self.assertEqual(increment('bar'), 'bar1')
        self.assertEqual(increment('bar1'), 'bar2')
        self.assertEqual(increment('bar9'), 'bar10')
        self.assertEqual(increment('bar9', max_length=4), 'ba10')

    def test_path_slugify(self):
        slugify = isofs_utils.iso_path_slugify
        pt = {'/': '/'}
        self.assertEqual(slugify('/abc.txt', pt), '/ABC.TXT')
        self.assertEqual(slugify('/àbc.txt', pt), '/_BC.TXT')
        self.assertEqual(slugify('/àbç.txt', pt), '/_B_.TXT')
        self.assertEqual(slugify('/àbé.txt', pt), '/_B_1.TXT')
        self.assertEqual(slugify('/àbé.txt', pt, True), '/_B_.TXT1')
        self.assertEqual(slugify('/àbè.txt', pt, True), '/_B_.TXT2')
