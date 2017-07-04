# coding: utf-8
"""Base classes to test archive filesystems.

Adapted from the core Pyfilesystem2 test module `test_archives.py
<https://github.com/PyFilesystem/pyfilesystem2/blob/master/tests/test_archives.py>`_
written by `Will McGugan <https://github.com/willmcgugan>`_ under the **MIT**
license.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import abc
import six
import sys
import shutil
import tempfile

from .. import open_fs
from .. import walk
from .. import errors
from ..test import UNICODE_TEXT

from . import base


@six.add_metaclass(abc.ABCMeta)
class ArchiveReadTestCases(object):
    """Base class to test ArchiveReadFS subclasses.
    """

    @abc.abstractproperty
    def _archive_read_fs(self):
        """The ArchiveReadFS class to test.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def compress(self, handle, fs):
        """Compress ``fs`` and write the resulting archive to ``handle``.
        """
        pass

    @abc.abstractmethod
    def remove_archive(self, handle):
        """Remove the archive in ``handle``
        """
        pass

    def make_source_fs(self):
        """Create the source filesystem.
        """
        return open_fs('temp://')

    def build_source(self, fs):
        """Create the test structure in the source filesystem.
        """
        fs.makedirs('foo/bar/baz')
        fs.makedir('tmp')
        fs.settext('top.txt', 'Hello, World')
        fs.settext('top2.txt', 'Hello, World')
        fs.settext('foo/bar/egg', 'foofoo')
        fs.makedir('unicode')
        fs.settext('unicode/text.txt', UNICODE_TEXT)

    def setUp(self, handle):
        self.handle = handle
        self.source_fs = source_fs = self.make_source_fs()
        self.build_source(source_fs)
        self.compress(self.handle, source_fs)
        self.handle.seek(0)
        self.fs = self._archive_read_fs(self.handle)

        self.assertIsInstance(
            self.fs, base.ArchiveReadFS,
            'load_archive did not return an ArchiveReadFS.'
        )

    def tearDown(self):
        self.source_fs.close()
        self.fs.close()
        self.remove_archive(self.handle)

    def test_create_failed(self):
        """Check CreateFailed is on rubbish input stream.
        """
        handle = io.BytesIO()
        handle.write(b'a'*100+b'z'*100)
        handle.seek(0)

        with self.assertRaises(errors.CreateFailed):
            self._archive_read_fs(handle)

    def test_repr(self):
        """Check that `__repr__` doesn't raise any error.
        """
        repr(self.fs)

    def test_str(self):
        """Check that `__str__` can be coerced to `six.text_type`.
        """
        self.assertIsInstance(six.text_type(self.fs), six.text_type)

    def test_scandir(self):
        """Check that `fs.base.FS.scandir` has the expected behaviour.
        """

        dirsize = self.fs.getdetails('foo').size
        if dirsize is None:
            self.skipTest("Filesystem does not support 'details' namespace")

        for entry in self.fs.scandir('/', namespaces=('details',)):
            if entry.is_dir:
                self.assertEqual(entry.size, dirsize)
            else:
                self.assertEqual(entry.size, len(self.fs.getbytes(entry.name)))

        with self.assertRaises(errors.ResourceNotFound):
            _ = next(self.fs.scandir('what'))
        with self.assertRaises(errors.DirectoryExpected):
            _ = next(self.fs.scandir('top.txt'))

    def test_readonly(self):
        """Check that read-only filesystems raise an error on edit attempts.
        """
        self.assertTrue(self.fs.getmeta().get('read_only'),
                        'Filesystem is not read-only.')

        with self.assertRaises(errors.ResourceReadOnly):
            self.fs.makedir('newdir')
        with self.assertRaises(errors.ResourceReadOnly):
            self.fs.remove('top.txt')
        with self.assertRaises(errors.ResourceReadOnly):
            self.fs.removedir('foo/bar/baz')
        with self.assertRaises(errors.ResourceReadOnly):
            self.fs.create('foo.txt')
        with self.assertRaises(errors.ResourceReadOnly):
            self.fs.setinfo('foo.txt', {})

    def test_getinfo(self):
        """Check that `fs.base.FS.getinfo` has the expected behaviour.
        """
        root = self.fs.getinfo('/')
        self.assertEqual(root.name, '')
        self.assertTrue(root.is_dir)

        top = self.fs.getinfo('top.txt', 'details')
        self.assertEqual(top.size, 12)
        self.assertFalse(top.is_dir)

        with self.assertRaises(errors.ResourceNotFound):
            _ = self.fs.getinfo('boom.txt')

    def test_listdir(self):
        """Check that `fs.base.FS.listdir` has the expected behaviour.
        """
        self.assertEqual(
            sorted(self.source_fs.listdir('/')),
            sorted(self.fs.listdir('/'))
        )
        with self.assertRaises(errors.DirectoryExpected):
            self.fs.listdir('top.txt')
        with self.assertRaises(errors.ResourceNotFound):
            self.fs.listdir('nothere')

    def test_open(self):
        """Check that `fs.base.FS.open` has the expected behaviour.
        """
        with self.fs.open('top.txt') as f:
            chars = []
            while True:
                c = f.read(2)
                if not c:
                    break
                chars.append(c)
            self.assertEqual(
                ''.join(chars),
                'Hello, World'
            )
        with self.assertRaises(errors.ResourceNotFound):
            with self.fs.open('nothere.txt') as f:
                pass
        with self.assertRaises(errors.FileExpected):
            with self.fs.open('foo') as f:
                pass

    def test_gettext(self):
        """Check that `fs.base.FS.gettext` has the expected behaviour.
        """
        self.assertEqual(self.fs.gettext('top.txt'), 'Hello, World')
        self.assertEqual(self.fs.gettext('foo/bar/egg'), 'foofoo')
        self.assertRaises(errors.ResourceNotFound, self.fs.getbytes, 'what.txt')
        self.assertRaises(errors.FileExpected, self.fs.gettext, 'foo')

    def test_getbytes(self):
        """Check that `fs.base.FS.getbytes` has the expected behaviour.
        """
        self.assertEqual(self.fs.getbytes('top.txt'), b'Hello, World')
        self.assertEqual(self.fs.getbytes('foo/bar/egg'), b'foofoo')
        self.assertRaises(errors.ResourceNotFound, self.fs.gettext, 'what.txt')
        self.assertRaises(errors.FileExpected, self.fs.getbytes, 'foo')

    def test_walk_files(self):
        """Check that `fs.base.FS.walk.files` has the expected behaviour.
        """
        source_files = sorted(walk.walk_files(self.source_fs))
        archive_files = sorted(walk.walk_files(self.fs))

        self.assertEqual(
            source_files,
            archive_files
        )

    def test_implied_dir(self):
        """Check that implied directories are accessible from archives.
        """
        self.fs.getinfo('foo/bar')
        self.fs.getinfo('foo')



