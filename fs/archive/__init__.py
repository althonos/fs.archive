# coding: utf-8
"""Enhanced archive filesystems for Pyfilesystem2.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

__all__ = ['open_archive']

from .opener import open_archive

__license__ = "MIT"
__copyright__ = "Copyright (c) 2017-2021 Martin Larralde"
__author__ = "Martin Larralde <martin.larralde@embl.de>"
__version__ = (
    __import__("pkg_resources")
    .resource_string(__name__, "_version.txt")
    .strip()
    .decode("ascii")
)
