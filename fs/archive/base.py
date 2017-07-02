# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import abc
import six
import shutil
import tempfile

from .. import errors

from ..base import FS
from ..proxy.writer import ProxyWriter


@six.add_metaclass(abc.ABCMeta)
class ArchiveSaver(object):

    def __init__(self, output, overwrite=False, stream=True, **options):
        self.output = output
        self.overwrite = overwrite
        self.stream = stream

        if hasattr(output, 'tell'):
            self._initial_position = output.tell()

    def save(self, fs):
        if self.stream:
            self.to_stream(fs)
        else:
            self.to_file(fs)

    def to_file(self, fs):
        if self.overwrite: # If we need to overwrite, use temporary file
            tmp = '.'.join([self.output, 'tmp'])
            self._to(tmp, fs)
            shutil.move(tmp, self.output)
        else:
            self._to(self.output, fs)

    def to_stream(self, fs):
        if self.overwrite: # If we need to overwrite, use temporary file
            fd, temp = tempfile.mkstemp()
            os.close(fd)
            self._to(temp, fs)

            self.output.seek(self._initial_position)
            with open(temp, 'rb') as f:
                shutil.copyfileobj(f, self.output)

        else:
            self._to(self.output, fs)

    @abc.abstractmethod
    def _to(self, handle, fs):
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class ArchiveReadFS(FS):

    def __init__(self, handle, **options):
        super(ArchiveReadFS, self).__init__()
        self._handle = handle

    def __repr__(self):
        return "{}({!r})".format(
            self.__class__.__name__,
            getattr(self._handle, 'name', self._handle),
        )

    def __str__(self):
        return "<{} '{}'>".format(
            self.__class__.__name__.lower(),
            getattr(self._handle, 'name', self._handle),
        )

    def _on_modification_attempt(self, path):
        raise errors.ResourceReadOnly(path)

    def setinfo(self, path, info):
        self.check()
        self._on_modification_attempt(path)

    def makedir(self, path, permissions=None, recreate=False):
        self.check()
        self._on_modification_attempt(path)

    def remove(self, path):
        self.check()
        self._on_modification_attempt(path)

    def removedir(self, path):
        self.check()
        self._on_modification_attempt(path)


@six.add_metaclass(abc.ABCMeta)
class ArchiveFS(ProxyWriter):
    _read_fs_cls = ArchiveReadFS
    _saver_cls = ArchiveSaver

    def __init__(self, handle, proxy=None, **options):

        if isinstance(handle, six.text_type):
            stream = False
            saver = True

            if os.path.exists(handle):
                read_only = self._read_fs_cls(handle, **options)
            else:
                read_only = None


        elif isinstance(handle, io.IOBase):
            stream = True
            saver = handle.writable()

            if handle.readable() and handle.seekable():
                read_only = self._read_fs_cls(handle, **options)
            else:
                read_only = None

        else:
            raise errors.CreateFailed("cannot use {}".format(handle))

        if saver:
            self._saver = self._saver_cls(handle, read_only is not None, stream)
        else:
            self._saver = None

        super(ArchiveFS, self).__init__(read_only, proxy)

    def close(self):
        if not self.isclosed():
            if self._saver is not None:
                self._saver.save(self)
            super(ArchiveFS, self).close()
