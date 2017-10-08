# coding: utf-8
"""Enhanced archive filesystems for Pyfilesystem2.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

__all__ = ['open_archive']

from .opener import open_archive

__license__ = "MIT"
__copyright__ = "Copyright (c) 2017 Martin Larralde"
__author__ = "Martin Larralde <martin.larralde@ens-cachan.fr>"
__version__ = 'dev'

# Dynamically get the version of the installed module
try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution(__name__).version
except Exception:  # pragma: no cover
    pkg_resources = None
finally:
    del pkg_resources
