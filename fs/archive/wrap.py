# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
import itertools
import abc
import six

from .. import errors
from ..base import FS
from ..errors import ResourceNotFound
from ..copy import copy_file
from ..path import abspath, dirname, join, normpath
from ..mode import Mode
from ..opener import open_fs
from ..wrapfs import WrapFS

from ._utils import unique, UniversalContainer, NoWrapMeta


__all__ = ["WrapWritable"]




@six.add_metaclass(NoWrapMeta)
class WrapWritable(WrapFS):
    """A wrapper that makes a read-only FS writable.

    All modifications are discarded once the filesystem is closed. Using
    the `NoWrapMeta` metaclass, the wrapper will use the base `FS`
    implementation of the non-essential methods instead of using the
    `WrapFS` implementation.
    """

    def __init__(self, delegate_fs, writable_fs="mem://"):  # noqa: D107
        super(WrapWritable, self).__init__(delegate_fs)
        self._rfs = delegate_fs
        self._wfs = open_fs(writable_fs)
        self._removed = set()

    def appendbytes(self, path, data):  # noqa: D102
        _path = self.validatepath(path)
        if not isinstance(data, six.binary_type):
            raise TypeError("must be bytes")
        if not self.isdir(dirname(_path)):
            raise errors.ResourceNotFound(dirname(path))
        self._wfs.makedirs(dirname(_path), recreate=True)
        if self.exists(_path) and not self.isfile(_path):
            raise errors.FileExpected(path)
        if self._rfs.isfile(_path) and _path not in self._removed:
            if not self._wfs.isfile(_path):
                _copy_file_rich(self._rfs, _path, self._wfs)
        if _path in self._removed:
            self._removed.remove(_path)
        return self._wfs.appendbytes(_path, data)

    # def appendtext(self, path, text):
    #     _path = self.validatepath(path)
    #     if not isinstance(text, six.text_type):
    #         raise TypeError("must be unicode string")
    #     if not self.isdir(dirname(_path)):
    #         raise errors.ResourceNotFound(dirname(path))
    #     self._wfs.makedirs(dirname(_path), recreate=True)
    #     if self.exists(_path) and not self.isfile(_path):
    #         raise errors.FileExpected(path)
    #     if self._rfs.isfile(_path) and _path not in self._removed:
    #         if not self._wfs.isfile(_path):
    #             _copy_file_rich(self._rfs, _path, self._wfs)
    #     if _path in self._removed:
    #         self._removed.remove(_path)
    #     return self._wfs.appendtext(_path, text)

    def close(self):  # noqa: D102
        if not self.isclosed():
            self._wfs.close()
            super(WrapWritable, self).close()

    def exists(self, path):  # noqa: D102
        _path = self.validatepath(path)
        if self._wfs.exists(path):
            return True
        if self._rfs.exists(path) and _path not in self._removed:
            return True
        return False

    def getinfo(self, path, namespaces=None):  # noqa: D102
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if self._wfs.exists(_path):
            return self._wfs.getinfo(_path, namespaces)
        return self._rfs.getinfo(_path, namespaces)

    def listdir(self, path):  # noqa: D102
        _path = self.validatepath(path)

        if not self.getinfo(path).is_dir:
            raise errors.DirectoryExpected(path)

        files_it = itertools.chain()
        if self._wfs.isdir(_path):
            files_it = itertools.chain(files_it, self._wfs.listdir(_path))
        if self._rfs.isdir(_path) and _path not in self._removed:
            files_it = itertools.chain(files_it, self._rfs.listdir(_path))

        def was_removed(name):
            return join(_path, name) in self._removed
        return list(unique(six.moves.filterfalse(was_removed, files_it)))

    def makedir(self, path, permissions=None, recreate=False):  # noqa: D102

        _path = self.validatepath(path)

        if self.exists(_path):
            if not recreate:
                raise errors.DirectoryExists(path)
        elif not self.exists(dirname(_path)):
            raise errors.ResourceNotFound(dirname(path))
        elif self.isfile(dirname(_path)):
            raise errors.DirectoryExpected(dirname(path))

        if _path in self._removed:
            self._removed.remove(_path)

        # FIXME: possible permission mismatch
        self._wfs.makedirs(dirname(_path), recreate=True)
        return self._wfs.makedir(_path, permissions, recreate)

    def openbin(self, path, mode='r', buffering=-1, **options):  # noqa: D102
        _path = self.validatepath(path)
        _mode = Mode(mode)
        _mode.validate_bin()

        if not self.exists(_path):
            if not self.isdir(dirname(_path)):
                raise ResourceNotFound(dirname(path))
            if _mode.create:
                if _path in self._removed:
                    self._removed.remove(_path)
                self._wfs.makedirs(dirname(_path), recreate=True)
                return self._wfs.openbin(path, mode, buffering, **options)
            else:
                raise ResourceNotFound(path)
        elif self._wfs.exists(_path):
            return self._wfs.openbin(path, mode, buffering, **options)
        elif not _mode.writing:
            return self._rfs.openbin(path, mode, buffering, **options)
        else:
            self._wfs.makedirs(dirname(_path), recreate=True)
            _copy_file_rich(self._rfs, _path, self._wfs)
            return self._wfs.openbin(path, mode, buffering, **options)

    def remove(self, path):  # noqa: D102
        _path = self.validatepath(path)
        if not self.getinfo(path).is_file:
            raise errors.FileExpected(path)
        self._removed.add(_path)
        if self._wfs.isfile(_path):
            self._wfs.remove(_path)

    def removedir(self, path):  # noqa: D102
        _path = self.validatepath(path)
        if not self.isempty(_path):
            raise errors.DirectoryNotEmpty(path)
        self._removed.add(_path)
        if self._wfs.isdir(_path):
            self._wfs.removedir(_path)

    def scandir(self, path, namespaces=None, page=None):  # noqa: D102
        _path = self.validatepath(path)

        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if not self.isdir(_path):
            raise errors.DirectoryExpected(path)

        it = itertools.chain()
        if self._wfs.isdir(_path):
            it = itertools.chain(it, self._wfs.scandir(_path, namespaces))
        if self._rfs.isdir(_path) and _path not in self._removed:
            it = itertools.chain(it, self._rfs.scandir(_path, namespaces))

        def _exists(info):
            return self.exists(join(_path, info.name))
        it = six.moves.filter(_exists, it)
        it = unique(it, key=operator.attrgetter('name'))
        if page is not None:
            it = itertools.islice(it, page[0], page[1])

        return it

    def setinfo(self, path, info):  # noqa: D102
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if self._rfs.exists(_path):
            self._wfs.makedirs(dirname(_path), recreate=True)
            _copy_file_rich(self._rfs, _path, self._wfs, _path)
        return self._wfs.setinfo(_path, info)

    # def touch(self, path):
    #     _path = self.validatepath(path)
    #     if not self.isfile(_path):
    #         with self.openbin(_path, 'wb') as f:
    #             f.write(b'')

    def validatepath(self, path):  # noqa: D102
        super(WrapWritable, self).validatepath(path)
        return abspath(normpath(path))



def _copy_file_rich(src_fs, src_path, dst_fs, dst_path=None):
    dst_path = src_path if dst_path is None else dst_path
    copy_file(src_fs, src_path, dst_fs, dst_path)
    src_info = src_fs.getinfo(src_path, namespaces=UniversalContainer())
    dst_fs.setinfo(dst_path, src_info.raw)
