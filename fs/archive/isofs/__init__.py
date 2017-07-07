# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import re
import operator

import six
import pycdlib

from pycdlib.pycdlibexception import PyCdlibException

from .._utils import writable_path

from ... import errors
from ...base import FS
from ...mode import Mode
from ...path import basename, dirname, join, iteratepath, split
from ...info import Info
from ...enums import Seek
from ..._fscompat import fsdecode, fspath

from . import names
from .utils import iget



class ISOFS(FS):


    # def _make_iso_name(self, name, directory=False):
    #     basename, extension = splitext(name)

    def _get_iso_path(self, numpath):
        components = ['/']
        current = self._cd.get_entry('/')
        for num in numpath:
            current = iget(current.children, num)
            components.append(names.get_iso_name(current, False))
        return join(*components)

    def _get_joliet_path(self, numpath):
        components = ['/']
        current = self._cd.get_entry('/', True)
        for num in numpath:
            current = iget(current.children, num)
            components.append(names.get_joliet_name(current))
        return join(*components)

    def _get_numpath(self, path):
        """Get the numbered path to a resource from a path.

        A numbered path intends to solve compatibility issues in ISO images
        due to the multiple file hierarchies that coexist in parallel. It
        expects the same file to come in the same position regardless of the
        examined hierarchy. By refering the entries in the filesystem with
        their *numbered path* instead of their *path*, the same entry can be
        found quickly in both of the hierarchies.

        To Do:
            Avoid recursing from '/' if an intermediary directory is found
            in the path table (if '/a/b/c' is in the path table, then finding
            the numbered path of '/a/b/c/d' should be a single step).

        See also:
            `_get_record_from_numpath` to actually get the record referenced
            to by a numbered path.
        """
        _path = self.validatepath(path)

        if _path not in self._path_table:

            current = self._cd.get_entry('/', self._joliet_only)
            numpath = []

            for component in iteratepath(_path):
                children = iter(enumerate(current.children))
                index, child = next(children)

                while child is not None and self._get_name(child) != component:
                    index, child = next(children, (-1, None))

                    if child is not None:
                        if child.is_dot() or child.is_dotdot():
                            continue
                    else:
                        raise errors.ResourceNotFound(path)

                numpath.append(index)
                current = child

            self._path_table[_path] = numpath

        return self._path_table[_path]

    def _get_record_from_numpath(self, numpath, joliet=False):
        """Get the record located at the given numpath.
        """
        self.check()
        current = self._cd.get_entry('/', joliet)
        for num in numpath:
            current = iget(current.children, num)
        return current

    def _make_info_from_record(self, record, namespaces=None):
        namespaces = namespaces or ()

        name = '' if record.file_identifier() in b'/' \
          else self._get_name(record)

        info = {'basic': {'name': name, 'is_dir': record.is_dir()}}
        return Info(info)


    def __init__(self, handle, **options):

        self._cd = pycdlib.PyCdlib()
        self._cd.open(handle, **options)

        self._joliet = self._cd.joliet_vd is not None
        self._rridge = self._cd.rock_ridge is not None
        self._joliet_only = self._joliet and not self._rridge

        self._path_table = {}

        if self._rridge:
            self._get_name = names.get_rridge_name
            #self._get_record = self._find_rridge_record
        elif self._joliet:
            self._get_name = names.get_joliet_name
            #self._get_record = self._find_joliet_record
        else:
            self._get_name = names.get_iso_name
            #self._get_record = self._find_iso_record

    def listdir(self, path):
        return [info.name for info in self.scandir(path)]

    def scandir(self, path, namespaces=None, page=None):
        _path = self.validatepath(path)

        numpath = self._get_numpath(path)
        record = self._get_record_from_numpath(numpath, self._joliet_only)

        if not record.is_dir():
            raise errors.DirectoryExpected(path)

        for child in record.children:
            if not child.is_dot() and not child.is_dotdot():
                yield self._make_info_from_record(child, namespaces)

    def getinfo(self, path, namespaces=None):
        _path = self.validatepath(path)

        if path in '/':
            #record = self._cd.get_entry('/', self._joliet_only)
            return Info({'basic': {'name': '', 'is_dir': True}})

        numpath = self._get_numpath(path)
        record = self._get_record_from_numpath(numpath, self._joliet_only)

        return self._make_info_from_record(record, namespaces)

    def openbin(self, path, mode='r', buffering=-1, **options):
        pass

    def makedir(self, path, permissions=None, recreate=False):
        _path = self.validatepath(path)

        if self.exists(_path):
            if not recreate:
                raise errors.DirectoryExists(path)

        else:

            parent, name = split(_path)

            parent_numpath = self._get_numpath(parent)
            parent_record = self._get_record_from_numpath(parent_numpath)

            try:
                pycdlib.pycdlib.check_iso9660_directory(
                    fullname=name.encode('ascii'),
                    interchange_level=self._cd.interchange_level
                )

            except (PyCdlibException, UnicodeEncodeError):

                #if self._rridge:

                #self._get_numpath(parent)

                iso_name = names.new_rridge_directory_name(name, parent_record)

                print(iso_name)

                self._cd.add_directory(
                    iso_path=join(parent, iso_name),
                    rr_name=name if self._rridge else None,
                    joliet_path=_path if self._joliet else None
                )


                # elif self._joliet:
                #
                #     pass



                #else:
                #six.raise_from(errors.InvalidPath(path), None)






            else:  # Name is ok for what we want

                self._cd.add_directory(
                    iso_path=_path.upper(),
                    rr_name=name if self._rridge else None,
                    joliet_path=_path if self._joliet else None
                )


        self._path_table.clear()

        return self.opendir(_path)









    def remove(self, path):
        _path = self.validatepath(path)

        numpath = self._get_numpath(_path)
        record = self._get_record_from_numpath(numpath, False)

        if record.is_dir():
            raise errors.FileExpected(path)

        iso_path = self._get_iso_path(numpath).upper()
        rridge_name = names.get_rridge_name(record) if self._rridge else None
        joliet_path = self._get_joliet_path(numpath) if self._joliet else None

        self._cd.rm_file(iso_path, rridge_name, joliet_path)
        self._path_table.clear()

    def removedir(self, path):
        _path = self.validatepath(path)

        if _path in '/':
            raise errors.RemoveRootError(path)

        numpath = self._get_numpath(_path)
        record = self._get_record_from_numpath(numpath, False)

        _children_filter = lambda r: (not r.is_dotdot() and not r.is_dot())

        if not record.is_dir():
            raise errors.DirectoryExpected(path)
        elif list(filter(_children_filter, record.children)):
            print(list(filter(_children_filter, record.children))[0].file_identifier())
            raise errors.DirectoryNotEmpty(path)

        iso_path = self._get_iso_path(numpath).upper()
        rridge_name =   names.get_rridge_name(record) if self._rridge else None
        joliet_path = self._get_joliet_path(numpath) if self._joliet else None

        self._cd.rm_directory(iso_path, rridge_name, joliet_path)
        self._path_table.clear()


    def validatepath(self, path):
        _path = super(ISOFS, self).validatepath(path)
        if not self._rridge and not self._joliet:
            _path = _path.lower()
        return _path

    def setinfo(self, path, info):
        raise errors.ResourceReadOnly(path)
