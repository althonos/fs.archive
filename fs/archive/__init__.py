# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib

@contextlib.contextmanager
def open_archive(fs_url, archive):
    from pkg_resources import iter_entry_points
    from ..opener import open_fs
    from ..opener._errors import Unsupported

    it = iter_entry_points('fs.archive.open_archive')
    entry_point = next((ep for ep in it if archive.endswith(ep.name)), None)

    if entry_point is None:
        raise Unsupported(
            'unknown archive extension: {}'.format(archive))

    archive_opener = entry_point.load()
    # if not isinstance(archive_fs, base.ArchiveFS):
    #     raise TypeError('bad entry point')

    try:
        with open_fs(fs_url) as fs:
            binfile = fs.openbin(archive, 'r+' if fs.isfile(archive) else 'w')
            archive_fs = archive_opener(binfile)
            yield archive_fs
    finally:
        archive_fs.close()
        binfile.close()

__all__ = ['open_archive']