@six.add_metaclass(abc.ABCMeta)
class ArchiveIOTestCases(object):
    """Base class to test ArchiveFS subclasses openers.
    """

    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)

    @abc.abstractproperty
    def _archive_fs(self):
        """The ArchiveFS class to test.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def compress(self, handle, fs):
        """Compress ``fs`` and write the resulting archive to ``handle``.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_files(self, handle):
        """Return an iterator over the files in the archive in ``handle``.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def iter_dirs(self, handle):
        """Return an iterator over the directories in the archive in ``handle``.
        """
        raise NotImplementedError()

    def tearDown(self):
        if hasattr(self, 'source_fs'):
            self.source_fs.close()
        if hasattr(getattr(self, 'handle', None), 'close'):
            self.handle.close()

    def build_source(self, fs):
        """Create the test structure in the source filesystem.
        """
        fs.settext('foo.txt', 'Hello World !')
        fs.makedir('baz')
        fs.settext('baz/bar.txt', 'Savy ?')
        fs.makedir('egg')

    def make_archive(self, handle):
        self.handle = handle
        self.source_fs = source_fs = self.make_source_fs()
        self.build_source(source_fs)
        self.compress(handle, source_fs)
        if hasattr(handle, 'seek'):
            handle.seek(0)
        return handle

    def make_source_fs(self):
        """Create the source filesystem.
        """
        return open_fs('temp://')

    def _test_read(self, fs):
        self.assertEqual(set(fs.listdir('/')), {'foo.txt', 'egg', 'baz'})
        self.assertEqual(fs.gettext('foo.txt'), 'Hello World !')
        self.assertTrue(fs.exists('baz/bar.txt'))
        self.assertTrue(fs.isdir('egg'))

    def _test_read_write(self, fs):
        self._test_read(fs)
        self._test_write(fs)

    def _test_write(self, fs):
        fs.touch('ham.txt')
        fs.makedirs('/spam/qux')
        fs.touch('/spam/boom.txt')

        if fs.isfile('foo.txt'):
            fs.remove('foo.txt')
        if fs.isdir('egg'):
            fs.removedir('egg')

        self.assertTrue(fs.isdir('spam/qux'))
        self.assertTrue(fs.isfile('spam/boom.txt'))
        self.assertFalse(fs.isdir('egg') or fs.exists('egg'))

    def test_read_stream(self):
        """Check archives can be read from a stream.
        """
        stream = self.make_archive(io.BytesIO())
        with self._archive_fs(io.BufferedReader(stream), close_handle=False) as archive_fs:
            self._test_read(archive_fs)

        self.assertEqual(
            sorted(self.iter_files(stream)),
            ['/baz/bar.txt', '/foo.txt'],
        )
        self.assertEqual(
            sorted(self.iter_dirs(stream)),
            ['/baz', '/egg'],
        )

    def test_read_write_stream(self):
        """Check archives can be updated from and to a stream.
        """
        stream = self.make_archive(io.BytesIO())
        with self._archive_fs(stream, close_handle=False) as archive_fs:
            self._test_read_write(archive_fs)

        self.assertEqual(
            sorted(self.iter_files(stream)),
            ['/baz/bar.txt', '/ham.txt', '/spam/boom.txt'],
        )
        self.assertEqual(
            sorted(self.iter_dirs(stream)),
            ['/baz', '/spam', '/spam/qux'],
        )

    def test_write_stream(self):
        """Check archives can be written to a stream.
        """
        stream = io.BytesIO()
        stream.readable = lambda: False   # mock a write-only stream
        with self._archive_fs(stream, close_handle=False) as zipfs:
            self._test_write(zipfs)

        self.assertEqual(
            sorted(self.iter_files(stream)),
            ['/ham.txt', '/spam/boom.txt'],
        )
        self.assertEqual(
            sorted(self.iter_dirs(stream)),
            ['/spam', '/spam/qux'],
        )

    def test_read_file(self):
        """Check archives can be read from a file.
        """
        filename = os.path.join(self.tempdir, 'read')
        with self._archive_fs(self.make_archive(filename)) as zipfs:
            self._test_read(zipfs)

        self.assertEqual(
            sorted(self.iter_files(filename)),
            ['/baz/bar.txt', '/foo.txt'],
        )
        self.assertEqual(
            sorted(self.iter_dirs(filename)),
            ['/baz', '/egg'],
        )

    def test_read_write_file(self):
        """Check archives can be updated from and to a stream.
        """
        filename = os.path.join(self.tempdir, 'write')
        with self._archive_fs(self.make_archive(filename)) as zipfs:
            self._test_read_write(zipfs)

        self.assertEqual(
            sorted(self.iter_files(filename)),
            ['/baz/bar.txt', '/ham.txt', '/spam/boom.txt'],
        )
        self.assertEqual(
            sorted(self.iter_dirs(filename)),
            ['/baz', '/spam', '/spam/qux'],
        )

    def test_write_file(self):
        """Check archives can be writtent to a stream.
        """
        filename = os.path.join(self.tempdir, 'read_write')
        with self._archive_fs(filename) as zipfs:
            self._test_write(zipfs)
            print(zipfs._saver)

        self.assertEqual(
            sorted(self.iter_dirs(filename)),
            ['/spam', '/spam/qux']
        )
        self.assertEqual(
            sorted(self.iter_files(filename)),
            ['/ham.txt', '/spam/boom.txt']
        )

    def test_iter_dirs(self):
        """Check the `iter_dirs` method works as intented.
        """
        handle = self.make_archive(io.BytesIO())

        self.assertEqual(
            sorted(self.iter_dirs(handle)),
            sorted(self.source_fs.walk.dirs()),
        )

    def test_iter_files(self):
        """Check the `iter_files` method works as intented.
        """
        handle = self.make_archive(io.BytesIO())

        self.assertEqual(
            sorted(self.iter_files(handle)),
            sorted(self.source_fs.walk.files())
        )
