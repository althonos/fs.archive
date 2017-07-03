# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import six
import construct

from ... import errors
from ...enums import Seek
from ...base import FS
from ...info import Info
from ...path import join, recursepath
from ...tempfs import TempFS
from ...memoryfs import MemoryFS

from .. import base

from .structs import VolumeDescriptorParser, DirectoryBlock


class ISOReadFile(io.RawIOBase):

    def __init__(self, fs, record):
        self._fs = fs
        self._stream = fs._stream
        self._record = record
        self._start = record['Location of Extent'] * fs._blocksize
        self._end = self._start + record['Data Length']
        self._position = 0

    @property
    def name(self):
        return self._record['File Identifier'].split(b';')[0].decode('utf-8')

    def read1(self, size=-1):
        if size == -1 or size + self._position > len(self):
            size = len(self) - self._position
        with self._fs._lock:
            self._stream.seek(self._start + self._position)
            buffer = self._stream.read(size)
        self._position += size
        return buffer

    def read(self, size=-1):
        return self.read1(size=size)

    def __len__(self):
        return self._record['Data Length']

    def readable(self):
        return True

    def seek(self, offset, whence=Seek.set):

        if whence == Seek.set:
            if offset > len(self):
                offset = len(self)
            elif offset < 0:
                offset = 0
            with self._fs._lock:
                self._stream.seek(self._start + offset)
                self._position = offset

        if whence == Seek.current:
            if offset + self._start + self._position > self._end:
                offset = self._end - self._position - self._start
            elif offset + self._start + self._position < 0:
                offset = - self._start - self._position
            with self._fs._lock:
                self._stream.seek(self._start + self._position + offset)
                self._position += offset

        if whence == Seek.end:
            if offset > 0:
                offset = 0
            elif -offset > len(self):
                offset = -len(self)
            with self._fs._lock:
                self._stream.seek(self._end + offset)
                self._position += offset

        return self._position

    def seekable(self):
        return True

    def tell(self):
        return self._position

    def tellable(self):
        return True

class ISOReadFS(base.ArchiveReadFS):

    _meta = {
        'case_insensitive': True,
        'network': False,
        'read_only': True,
        'supports_rename': True,
        'thread_safe': True,
        'unicode_paths': False,
        'virtual': False,
    }

    def __init__(self, handle, **options):
        """Create a new read-only filesystem from an ISO image byte stream.
        """
        super(ReadISOFS, self).__init__(handle)

        if isinstance(handle, six.binary_type):
            handle = handle.decode('utf-8')
        if isinstance(handle, six.text_type):
            handle = open(handle, 'rb')
            self._close_handle = True
        else:
            self._close_handle = False

        self._stream = handle

        self._primary_descriptor = next(
            d for d in self._descriptors() if d.type=='PrimaryVolumeDescriptor')
        self._blocksize = self._primary_descriptor['Logical Block Size']

        self._path_table = {
            '/': self._primary_descriptor['Root Directory Record']
        }

    def _descriptors(self):
        """Yield the descriptors of the ISO image.
        """

        # Go to initial descriptor adress
        self._stream.seek(16 * 2048)

        descriptor_type = None
        while descriptor_type != 'VolumeDescriptorSetTerminator':

            # Read the next block & decode the descriptor
            block = self._stream.read(2048)
            meta_descriptor = VolumeDescriptorParser.parse(block)

            # Extract the type of the descriptor
            descriptor_type = meta_descriptor['VolumeDescriptor'].type

            # Yield the right descriptor struct
            yield meta_descriptor.get(
                descriptor_type, meta_descriptor['RawVolumeDescriptor'])

    def _directory_records(self, block_id):
        """Yield the records within a directory.

        Note:
            ``.`` and ``..`` (which in the ISO9660 standard are
            defined as ``\x00`` and ``\x01``) are ignored.
        """

        # Get the main directory block
        extent = self._get_block(block_id)
        block = DirectoryBlock(self._blocksize).parse(extent)
        block.records = block.records[2:] # NB: remove '\x01' and '\x02'

        while block.records:
            for record in block.records:
                # Stop iterator if we enter another directory
                if record['File Identifier'] in (b'\x00', b'\x01'):
                    return
                yield record

            # Attempt to explore adjacent block
            extent = self._stream.read(self._blocksize)
            block = DirectoryBlock(self._blocksize).parse(extent)

    def _find(self, path):
        for subpath in recursepath(path):
            try:
                record = self._path_table[subpath]
            except KeyError:
                raise errors.ResourceNotFound(subpath)

            for record in self._directory_records(record["Location of Extent"]):
                record_path = join(
                    subpath, record['File Identifier'].decode('ascii'))
                self._path_table[record_path] = record

    def _get_block(self, block_id):
        self._stream.seek(self._blocksize * block_id)
        return self._stream.read(self._blocksize)

    def _get_record(self, path):
        if path not in self._path_table:
            self._find(path)
        return self._path_table[path]

    def _make_info_from_record(self, record, namespaces=None):
        namespaces = namespaces or ()

        # FIXME: other namespaces
        info = {'basic': {
            'name': record['File Identifier'].split(b';')[0].decode('ascii'),
            'is_dir': record['Flags'].is_dir,
        }}

        return Info(info)

    def openbin(self, path, mode='r', buffering=-1, **options):
        if not mode.startswith('r'):
            self._on_modification_attempt(path)

        _path = self.validatepath(path)
        record = self._get_record(_path)

        return ISOReadFile(self, record)

    def scandir(self, path, namespaces=None, page=None):
        _path = self.validatepath(path)
        record = self._get_record(_path)

        if not record['Flags'].is_dir:
            raise errors.DirectoryExpected(path)

        for record in self._directory_records(record["Location of Extent"]):
            name = record['File Identifier'].split(b';')[0].decode('ascii')
            self._path_table[join(_path, name)] = record
            yield self._make_info_from_record(record, namespaces)

    def listdir(self, path):
        return [entry.name for entry in self.scandir(path)]

    def getinfo(self, path, namespaces=None):
        _path = self.validatepath(path)
        record = self._get_record(_path)

        return self._make_info_from_record(record, namespaces)
