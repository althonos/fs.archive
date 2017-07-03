# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import abc
import six
import sys
import shutil
import tempfile

from .. import errors

from ..base import FS
from ..proxy.writer import ProxyWriter

def _writable(handle):
    if isinstance(handle, io.IOBase) and sys.version_info >= (3, 5):
        return handle.writable()
    try:
        handle.write(b'')
    except (io.UnsupportedOperation, OSError):
        return False
    else:
        return True



@six.add_metaclass(abc.ABCMeta)
class ArchiveSaver(object):

    def __init__(self, output, overwrite=False, initial_position=0, **options):
        self.output = output
        self.overwrite = overwrite
        self.initial_position = initial_position
        self.stream = isinstance(output, io.IOBase)

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

            self.output.seek(self.initial_position)
            with open(temp, 'rb') as f:
                shutil.copyfileobj(f, self.output)

            os.remove(temp)

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

    def getmeta(self, namespace="standard"):
        if namespace == "standard":
            return self._meta.copy()
        return {}


@six.add_metaclass(abc.ABCMeta)
class ArchiveFS(ProxyWriter):
    _read_fs_cls = ArchiveReadFS
    _saver_cls = ArchiveSaver

    def __init__(self, handle, proxy=None, **options):

        initial_position = 0

        if isinstance(handle, six.binary_type):
            handle = handle.decode('utf-8')

        if isinstance(handle, six.text_type):
            create_saver = True
            read_only = self._read_fs_cls(handle, **options) \
                        if os.path.exists(handle) else None

        elif hasattr(handle, 'read'):
            create_saver = _writable(handle)
            initial_position = getattr(handle, 'tell', lambda: 0)()
            read_only = self._read_fs_cls(handle, **options) \
                        if handle.readable() and handle.seekable() \
                        else None

        else:
            raise errors.CreateFailed("cannot use {}".format(handle))

        overwrite = read_only is not None
        self._saver = self._saver_cls(handle, overwrite, initial_position) \
                      if create_saver else None

        super(ArchiveFS, self).__init__(read_only, proxy)

    def close(self):
        if not self.isclosed():
            if self._saver is not None:
                self._saver.save(self)
            super(ArchiveFS, self).close()
