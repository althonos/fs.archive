# coding: utf-8
"""Declaration of the `open_archive` function.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import six
import pkg_resources

from .. import errors
from ..path import basename
from ..opener import open_fs
from ..opener.errors import UnsupportedProtocol

from . import base


def open_archive(fs_url, archive):
    """Open an archive on a filesystem.

    This function tries to mimick the behaviour of `fs.open_fs` as closely
    as possible: it accepts either a FS URL or a filesystem instance, and
    will close all resources it had to open.

    Arguments:
        fs_url (FS or text_type): a FS URL, or a filesystem
            instance, where the archive file is located.
        archive (text_type): the path to the archive file on the
            given filesystem.

    Raises:
        `fs.opener._errors.Unsupported`: when the archive type is not supported
            (either the file extension is unknown or the opener requires unmet
            dependencies).

    Example:
        >>> from fs.archive import open_archive
        >>> with open_archive('mem://', 'test.tar.gz') as archive_fs:
        ...     type(archive_fs)
        <class 'fs.archive.tarfs.TarFS'>

    Hint:
        This function finds the entry points defined in group
        ``fs.archive.open_archive``, using the names of the entry point
        as the registered extension.

    """
    it = pkg_resources.iter_entry_points('fs.archive.open_archive')
    entry_point = next((ep for ep in it if archive.endswith(ep.name)), None)

    if entry_point is None:
        raise UnsupportedProtocol(
            'unknown archive extension: {}'.format(archive))

    try:
        archive_opener = entry_point.load()
    except pkg_resources.DistributionNotFound as df: # pragma: no cover
        six.raise_from(UnsupportedProtocol(
            'extension {} requires {}'.format(entry_point.name, df.req)), None)

    try:
        binfile = None
        archive_fs = None
        fs = open_fs(fs_url)

        if issubclass(archive_opener, base.ArchiveFS):
            try:
                binfile = fs.openbin(archive, 'r+')
            except errors.ResourceNotFound:
                binfile = fs.openbin(archive, 'w')
            except errors.ResourceReadOnly:
                binfile = fs.openbin(archive, 'r')
                archive_opener = archive_opener._read_fs_cls

        elif issubclass(archive_opener, base.ArchiveReadFS):
            binfile = fs.openbin(archive, 'r')

        if not hasattr(binfile, 'name'):
            binfile.name = basename(archive)

        archive_fs = archive_opener(binfile)

    except Exception:
        getattr(archive_fs, 'close', lambda: None)()
        getattr(binfile, 'close', lambda: None)()
        raise

    else:
        return archive_fs
