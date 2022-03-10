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
from ..mode import Mode
from ..copy import copy_file
from ..path import abspath, normpath, join, dirname
from ..base import FS
from ..opener import open_fs
from ..wrapfs import WrapFS
from ..multifs import MultiFS
from .._fscompat import fsdecode, fspath

from .wrap import WrapWritable
from ._utils import writable_stream, writable_path, unique


@six.add_metaclass(abc.ABCMeta)
class ArchiveSaver(object):
    """Base class for archive serializers.
    """

    def __init__(self, output, overwrite=False, initial_position=0, **options):
        """Create a new serializer.

        Parameters:
            output (`io.IOBase` or `str`): The filename of the destination
                or a file handle in which to write the archive.
            overwrite (`boolean`): If True, use a temporary file to save
                the contents of the archive. Useful when updating an archive
                file. **[default: False]**
            initial_position (`int`): The initial position of the stream when
                it was seen for the first time. **[default: 0]**

        """
        self.output = output
        self.overwrite = overwrite
        self.initial_position = initial_position
        self.stream = isinstance(output, io.IOBase)

    def save(self, fs):
        """Save the given FS.

        Parameters:
            fs (`fs.base.FS`): the filesystem to save in the archive.

        """
        if self.stream:
            self.to_stream(fs)
        else:
            self.to_file(fs)

    def to_file(self, fs):
        """Save the given FS, considering ``self.output`` as a filename.

        Parameters:
            fs (`fs.base.FS`): the filesystem to save in the archive.

        """
        if self.overwrite: # If we need to overwrite, use temporary file
            tmp = '.'.join([self.output, 'tmp'])
            self._to(tmp, fs)
            shutil.move(tmp, self.output)
        else:
            self._to(self.output, fs)

    def to_stream(self, fs):
        """Save the given FS, considering ``self.output`` as a stream.

        Parameters:
            fs (`fs.base.FS`): the filesystem to save in the archive.

        """
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
        """Save the given FS to the given stream handle.

        Parameters:
            handle (`io.IOBase`): a writable stream in which to write
                the filesystem in an archive.
            fs (`fs.base.FS`): the filesystem to save.

        """
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class ArchiveReadFS(FS):
    """A filesystem allowing to read an archive.
    """

    _meta = NotImplemented

    def __init__(self, handle, **options):
        """Create a new archive reader filesystem.

        Parameters:
            handle (`io.IOBase` or `str`): A filename or a readable
                file-like object storing the archive to read.

        Keyword Arguments:
            close_handle (`boolean`): If ``True``, close the handle
                when the filesystem is closed. **[default: True]**

        Raises:
            `TypeError`: When ``handle`` does not have the right type.
            `~fs.errors.CreateFailed`: When ``handle`` could not be used to
                created a new `ArchiveReadFS`.

        """
        super(ArchiveReadFS, self).__init__()

        self._close_handle = False
        self._handle = None

        if isinstance(handle, six.binary_type):
            # Decode the path if it is in binary format
            handle = fsdecode(fspath(handle))

        if isinstance(handle, six.text_type):
            # Expand the path
            _path = os.path.expanduser(os.path.expandvars(handle))
            _path = os.path.normpath(os.path.abspath(_path))
            # Create the readable fs if the handle exists
            try:
                self._close_handle = True
                self._handle = open(_path, 'rb')
            except Exception as err:
                six.raise_from(errors.CreateFailed("Could not open {!r}".format(handle)), err)

        elif hasattr(handle, 'read'):
            # Create the readable fs if the handle is readable
            if handle.readable() and handle.seekable():
                self._close_handle = options.get('close_handle', True)
                self._handle = handle
            else:
                raise errors.CreateFailed("Could not read or seek from {!r}".format(handle))

        else:
            ty = type(handle).__name__
            raise TypeError("Expected str, bytes or file-like handle, found {}".format(ty))

    def __repr__(self):  # noqa: D105
        return "{}({!r})".format(
            self.__class__.__name__,
            getattr(self._handle, 'name', self._handle),
        )

    def __str__(self):  # noqa: D105
        return "<{} '{}'>".format(
            self.__class__.__name__.lower(),
            getattr(self._handle, 'name', self._handle),
        )

    def _on_modification_attempt(self, path):
        """Call when a modification is attempted on the archive.
        """
        raise errors.ResourceReadOnly(path)

    def setinfo(self, path, info):  # noqa: D102
        self.check()
        self._on_modification_attempt(path)

    def makedir(self, path, permissions=None, recreate=False):  # noqa: D102
        self.check()
        self._on_modification_attempt(path)

    def remove(self, path):  # noqa: D102
        self.check()
        self._on_modification_attempt(path)

    def removedir(self, path):  # noqa: D102
        self.check()
        self._on_modification_attempt(path)

    def getmeta(self, namespace="standard"):  # noqa: D102
        if namespace == "standard":
            return self._meta['standard'].copy()
        return {}

    def close(self):  # noqa: D102
        if not self.isclosed():
            if self._close_handle:
                getattr(self._handle, 'close', lambda: None)()
            super(ArchiveReadFS, self).close()


@six.add_metaclass(abc.ABCMeta)
class ArchiveFS(WrapFS):
    """A wrapper filesystem allowing to read, write and update an archive.
    """

    _read_fs_cls = NotImplemented
    _saver_cls = NotImplemented

    def __init__(self, handle, proxy=None, **options):
        """Create a new archive filesystem.

        Parameters:
            handle (io.IOBase or str): A filename or a stream storing an
                archive and/or in which to write the updated archive.
            proxy (FS): The filesystem to use as to perform temporary
                write operations. Leave to `None` to use the default
                defined in `~fs.archive.wrap.WrapWritable`.
                **[default: `~fs.memoryfs.MemoryFS`]**

        Keyword Arguments:
            close_handle (boolean): If `True`, close the handle
                when the filesystem is closed. **[default: True]**

        """
        initial_position = 0
        read_fs = None
        self._saver = None

        if isinstance(handle, six.binary_type):
            # Decode the path if it is in binary format
            handle = fsdecode(fspath(handle))

        if isinstance(handle, six.text_type):
            # Expand the path
            _path = os.path.expanduser(os.path.expandvars(handle))
            _path = os.path.normpath(os.path.abspath(_path))
            # Create the readable fs if the handle exists
            if os.path.exists(_path) and os.access(_path, os.R_OK):
                options.setdefault('close_handle', True)
                read_fs = self._read_fs_cls(handle, **options)
            # Create a saver only if the destination is writable
            create_saver = writable_path(_path)

        elif hasattr(handle, 'read'):
            # Get the initial stream position
            initial_position = getattr(handle, 'tell', lambda: 0)()
            # Create the readable fs if the handle is readable
            if handle.readable() and handle.seekable():
                read_fs = self._read_fs_cls(handle, **options)
            # Create a saver only if the destination is writable
            create_saver = writable_stream(handle)

        else:
            raise errors.CreateFailed("cannot use {}".format(handle))

        overwrite = read_fs is not None
        if create_saver:
            self._saver = self._saver_cls(handle, overwrite, initial_position)

        proxy = proxy or "mem://"
        wrapped_fs = WrapWritable(read_fs, writable_fs=proxy) \
                  if read_fs is not None else open_fs(proxy)
        super(ArchiveFS, self).__init__(wrapped_fs)

    def close(self):  # noqa: D102
        if not self.isclosed():
            if self._saver is not None:
                self._saver.save(self)
            self.delegate_fs().close()
            super(ArchiveFS, self).close()
